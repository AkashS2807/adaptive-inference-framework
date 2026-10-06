import csv,json,tempfile,unittest
from pathlib import Path
import test_pipeline
from aai.experiments import run_benchmark,export_grades,import_grades,report,dataset
from aai.config import ROOT

class ExperimentTests(unittest.TestCase):
    setUp=test_pipeline.PipelineTests.setUp
    tearDown=test_pipeline.PipelineTests.tearDown
    engine=test_pipeline.PipelineTests.engine
    def test_dataset_splits(self):
        rows=dataset(ROOT/'data/benchmark.jsonl')
        queries=[x['query'] for x in rows]
        self.assertEqual(len(queries),len(set(queries)))
        self.assertEqual(set(x['split'] for x in rows),{'pilot','train','test'})
    def test_experiment_resumes_and_grades(self):
        e=self.engine();e.cfg['automatic_proxy_rewards']=False
        path=Path(self.tmp.name)/'dataset.jsonl'
        path.write_text(json.dumps({'id':'q','split':'test','category':'factual','query':'What is a tree?','rubric':'A woody plant.'})+'\n')
        self.assertTrue(run_benchmark(e,path,'unit',modes=['formula','baseline']))
        self.assertTrue(run_benchmark(e,path,'unit',modes=['formula','baseline']))
        self.assertEqual(len(e.store.recent()),2)
        folder=Path(self.tmp.name)/'report';export_grades(e.store,'unit',folder)
        with (folder/'blind_grading.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
        for row in rows:row.update(relevance='1',completeness='1',correctness='1')
        with (folder/'blind_grading.csv').open('w',newline='',encoding='utf-8-sig') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        self.assertEqual(import_grades(e,folder),2)
        result=report(e.store,'unit',folder)
        self.assertEqual(result[0]['mean_human_quality'],1)
        self.assertEqual(import_grades(e,folder,source='blinded_assistant'),2)
        result=report(e.store,'unit',folder)
        self.assertEqual(result[0]['human_scored'],0)
        self.assertIsNone(result[0]['mean_human_quality'])
        self.assertEqual(result[0]['assistant_scored'],1)
        self.assertEqual(result[0]['mean_assistant_quality'],1)
        self.assertTrue(all(not r['learning_enabled'] and r['reward'] is None for r in e.store.recent()))
        self.assertTrue((folder/'all_attempts.jsonl').exists())
    def test_sequential_training_feedback(self):
        e=self.engine();e.cfg['automatic_proxy_rewards']=False
        path=Path(self.tmp.name)/'train.jsonl'
        path.write_text('\n'.join(json.dumps({'id':str(i),'split':'train','category':'factual','query':f'What is a tree? {i}'}) for i in range(3)))
        self.assertTrue(run_benchmark(e,path,'training',split='train',modes=['online'],feedback_fn=lambda r,q:.9))
        rows=e.store.recent();self.assertEqual(sorted(r['decision']['initial_tier'] for r in rows),[0,1,2])
        self.assertEqual(e.store.state(rows[0]['decision']['state_key'])['counts'],[1,1,1])
    def test_snapshot_isolation(self):
        e=self.engine();r=e.run('What is a tree?','online',True);e.controller.feedback(r,.8,'human')
        path=Path(self.tmp.name)/'test.jsonl';path.write_text(json.dumps({'id':'q','split':'test','category':'factual','query':'What is a tree?'})+'\n')
        run_benchmark(e,path,'frozen',modes=['online'])
        test=e.store.recent()[0];self.assertNotEqual(test['decision']['state_key'],r['decision']['state_key'])
        self.assertEqual(test['decision']['state_version'],1)
        self.assertFalse(test['learning_enabled'])

    def test_suffix_signature_rejects_changed_condition(self):
        e=self.engine();path=Path(self.tmp.name)/'format.jsonl'
        path.write_text(json.dumps({'id':'q','split':'test','category':'factual','query':'What is a tree?'})+'\n')
        self.assertTrue(run_benchmark(e,path,'format',modes=['formula'],generation_suffix='Be concise.'))
        r=e.store.recent()[0];self.assertEqual(r['analysis']['original'],'What is a tree?')
        self.assertFalse(r['learning_enabled']);self.assertIsNone(r['reward'])
        for suffix in ('Different instruction.',''):
            with self.assertRaises(ValueError):run_benchmark(e,path,'format',modes=['formula'],generation_suffix=suffix)
        with self.assertRaises(ValueError):run_benchmark(e,path,'format',split='train',generation_suffix='Be concise.')

    def test_amended_cohort_stops_on_structural_failure(self):
        e=self.engine();path=Path(self.tmp.name)/'structural.jsonl'
        path.write_text(json.dumps({'id':'q','split':'test','category':'factual','query':'What is a tree?'})+'\n')
        original=e.run
        def truncated(*args,**kwargs):
            r=original(*args,**kwargs);r['status']='needs_review'
            r['attempts'][0]['evaluation']['basic']['issues']=['output_truncated']
            e.store.save(r);return r
        e.run=truncated
        self.assertFalse(run_benchmark(e,path,'structural',generation_suffix='Be concise.'))
        self.assertEqual(len(e.store.recent()),1)

    def test_explicit_retry_preserves_review_and_skips_completed(self):
        e=self.engine();e.cfg['automatic_proxy_rewards']=False
        path=Path(self.tmp.name)/'retry.jsonl'
        path.write_text(json.dumps({'id':'q','split':'test','category':'factual','query':'What is a tree?'})+'\n')
        run_benchmark(e,path,'retry-review',modes=['formula','baseline'])
        original=next(r for r in e.store.recent() if r['mode']=='formula')
        original['status']='needs_review';e.store.save(original)
        run_benchmark(e,path,'retry-review',modes=['formula','baseline'])
        self.assertEqual(len(e.store.recent()),2)
        run_benchmark(e,path,'retry-review',modes=['formula','baseline'],retry_needs_review=True)
        self.assertEqual(len(e.store.recent()),3)
        self.assertEqual(e.store.get(original['id'])['status'],'needs_review')
        self.assertEqual(sum(r['mode']=='baseline' for r in e.store.recent()),1)
        self.assertTrue(all(not r['learning_enabled'] and r.get('reward') is None for r in e.store.recent()))
