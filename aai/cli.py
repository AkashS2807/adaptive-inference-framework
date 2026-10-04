import argparse,json,os,sys,uuid,importlib.util,platform
from pathlib import Path
from .config import ROOT,load_config,load_env
from .storage import Store
from .providers import Gateway,APIError
from .controllers import MODES

def main():
    p=argparse.ArgumentParser(description='Phase 1 adaptive inference')
    p.add_argument('--config',default=str(ROOT/'configs/settings.json'));p.add_argument('--db',default=str(ROOT/'outputs/runs.sqlite'))
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor');sub.add_parser('check-apis');sub.add_parser('prepare')
    ask=sub.add_parser('ask');ask.add_argument('query');ask.add_argument('--mode',choices=MODES,default='formula');ask.add_argument('--learn',action='store_true');ask.add_argument('--namespace',default='default')
    bench=sub.add_parser('benchmark');bench.add_argument('--dataset',default=str(ROOT/'data/benchmark.jsonl'));bench.add_argument('--experiment',required=True);bench.add_argument('--split',choices=('pilot','train','test'),default='test');bench.add_argument('--modes',nargs='+',choices=MODES,default=list(MODES));bench.add_argument('--namespace',default='default');bench.add_argument('--limit',type=int);bench.add_argument('--seed',type=int,default=42)
    for name in ('report','export-grades'):
        q=sub.add_parser(name);q.add_argument('--experiment',required=True);q.add_argument('--folder',default=str(ROOT/'outputs/report'))
    q=sub.add_parser('import-grades');q.add_argument('--folder',default=str(ROOT/'outputs/report'))
    args=p.parse_args();load_env();cfg=load_config(args.config);store=Store(args.db)
    if args.command=='doctor':
        print('Python:',platform.python_version(),'| Free plan confirmation:',os.getenv('FREE_TIER_CONFIRMED','false'))
        for n in ('numpy','streamlit','sentence_transformers','dotenv'):print(n,':','installed' if importlib.util.find_spec(n) else 'MISSING')
        for key in ('GEMINI_API_KEY','GROQ_API_KEY'):print(key,':','present (hidden)' if os.getenv(key) else 'MISSING')
        print('Models:',', '.join(m['id'] for m in cfg['models']));print('Configuration calibrated:',cfg['calibrated']);return
    if args.command=='check-apis':
        g=Gateway(cfg,store);failed=False
        for tier,m in enumerate(cfg['models']):
            try:
                r=g.generate('preflight-'+uuid.uuid4().hex,tier,'Give a short final answer.','What is 2 plus 2?',max_output=768)
                if not r['text'].strip() or r['finish_reason'] in ('length','MAX_TOKENS'): raise APIError('Empty/truncated response: inspect output budget and reasoning settings.')
                print(m['id'],': OK |',r['text'][:180])
            except APIError as exc:print(m['id'],': FAILED |',str(exc));failed=True
        if failed:sys.exit(1)
        return
    from .experiments import run_benchmark,report,export_grades,import_grades
    if args.command=='report':print(json.dumps(report(store,args.experiment,args.folder),indent=2));return
    if args.command=='export-grades':print(export_grades(store,args.experiment,args.folder));return
    if args.command=='import-grades':
        from .controllers import Controller
        class Grader:pass
        e=Grader();e.store=store;e.controller=Controller(cfg,store)
        print('Imported grades:',import_grades(e,args.folder));return
    from .pipeline import Engine
    e=Engine(cfg,store)
    if args.command=='prepare':print('CPU embedding model, prototypes and evidence corpus loaded successfully.');return
    if args.command=='ask':
        r=e.run(args.query,args.mode,args.learn,args.namespace);print(r['response']);print(json.dumps({'id':r['id'],'status':r['status'],'decision':{k:v for k,v in r['decision'].items() if k!='state_snapshot'},'metrics':r['metrics'],'evaluation':r['final_evaluation'],'error':r.get('error')},indent=2));return
    if args.command=='benchmark':
        if args.split=='test':print('Test run: online updates disabled. Train and grade online/hybrid beforehand; an untrained policy is only a cold-start smoke test.')
        def feedback(run,item):
            print('\nTRAINING ANSWER:\n'+run['response']+'\nRubric: '+item.get('rubric',''))
            while True:
                value=input('Score relevance, completeness and correctness 0..1 (e.g. 1,.8,.9), or skip: ').strip()
                if value.lower()=='skip':return None
                try:
                    scores=[float(v) for v in value.split(',')]
                    if len(scores)==3 and all(0<=s<=1 for s in scores):return sum(scores)/3
                except ValueError:pass
                print('Enter three numbers between 0 and 1, separated by commas.')
        if not run_benchmark(e,args.dataset,args.experiment,args.split,args.modes,args.namespace,args.seed,args.limit,feedback if args.split=='train' and not cfg.get('automatic_proxy_rewards') else None):sys.exit(2)
if __name__=='__main__':
    try:main()
    except (ValueError,APIError) as exc:print('Error:',exc,file=sys.stderr);sys.exit(1)
