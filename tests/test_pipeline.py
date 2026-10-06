import json,os,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
import numpy as np
from aai.config import load_config
from aai.storage import Store
from aai.providers import Gateway,QuotaError,APIError
from aai.evaluation import parse_judgment
from aai.pipeline import Engine
from aai.controllers import Controller

class Semantic:
    def analyze(self,q):
        return {'similarities':{'Factual':.9,'Reasoning':.2,'Analytical':.1,'Creative':.05,'Technical':.1},'task':'Factual','margin':.7,'uncertain':False,'prototype_hash':'test-prototypes'}
class Retrieval:
    def search(self,q,recency=False):
        return {'status':'fresh_evidence_unavailable' if recency else 'retrieved','documents':[] if recency else [{'id':'test','text':'Reference'}]}
class Transport:
    def __init__(self,scores=None): self.scores=iter(scores or [.9]*20);self.bodies=[]
    def __call__(self,url,headers,body,timeout):
        self.bodies.append(body)
        is_gemini='contents' in body
        system=body['systemInstruction']['parts'][0]['text'] if is_gemini else body['messages'][0]['content']
        text='A relevant, complete answer.'
        if 'assess a response' in system:
            score=next(self.scores);text=json.dumps(dict(relevance=score,completeness=score,task_quality=score,evidence_consistency=score,reason='rubric'))
        if is_gemini: return {'candidates':[{'content':{'parts':[{'text':text}]},'finishReason':'STOP'}],'usageMetadata':{'promptTokenCount':20,'candidatesTokenCount':30,'totalTokenCount':50}}
        return {'choices':[{'message':{'content':text},'finish_reason':'stop'}],'usage':{'prompt_tokens':20,'completion_tokens':30,'total_tokens':50}}
class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'test.sqlite');self.cfg=load_config();self.cfg["automatic_proxy_rewards"]=True
        for m in self.cfg['models']: m.update(rpm=1000,rpd=10000,tpm=1000000,tpd=10000000)
        self.env=patch.dict(os.environ,{'FREE_TIER_CONFIRMED':'true','GEMINI_API_KEY':'test-secret','GROQ_API_KEY':'test-secret'});self.env.start()
    def tearDown(self): self.env.stop();self.tmp.cleanup()
    def engine(self,scores=None):
        self.transport=Transport(scores);g=Gateway(self.cfg,self.store,self.transport)
        return Engine(self.cfg,self.store,Semantic(),g,Retrieval())
    def test_simple_no_judge(self):
        r=self.engine().run('What is a tree?')
        self.assertEqual(r['decision']['initial_tier'],0);self.assertEqual(r['metrics']['api_calls'],1)
        self.assertIsNone(r['final_evaluation']['score']);self.assertEqual(r['final_evaluation']['status'],'unchecked')

    def test_generation_suffix_preserves_analysis_and_judge(self):
        from aai.pipeline import SYSTEM
        from aai.evaluation import JUDGE_SYSTEM
        from aai.config import ROOT
        import hashlib
        suffix=(ROOT/'docs/complex-concise-instruction.txt').read_text(encoding='utf-8').rstrip('\r\n')
        for mode in ('formula','online','hybrid','baseline'):
            e=self.engine([.2,.9,.9]);q='Calculate 4 plus 4'
            original=e.run(q,mode)
            r=e.run(q,mode,metadata={'split':'test'},generation_suffix=suffix)
            self.assertEqual(r['analysis'],original['analysis'])
            self.assertEqual(r['decision']['initial_tier'],original['decision']['initial_tier'])
            self.assertFalse(r['learning_enabled']);self.assertIsNone(r['reward'])
            self.assertEqual(r['generation_prompt_hash'],hashlib.sha256((SYSTEM+'\n\n'+suffix).encode()).hexdigest())
            self.assertEqual(r['generation_format']['instruction'],suffix)
            bodies=self.transport.bodies[-r['metrics']['api_calls']:]
            for body in bodies:
                system=body['systemInstruction']['parts'][0]['text'] if 'contents' in body else body['messages'][0]['content']
                self.assertIn(system,(SYSTEM+'\n\n'+suffix,JUDGE_SYSTEM))
        with self.assertRaises(ValueError):self.engine().run('q',learning=True,metadata={'split':'test'},generation_suffix=suffix)
    def test_escalation_and_full_cost(self):
        r=self.engine([.2,.9]).run('Calculate 4 plus 4','online',True)
        self.assertEqual([a['tier'] for a in r['attempts']],[0,1]);self.assertEqual(r['metrics']['api_calls'],4)
        self.assertEqual(r['metrics']['total_tokens'],200);self.assertEqual(r['reward']['credited_initial_tier'],0)
        self.assertEqual(self.store.state(r['decision']['state_key'])['counts'],[1,0,0])
    def test_max_escalation(self):
        r=self.engine([.1,.3,.2]).run('Calculate 4 plus 4','online')
        self.assertEqual(len(r['attempts']),3);self.assertEqual(r['status'],'needs_review');self.assertEqual(r['final_tier'],1)
    def test_baseline(self):
        r=self.engine().run('What is a tree?','baseline')
        self.assertEqual(r['decision']['initial_tier'],2);self.assertEqual(len(r['attempts']),1)
    def test_no_fresh_source_no_call(self):
        r=self.engine().run('What is the latest policy?');self.assertEqual(r['status'],'evidence_unavailable');self.assertEqual(r['metrics']['api_calls'],0)
    def test_feedback_once(self):
        e=self.engine();r=e.run('What is a tree?','online',True)
        self.assertIsNone(r['reward']);e.controller.feedback(r,.8,'human')
        with self.assertRaises(ValueError): e.controller.feedback(r,.8,'human')
    def test_frozen_policy(self):
        e=self.engine();r=e.run('Calculate 4 plus 4','online',False)
        self.assertIsNone(self.store.state(r['decision']['state_key']));self.assertIsNone(r['reward'])
    def test_infra_not_reward(self):
        e=self.engine();e.gateway.transport=lambda *args: (_ for _ in ()).throw(APIError('offline'))
        r=e.run('Calculate 4 plus 4','online',True)
        self.assertEqual(r['status'],'api_error');self.assertIsNone(r['reward'])
    def test_judge_api_failure_does_not_escalate_or_learn(self):
        e=self.engine()
        original=e.gateway.transport
        def fail_judge(url,headers,body,timeout):
            if 'messages' in body and 'assess a response' in body['messages'][0]['content']:raise QuotaError('judge rate limit')
            return original(url,headers,body,timeout)
        e.gateway.transport=fail_judge
        r=e.run('Calculate 4 plus 4','online',True)
        self.assertEqual(r['status'],'evaluation_unavailable');self.assertEqual(len(r['attempts']),1);self.assertIsNone(r['reward'])
    def test_invalid_judge_json_is_not_model_failure(self):
        e=self.engine();original=e.gateway.transport
        def invalid(url,headers,body,timeout):
            raw=original(url,headers,body,timeout)
            if 'messages' in body and 'assess a response' in body['messages'][0]['content']:raw['choices'][0]['message']['content']='not JSON'
            return raw
        e.gateway.transport=invalid;r=e.run('Calculate 4 plus 4','online',True)
        self.assertEqual(r['status'],'evaluation_unavailable');self.assertEqual(len(r['attempts']),1)
    def test_missing_usage_blocks_reward(self):
        e=self.engine();original=e.gateway.transport
        def no_usage(url,headers,body,timeout):
            raw=original(url,headers,body,timeout);raw.pop('usage',None);raw.pop('usageMetadata',None);return raw
        e.gateway.transport=no_usage;r=e.run('What is a tree?','online',True)
        self.assertFalse(r['metrics']['token_usage_complete'])
        with self.assertRaises(ValueError):e.controller.feedback(r,.9,'human')
    def test_no_key_in_logs(self):
        r=self.engine().run('Hello');self.assertNotIn('test-secret',json.dumps(r))
    def test_quota_prevents_transport(self):
        self.cfg['models'][0]['rpd']=1
        e=self.engine();e.run('Hello')
        with self.assertRaises(QuotaError): e.gateway.generate('x',0,'system','user')
        self.assertEqual(len(self.transport.bodies),1)
    def test_invalid_judge(self):
        with self.assertRaises(ValueError):parse_judgment('{"relevance":NaN,"completeness":1,"task_quality":1}',False)
    def test_no_billing_confirmation(self):
        os.environ['FREE_TIER_CONFIRMED']='false';r=self.engine().run('Hello')
        self.assertEqual(r['status'],'api_error');self.assertEqual(len(self.transport.bodies),0)
    def test_hybrid_prior_and_independent_state(self):
        e=self.engine();r=e.run('Explain recursion','hybrid',True)
        self.assertEqual(r['decision']['initial_tier'],r['decision']['formula_tier'])
        e.controller.feedback(r,.9,'human')
        other=e.run('Explain recursion','online',False)
        self.assertIsNone(e.store.state(other['decision']['state_key']))
if __name__=='__main__':unittest.main()
