import hashlib,json,math
import numpy as np
MODES=('formula','online','hybrid','baseline')

def formula(a,cfg):
    f=a['features'];reasons=[];tier=0
    if a['complexity']>=cfg['complexity']['high'] or (f['requirements']>=2/3 and (f['reasoning']>0 or a['semantic']['task']=='Analytical')):
        tier=2;reasons.append('High complexity or combined reasoning and multiple requirements')
    elif a['complexity']>=cfg['complexity']['low'] or f['reasoning']>0 or f['technical']>0 or f['code'] or f['calculation'] or a['semantic']['task'] in ('Analytical','Reasoning','Technical'):
        tier=1;reasons.append('Reasoning, technical work, calculation, or moderate complexity')
    else: reasons.append('Low measured demand')
    if a['semantic']['uncertain'] and tier==0:
        tier=1;reasons.append('Uncertain semantic classification: conservative middle tier')
    return tier,reasons

class Controller:
    def __init__(self,cfg,store): self.cfg,self.store=cfg,store
    def key(self,mode,analysis,namespace='default'):
        # Isolate states whenever features/prototypes/configuration or experiment changes.
        return f'bandit:{namespace}:{mode}:{self.cfg["hash"]}:{analysis["semantic"]["prototype_hash"]}'
    def initial(self,dim):
        return {'A':[(np.eye(dim)*self.cfg['bandit']['ridge']).tolist() for _ in range(3)],
                'b':[[0.]*dim for _ in range(3)],'counts':[0,0,0],'version':0}
    def decide(self,mode,a,namespace='default'):
        if mode not in MODES: raise ValueError('Unknown routing mode')
        prior,reasons=formula(a,self.cfg);state=None;scores=None;key=None
        if mode=='baseline': action=2;reasons=['Always start at tier 3; same tools/evaluator policy']
        elif mode=='formula': action=prior
        else:
            key=self.key(mode,a,namespace);x=np.asarray(a['context'],dtype=float)
            state=self.store.state(key) or self.initial(len(x));scores=[]
            for arm in range(3):
                A=np.asarray(state['A'][arm]);b=np.asarray(state['b'][arm]);invx=np.linalg.solve(A,x)
                score=float(np.linalg.solve(A,b)@x+self.cfg['bandit']['exploration']*np.sqrt(max(0,x@invx)))
                if mode=='hybrid' and arm==prior: score+=self.cfg['bandit']['hybrid_bonus']
                scores.append(score)
            # Deterministic balanced cold start; no cherry-picked demo routing.
            untried=[i for i,n in enumerate(state['counts']) if n==0]
            action=(prior if prior in untried and mode=='hybrid' else untried[0]) if untried else int(np.argmax(scores))
            reasons=['LinUCB contextual selection'+(' with formula prior bonus' if mode=='hybrid' else ''),
                     'Cold-start exploration' if untried else 'Learned mean utility plus uncertainty bonus']
        snapshot=hashlib.sha256(json.dumps(state,sort_keys=True).encode()).hexdigest() if state else None
        return {'initial_tier':action,'initial_model':self.cfg['models'][action]['id'],'formula_tier':prior,
                'reasons':reasons,'scores':scores,'state_key':key,'state_version':state['version'] if state else None,
                'state_hash':snapshot,'state_snapshot':state}
    def feedback(self,run,quality,source):
        if run.get('config_hash')!=self.cfg['hash']: raise ValueError('Feedback configuration differs from the original run; use its saved configuration.')
        if not math.isfinite(quality) or not 0<=quality<=1: raise ValueError('Quality must be finite and in [0,1]')
        if not run.get('learning_enabled') or run['mode'] not in ('online','hybrid'): raise ValueError('Learning is disabled for this run')
        if run['status'] not in ('completed','needs_review'): raise ValueError('Do not train on infrastructure failures or unavailable evidence')
        metrics=run['metrics']
        if not metrics['token_usage_complete']: raise ValueError('Missing API token usage: reward cannot be measured consistently')
        w=self.cfg['reward'];tokens=metrics['total_tokens'];seconds=metrics['active_latency_seconds']
        failed=quality<self.cfg['acceptance']
        reward=float(quality-w['token_weight']*min(tokens/w['token_reference'],1)-w['latency_weight']*min(seconds/w['seconds_reference'],1)-w['failure_penalty']*failed)
        decision=run['decision'];key=decision['state_key'];x=np.asarray(run['analysis']['context']);arm=decision['initial_tier']
        # Atomic exactly-once update, including delayed human feedback.
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM feedback WHERE run_id=?',(run['id'],)).fetchone(): raise ValueError('Feedback already applied to this run')
            row=db.execute('SELECT payload FROM states WHERE name=?',(key,)).fetchone()
            state=json.loads(row[0]) if row else self.initial(len(x))
            state['A'][arm]=(np.asarray(state['A'][arm])+np.outer(x,x)).tolist()
            state['b'][arm]=(np.asarray(state['b'][arm])+reward*x).tolist()
            state['counts'][arm]+=1;state['version']+=1
            run['reward']={'value':reward,'quality':quality,'source':source,'updated_state_version':state['version'],'credited_initial_tier':arm}
            db.execute('INSERT INTO feedback VALUES(?,?,?)',(run['id'],quality,reward))
            db.execute('INSERT OR REPLACE INTO states VALUES(?,?)',(key,json.dumps(state)))
            db.execute('INSERT OR REPLACE INTO runs VALUES(?,?,?)',(run['id'],run['created'],json.dumps(run)))
        return run['reward']
