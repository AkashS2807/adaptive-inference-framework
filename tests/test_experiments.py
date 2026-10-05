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
