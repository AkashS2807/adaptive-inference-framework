"""Free-plan API adapters. No billing setup, paid fallback, or implicit retry."""
import json,os,time,uuid,urllib.request,urllib.error

class APIError(RuntimeError): pass
class QuotaError(APIError):
    def __init__(self,message,retry_after=None):
        super().__init__(message);self.retry_after=retry_after

def post_json(url,headers,body,timeout):
    req=urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'adaptive-inference-phase1/1.0',
            **headers
        },
        method='POST'
    )
    try:
        with urllib.request.urlopen(req,timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise QuotaError(
                "Provider quota/rate limit reached. Pause and check the provider dashboard; no retry was made."
            ) from None
        raise APIError(
            f"Provider HTTP {exc.code}; check model access, key, and provider dashboard."
        ) from None
    except (urllib.error.URLError,TimeoutError,OSError):
        raise APIError('API connection failed or timed out; no automatic retry was made.') from None

class Gateway:
    def __init__(self,cfg,store,transport=post_json):
        self.cfg,self.store,self.transport=cfg,store,transport
    def _reserve(self,run_id,model,reserved,purpose):
        now=time.time();mid=model['id'];cid=uuid.uuid4().hex
        record={'id':cid,'model':mid,'provider':model['provider'],'purpose':purpose,'created':now,
                'status':'reserved','estimated_tokens_reserved':reserved,'input_tokens':None,'output_tokens':None,'total_tokens':None}
        # A single transaction prevents concurrent sessions from bypassing local limits.
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            cool=db.execute('SELECT payload FROM states WHERE name=?',('cooldown:'+mid,)).fetchone()
            if cool and json.loads(cool[0])>now: raise QuotaError('Provider returned 429 recently; this model is temporarily paused.')
            rows=db.execute('SELECT created,reserved FROM calls WHERE model=? AND created>?',(mid,now-86400)).fetchall()
            recent=[r for r in rows if r[0]>now-60]
            head=self.cfg['quota_headroom']
            checks=[(len(recent)+1,model['rpm'],'minute request'),(len(rows)+1,model['rpd'],'rolling-day request'),
                    (sum(r[1] for r in recent)+reserved,model['tpm'],'minute token'),
                    (sum(r[1] for r in rows)+reserved,model.get('tpd'),'rolling-day token')]
            for value,limit,label in checks:
                if limit is not None and value>max(1,int(limit*head)):
                    wait=max(0.1,min(r[0] for r in recent)+60-now+0.1) if label.startswith('minute') and recent and reserved<=int(model['tpm']*head) else None
                    raise QuotaError(f'Local {label} budget for {mid} reached. Wait or resume later; no API request was sent.',wait)
            db.execute('INSERT INTO calls VALUES(?,?,?,?,?,?)',(cid,run_id,mid,now,reserved,json.dumps(record)))
        return record
    def generate(self,run_id,tier,system,user,purpose='generation',max_output=None):
        if os.getenv('FREE_TIER_CONFIRMED','').lower()!='true':
            raise APIError('Confirm both projects are on free plans, then set FREE_TIER_CONFIRMED=true in your local .env.')
        m=self.cfg['models'][tier];key=os.getenv('GEMINI_API_KEY' if m['provider']=='gemini' else 'GROQ_API_KEY')
        if not key: raise APIError(f'Missing local API key for {m["provider"]}.')
        maximum=max_output or m['max_output']
        # UTF-8 bytes are a deliberately conservative input-token proxy, not reported usage.
        reserved=len((system+user).encode('utf-8'))+maximum
        wait_started=time.perf_counter();waited=0.
        while True:
            try:
                record=self._reserve(run_id,m,reserved,purpose);break
            except QuotaError as exc:
                elapsed=time.perf_counter()-wait_started
                if exc.retry_after is None or elapsed+exc.retry_after>self.cfg['max_wait_seconds']: raise
                time.sleep(min(exc.retry_after,60));waited=time.perf_counter()-wait_started
        record['quota_wait_seconds']=waited
        start=time.perf_counter()
        try:
            if m['provider']=='gemini':
                if not all(c.isalnum() or c in '-._' for c in m['id']): raise APIError('Invalid Gemini model ID')
                raw=self.transport('https://generativelanguage.googleapis.com/v1beta/models/'+m['id']+':generateContent',
                    {'x-goog-api-key':key},{'systemInstruction':{'parts':[{'text':system}]},'contents':[{'role':'user','parts':[{'text':user}]}],
                    'generationConfig':{'temperature':self.cfg['temperature'],'maxOutputTokens':maximum}},self.cfg['timeout_seconds'])
                candidates=raw.get('candidates',[])
                if not candidates: raise APIError('Provider returned no answer candidate (possibly blocked).')
                c=candidates[0];answer=''.join(p.get('text','') for p in c.get('content',{}).get('parts',[]) if not p.get('thought'))
                usage=raw.get('usageMetadata',{});inp=usage.get('promptTokenCount');out=usage.get('candidatesTokenCount');total=usage.get('totalTokenCount')
                finish=c.get('finishReason');reasoning=usage.get('thoughtsTokenCount')
                version=raw.get('modelVersion',m['id'])
            elif m['provider']=='groq':
                body={'model':m['id'],'messages':[{'role':'system','content':system},{'role':'user','content':user}],
                      'temperature':self.cfg['temperature'],'max_completion_tokens':maximum}
                if 'gpt-oss' in m['id']: body.update(reasoning_effort=m.get('reasoning_effort','low'),include_reasoning=False)
                raw=self.transport('https://api.groq.com/openai/v1/chat/completions',{'Authorization':'Bearer '+key},body,self.cfg['timeout_seconds'])
                choices=raw.get('choices',[])
                if not choices: raise APIError('Provider returned no answer choice.')
                c=choices[0];answer=c.get('message',{}).get('content') or '';usage=raw.get('usage',{})
                inp=usage.get('prompt_tokens');out=usage.get('completion_tokens');total=usage.get('total_tokens')
                finish=c.get('finish_reason');reasoning=usage.get('completion_tokens_details',{}).get('reasoning_tokens');version=raw.get('model',m['id'])
            else: raise APIError('Unsupported provider')
            record.update(status='ok',input_tokens=inp,output_tokens=out,total_tokens=total,reasoning_tokens=reasoning,
                          finish_reason=finish,model_version=version)
            return {'text':answer,'finish_reason':finish,'call_id':record['id']}
        except QuotaError:
            record['status']='quota_error'
            self.store.save_state('cooldown:'+m['id'],time.time()+60)
            raise
        except APIError:
            record['status']='api_error';raise
        except Exception:
            record['status']='invalid_response'
            raise APIError('Unexpected provider response format; inspect model compatibility.') from None
        finally:
            record['latency_seconds']=time.perf_counter()-start
            with self.store.connect() as db:
                db.execute('UPDATE calls SET payload=? WHERE id=?',(json.dumps(record),record['id']))
