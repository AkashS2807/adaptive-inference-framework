"""Paired experiments, blinded human grading, and coverage-aware summaries."""
import csv,hashlib,json,random,statistics,time
from pathlib import Path
from .controllers import MODES

def dataset(path):
    items=[json.loads(s) for s in Path(path).read_text(encoding='utf-8').splitlines() if s.strip()]
    ids=[q['id'] for q in items]
    if len(ids)!=len(set(ids)): raise ValueError('Dataset IDs must be unique')
    if not all(q.get('split') in ('pilot','train','test') and q.get('query') for q in items): raise ValueError('Each query needs split and query fields')
    return items

def run_benchmark(engine,path,experiment,split='test',modes=MODES,namespace='default',seed=42,limit=None,feedback_fn=None,retry_needs_review=False,generation_suffix=''):
    if generation_suffix and split!='test':
        raise ValueError('Generation format suffix requires frozen test evaluation')
    if retry_needs_review and split != 'test':
        raise ValueError('Retrying needs_review is restricted to frozen test evaluation')
    items=[q for q in dataset(path) if q['split']==split]
    if limit: items=items[:limit]
    if not items: raise ValueError('No queries in the selected split')
    dh=hashlib.sha256(Path(path).read_bytes()).hexdigest()
    signature={'dataset_hash':dh,'split':split,'modes':list(modes),'namespace':namespace,'seed':seed,'limit':limit,'config_hash':engine.cfg['hash']}
    if generation_suffix: signature['generation_suffix_sha256']=hashlib.sha256(generation_suffix.encode()).hexdigest()
    key='experiment:'+experiment;old=engine.store.state(key)
    if old and old!=signature: raise ValueError('Experiment ID already has different settings; use a new ID.')
    engine.store.save_state(key,signature)
    run_namespace=namespace
    if split=='test':
        from .analysis import analyze
        context=analyze(items[0]['query'],engine.semantic,engine.cfg)
        run_namespace=namespace+'__frozen__'+experiment
        for mode in ('online','hybrid'):
            dest=engine.controller.key(mode,context,run_namespace)
            if engine.store.state(dest) is None:
                source=engine.controller.key(mode,context,namespace)
                engine.store.save_state(dest,engine.store.state(source) or engine.controller.initial(len(context['context'])))
    existing=[r for r in engine.store.recent(100000) if r.get('metadata',{}).get('experiment')==experiment]
    terminal=('completed','evidence_unavailable') if retry_needs_review else ('completed','needs_review','evidence_unavailable')
    completed={(r['metadata']['query_id'],r['mode']) for r in existing if r['status'] in terminal}
    order=random.Random(seed)
    for q in items:
        current=list(modes);order.shuffle(current)
        for mode in current:
            if (q['id'],mode) in completed: continue
            metadata={'experiment':experiment,'query_id':q['id'],'split':split,'category':q['category'],'dataset_hash':dh,'reference_rubric':q.get('rubric',''),'order_seed':seed}
            kwargs={'generation_suffix':generation_suffix} if generation_suffix else {}
            r=engine.run(q['query'],mode,learning=(split=='train'),namespace=run_namespace,metadata=metadata,**kwargs)
            if split=='train' and feedback_fn and r['learning_enabled'] and not r.get('reward') and r['status'] in ('completed','needs_review'):
                quality=feedback_fn(r,q)
                if quality is not None: engine.controller.feedback(r,quality,'human_training')
            print(f'{q["id"]} | {mode} | {r["status"]} | calls={r["metrics"]["api_calls"]}',flush=True)
            if generation_suffix and (r['status'] not in ('completed',) or any('output_truncated' in a['evaluation'].get('basic',{}).get('issues',[]) for a in r['attempts'])):
                print('Amended cohort stopped on incomplete/structural outcome; no retry was made.',flush=True)
                return False
            if r['status'] in ('quota_paused','api_error','evaluation_unavailable'):
                print('Paused. Resolve the reported issue and repeat the same command to resume. Partial attempts remain logged.',flush=True)
                return False
    return True

def experiment_runs(store,name):
    allruns=[r for r in store.recent(100000) if r.get('metadata',{}).get('experiment')==name]
    # Latest attempt per cell. Earlier incomplete attempts remain in the raw DB/export.
    seen=set();result=[]
    for r in allruns:
        cell=(r['metadata']['query_id'],r['mode'])
        if cell not in seen: result.append(r);seen.add(cell)
    return result

def export_grades(store,name,folder):
    rows=experiment_runs(store,name);random.Random(712).shuffle(rows)
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);mapping={}
    fields=['blind_id','query','reference_rubric','response','relevance','completeness','correctness','notes']
    with (folder/'blind_grading.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for i,r in enumerate(rows,1):
            bid=f'answer-{i:04d}';mapping[bid]=r['id']
            w.writerow({'blind_id':bid,'query':r['analysis']['original'],'reference_rubric':r['metadata'].get('reference_rubric',''),'response':r['response']})
    (folder/'grading_key.json').write_text(json.dumps(mapping,indent=2),encoding='utf-8')
    return str(folder/'blind_grading.csv')

def import_grades(engine,folder,source='blinded_human'):
    if source not in ('blinded_human','blinded_assistant'):
        raise ValueError('Unknown grading source')
    folder=Path(folder);mapping=json.loads((folder/'grading_key.json').read_text(encoding='utf-8'));count=0
    with (folder/'blind_grading.csv').open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            if not all(row.get(k,'').strip() for k in ('relevance','completeness','correctness')): continue
            values=[float(row[k]) for k in ('relevance','completeness','correctness')]
            if not all(0<=v<=1 for v in values): raise ValueError('Scores must be 0..1')
            r=engine.store.get(mapping[row['blind_id']]);quality=sum(values)/3
            r['benchmark_quality']={'score':quality,'dimensions':dict(zip(('relevance','completeness','correctness'),values)),'source':source,'notes':row.get('notes','')}
            engine.store.save(r)
            if r['learning_enabled'] and not r.get('reward') and r['status'] in ('completed','needs_review'):
                engine.controller.feedback(r,quality,source)
            count+=1
    return count

def report(store,name,folder):
    rows=experiment_runs(store,name);folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    summary=[]
    for mode in MODES:
        group=[r for r in rows if r['mode']==mode]
        if not group: continue
        good=[r for r in group if r['status'] in ('completed','needs_review')]
        quality=[r['benchmark_quality']['score'] for r in good if r.get('benchmark_quality',{}).get('source')=='blinded_human']
        assistant=[r['benchmark_quality']['score'] for r in good if r.get('benchmark_quality',{}).get('source')=='blinded_assistant']
        def avg(k):return statistics.mean(r['metrics'][k] for r in good) if good else None
        counts=sum(r['metrics']['generation_calls'] for r in good)
        summary.append({'mode':mode,'cells_attempted':len(group),'completed_responses':len(good),'human_scored':len(quality),
          'mean_human_quality':statistics.mean(quality) if quality else None,
          'human_pass_rate':sum(q>=group[0]['config']['acceptance'] for q in quality)/len(quality) if quality else None,
          'assistant_scored':len(assistant),'mean_assistant_quality':statistics.mean(assistant) if assistant else None,
          'assistant_pass_rate':sum(q>=group[0]['config']['acceptance'] for q in assistant)/len(assistant) if assistant else None,
          'mean_active_seconds':avg('active_latency_seconds'),'mean_wall_seconds':avg('wall_latency_seconds'),
          'mean_total_tokens':avg('total_tokens'),'mean_actual_cost_inr':avg('actual_cost_inr'),'mean_api_calls':avg('api_calls'),
          'tier3_generation_share':sum(r['metrics']['tier3_generation_calls'] for r in good)/counts if counts else None,
          'retrieval_rate':sum(r['analysis']['retrieval_required'] for r in group)/len(group),
          'verification_rate':sum(r['metrics']['verification_calls']>0 for r in group)/len(group),
          'escalation_rate':sum(r['metrics']['escalations']>0 for r in group)/len(group)})
    if summary:
        with (folder/'summary.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
    categories=[]
    for category in sorted(set(r['metadata'].get('category','unknown') for r in rows)):
        for mode in MODES:
            group=[r for r in rows if r['metadata'].get('category','unknown')==category and r['mode']==mode]
            if not group:continue
            categories.append({'category':category,'mode':mode,'queries':len(group),
                'initial_tier1':sum(r['decision']['initial_tier']==0 for r in group),
                'initial_tier2':sum(r['decision']['initial_tier']==1 for r in group),
                'initial_tier3':sum(r['decision']['initial_tier']==2 for r in group),
                'incomplete':sum(r['status'] not in ('completed','needs_review') for r in group)})
    if categories:
        with (folder/'routing_by_category.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(categories[0]));w.writeheader();w.writerows(categories)
    (folder/'runs.jsonl').write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n',encoding='utf-8')
    # Retain failed/retried overhead separately; never silently erase quota consumption.
    raw=[r for r in store.recent(100000) if r.get('metadata',{}).get('experiment')==name]
    (folder/'all_attempts.jsonl').write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in raw)+'\n',encoding='utf-8')
    overhead={'all_attempt_api_calls':sum(r.get('metrics',{}).get('api_calls',0) for r in raw),'all_attempt_reported_tokens':sum(r.get('metrics',{}).get('total_tokens',0) for r in raw),'attempt_records':len(raw)}
    (folder/'usage.json').write_text(json.dumps(overhead,indent=2),encoding='utf-8')
    (folder/'README.txt').write_text('Descriptive pilot results only. Blank quality means ungraded, not zero. Compare identical completed query IDs; report missing cells and grading coverage. API latency includes provider/network differences. Tokens are a resource proxy, not FLOPs. Human and assistant grades are reported separately; assistant review is not independent human validation. Test policies are frozen. All-attempt overhead includes retries. Failed-call token consumption is unknown, not zero. Do not claim statistical superiority from this smoke benchmark.\n',encoding='utf-8')
    return summary
