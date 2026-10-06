"""Read-only paired Phase 1 analysis. No inference, grading, or state writes."""
import argparse
import csv
import hashlib
import json
import os
import sqlite3
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODES = ('formula', 'online', 'hybrid', 'baseline')
LABELS = ('Formula', 'Online', 'Hybrid', 'Always-Strongest')
LEVELS = ('Simple', 'Moderate', 'Complex')


def mean(values):
    values = [v for v in values if v is not None]
    return statistics.mean(values) if values else None


def select(rows):
    latest = {}
    for r in sorted(rows, key=lambda r: (r['created'], r['id'])):
        latest[r['metadata']['query_id'], r['mode']] = r
    paired = sorted({q for q, _ in latest if all(
        (q, m) in latest and latest[q, m]['status'] == 'completed' for m in MODES)})
    return list(latest.values()), [latest[q, m] for q in paired for m in MODES]


def summarize(rows):
    def avg(k):
        return mean([r['metrics'].get(k) for r in rows])
    def rate(fn):
        return mean([int(fn(r)) for r in rows])
    def quality(source, dimension=None):
        return mean([(r['benchmark_quality']['dimensions'].get(dimension) if dimension else r['benchmark_quality']['score'])
                     for r in rows if r.get('benchmark_quality', {}).get('source') == source])
    conditions=sorted({('Amended concise-format Complex extension' if r.get('generation_format') else 'Original Phase 1 prompt') for r in rows})
    result = {'Prompt condition/cohort': '; '.join(conditions) if conditions else 'Unmeasured',
              'queries': len({r['metadata']['query_id'] for r in rows}), 'responses': len(rows),
              'mean_complexity': mean([r['analysis']['complexity'] for r in rows])}
    amended=[r for r in rows if r.get('generation_format')]
    result['amended_format_responses']=len(amended)
    result['amended_mean_response_words']=mean([len(r['response'].split()) for r in amended])
    result['amended_responses_over_300_words']=sum(len(r['response'].split())>300 for r in amended) if amended else None
    for k in ('input_tokens', 'output_tokens', 'total_tokens'):
        # Component counts must exist for every call; pipeline sums alone mask missing usage.
        eligible = [r for r in rows if r['calls'] and all(c['status'] == 'ok' and c.get(k) is not None for c in r['calls'])]
        result['mean_' + k] = mean([sum(c[k] for c in r['calls']) for r in eligible])
        result[k + '_coverage'] = len(eligible)
    for k in ('active_latency_seconds', 'wall_latency_seconds', 'quota_wait_seconds', 'api_latency_seconds',
              'api_calls', 'generation_calls', 'verification_calls', 'actual_cost_inr'):
        result['mean_' + k] = avg(k)
    for i in range(3):
        result[f'tier{i+1}_selection_rate'] = rate(lambda r: r['decision']['initial_tier'] == i)
    generations = sum(r['metrics']['generation_calls'] for r in rows)
    result['tier3_generation_share'] = sum(r['metrics']['tier3_generation_calls'] for r in rows)/generations if generations else None
    result.update(retrieval_request_rate=rate(lambda r: r['analysis']['retrieval_required']),
                  retrieval_success_rate=rate(lambda r: r['retrieval']['status'] == 'retrieved'),
                  verification_rate=rate(lambda r: r['metrics']['verification_calls'] > 0),
                  escalation_rate=rate(lambda r: r['metrics']['escalations'] > 0))
    for source, label in (('blinded_assistant', 'assistant'), ('blinded_human', 'human')):
        scored = [r for r in rows if r.get('benchmark_quality', {}).get('source') == source]
        result[label + '_scored'] = len(scored)
        result['mean_' + label + '_quality'] = quality(source)
        for d in ('relevance', 'completeness', 'correctness'):
            result['mean_' + label + '_' + d] = quality(source, d)
        result[label + '_pass_rate'] = mean([int(r['benchmark_quality']['score'] >= r['config']['acceptance']) for r in scored])
    result['feedback_updates'] = sum(bool(r.get('reward')) for r in rows)
    result['mean_recorded_reward'] = mean([r['reward']['value'] for r in rows if r.get('reward')])
    return result


def write_csv(path, rows):
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def table(rows, fields):
    def fmt(v):
        return 'unmeasured' if v is None else f'{v:.4f}' if isinstance(v, float) else str(v)
    return '| ' + ' | '.join(fields) + ' |\n|' + '|'.join(['---'] * len(fields)) + '|\n' + '\n'.join(
        '| ' + ' | '.join(fmt(r[k]) for k in fields) + ' |' for r in rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db', type=Path, default=ROOT/'outputs/runs.sqlite')
    p.add_argument('--experiment', default='phase1-test-fast')
    p.add_argument('--extension-experiment', help='Separately identified extension cohort; original results remain unchanged')
    p.add_argument('--output', type=Path, default=ROOT/'outputs/performance-analysis')
    args = p.parse_args()
    with sqlite3.connect(args.db.resolve().as_uri() + '?mode=ro', uri=True) as db:
        allrows = [json.loads(v) for (v,) in db.execute('SELECT payload FROM runs ORDER BY created,id')]
        states = {n: json.loads(v) for n, v in db.execute('SELECT name,payload FROM states')}
        integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
    experiments = [args.experiment] + ([args.extension_experiment] if args.extension_experiment else [])
    raw = [r for r in allrows if r.get('metadata', {}).get('experiment') in experiments]
    if not raw:
        raise ValueError('Experiment has no records')
    latest, paired = [], []
    cohorts = []
    for name in experiments:
        cohort_raw = [r for r in raw if r['metadata']['experiment'] == name]
        cohort_latest, cohort_paired = select(cohort_raw)
        latest.extend(cohort_latest); paired.extend(cohort_paired)
        signature = states.get('experiment:' + name)
        planned = None
        if signature:
            paths = [ROOT/'data/benchmark.jsonl', ROOT/'data/performance-extension.jsonl']
            path = next((path for path in paths if hashlib.sha256(path.read_bytes()).hexdigest() == signature['dataset_hash']), None)
            if path is None:
                raise ValueError('Cannot determine planned coverage: unknown dataset hash')
            planned = sum(json.loads(s)['split'] == signature['split'] for s in path.read_text(encoding='utf-8').splitlines() if s.strip())
            if signature.get('limit'): planned = min(planned, signature['limit'])
            planned *= len(signature['modes'])
        cohorts.append({'experiment': name, 'planned_cells': planned, 'attempted_cells': len(cohort_latest),
                        'completed_cells': sum(r['status'] == 'completed' for r in cohort_latest),
                        'paired_queries': len(cohort_paired)//4, 'all_attempt_statuses': dict(Counter(r['status'] for r in cohort_raw))})
    if not paired:
        raise ValueError('No fully completed four-controller query pairs')
    for r in raw:
        if r['metadata']['split'] != 'test' or r['learning_enabled'] or r.get('reward'):
            raise ValueError('Expected frozen held-out runs')
        c = r['config']['complexity']; score = r['analysis']['complexity']
        level = 'Simple' if score < c['low'] else 'Complex' if score >= c['high'] else 'Moderate'
        if level != r['analysis']['complexity_level']:
            raise ValueError('Logged complexity class disagrees with saved configuration')
        if r.get('generation_format'):
            fmt=r['generation_format'];signature=states['experiment:'+r['metadata']['experiment']]
            if hashlib.sha256(fmt['instruction'].encode()).hexdigest()!=fmt['sha256'] or fmt['sha256']!=signature.get('generation_suffix_sha256'):
                raise ValueError('Generation format provenance mismatch')
        if r['mode'] in ('online', 'hybrid'):
            state = states[r['decision']['state_key']]
            if hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest() != r['decision']['state_hash']:
                raise ValueError('Frozen policy differs from decision snapshot')
    comparisons = [dict(controller=label, **summarize([r for r in paired if r['mode'] == m])) for m, label in zip(MODES, LABELS)]
    base = comparisons[-1]
    for row in comparisons:
        row['token_reduction_vs_baseline_percent'] = 100*(1-row['mean_total_tokens']/base['mean_total_tokens'])
        row['assistant_quality_delta_vs_baseline'] = (row['mean_assistant_quality']-base['mean_assistant_quality']) if row['mean_assistant_quality'] is not None and base['mean_assistant_quality'] is not None else None
    complexity = [dict(complexity=level, **summarize([r for r in paired if r['analysis']['complexity_level'] == level])) for level in LEVELS]
    cross = [dict(complexity=level, controller=label, **summarize([r for r in paired if r['analysis']['complexity_level'] == level and r['mode'] == m])) for level in LEVELS for m, label in zip(MODES, LABELS)]
    out = args.output; out.mkdir(parents=True, exist_ok=True)
    for filename, rows in [('controller_comparison.csv', comparisons), ('complexity_analysis.csv', complexity), ('controller_by_complexity.csv', cross), ('performance_metrics.csv', comparisons)]:
        write_csv(out/filename, rows)
    write_csv(out/'cohort_controller_comparison.csv', [dict(experiment=name, controller=label, **summarize([r for r in paired if r['metadata']['experiment'] == name and r['mode'] == mode])) for name in experiments for mode, label in zip(MODES, LABELS)])
    infra = ('api_error', 'quota_paused', 'evaluation_unavailable')
    reliability = {'experiment': args.experiment, 'cohorts': cohorts, 'planned_cells': sum(c['planned_cells'] or 0 for c in cohorts),
                   'latest_completed': sum(r['status'] == 'completed' for r in latest), 'latest_attempted': len(latest),
                   'all_attempt_statuses': dict(Counter(r['status'] for r in raw)), 'attempt_records': len(raw),
                   'infrastructure_failure_rate': sum(r['status'] in infra for r in raw)/len(raw),
                   'all_attempt_api_calls': sum(r['metrics']['api_calls'] for r in raw),
                   'all_attempt_reported_tokens': sum(r['metrics']['total_tokens'] for r in raw),
                   'unknown_token_calls': sum(c.get('total_tokens') is None for r in raw for c in r['calls']),
                   'sqlite_integrity': integrity, 'config_hashes': sorted({r['config_hash'] for r in raw}),
                   'source_hashes': sorted({r['source_hash'] for r in raw}),
                   'dataset_hashes': sorted({r['metadata']['dataset_hash'] for r in raw}),
                   'frozen_policy_audit': {m: {'version': next(r['decision']['state_version'] for r in paired if r['mode'] == m),
                                             'counts': next(r['decision']['state_snapshot']['counts'] for r in paired if r['mode'] == m),
                                             'unchanged': True} for m in ('online', 'hybrid')},
                   'training_feedback': [{'mode': m, 'updates': sum(bool(r.get('reward')) for r in allrows if r['mode'] == m and r.get('metadata', {}).get('split') == 'train'),
                                          'mean_recorded_reward': mean([r['reward']['value'] for r in allrows if r['mode'] == m and r.get('metadata', {}).get('split') == 'train' and r.get('reward')])} for m in ('online', 'hybrid')]}
    (out/'reliability.json').write_text(json.dumps(reliability, indent=2)+'\n', encoding='utf-8')
    (out/'tables.md').write_text(table(comparisons, ['controller', 'Prompt condition/cohort', 'queries', 'mean_total_tokens', 'mean_active_latency_seconds', 'mean_assistant_quality', 'tier3_generation_share'])+'\n\n'+table(complexity, ['complexity', 'Prompt condition/cohort', 'queries', 'responses', 'mean_complexity', 'mean_total_tokens', 'mean_active_latency_seconds', 'mean_assistant_quality'])+'\n', encoding='utf-8')
    (out/'moe_comparison.md').write_text((ROOT/'docs/moe-comparison.md').read_text(encoding='utf-8'), encoding='utf-8')
    plot(out, comparisons, complexity, extension=bool(args.extension_experiment))
    print((out/'tables.md').read_text(encoding='utf-8'))
    print(json.dumps(reliability, indent=2))


def plot(out, comparisons, complexity, extension=False):
    os.environ.setdefault('MPLCONFIGDIR', str(out.resolve()/'matplotlib-cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 12, 'axes.spines.top': False, 'axes.spines.right': False, 'svg.hashsalt': 'phase1-performance'})
    folder = out/'graphs'; folder.mkdir(exist_ok=True)
    colors = ['#2369a0', '#32936f', '#bb7735', '#7855a3']
    n = comparisons[0]['queries']
    def save(fig, name):
        cohort_label = 'Phase 1 + separate Complex extension' if extension else 'Frozen held-out pilot'
        concise=any('Amended concise' in r['Prompt condition/cohort'] for r in comparisons)
        if concise: cohort_label='Amended concise-format Complex cohort'+(' + original Phase 1' if extension else '')
        fig.text(.5, .01, f'{cohort_label}: {n} paired queries; descriptive results; assistant grades', ha='center', fontsize=9)
        if concise and extension: fig.text(.5,.045,'Complex used amended concise format: descriptive comparison, not a controlled causal estimate of complexity effects.',ha='center',fontsize=8)
        fig.tight_layout(rect=(0, .09 if concise and extension else .05, 1, 1)); fig.savefig(folder/(name+'.png'), dpi=300); fig.savefig(folder/(name+'.svg'), metadata={'Date': None}); plt.close(fig)
    for field, title, unit, name in [('mean_total_tokens', 'Mean provider-reported total tokens by controller', 'Tokens per response (all calls)', '01_tokens'), ('mean_active_latency_seconds', 'Mean active service latency by controller', 'Seconds per response (quota waits excluded)', '02_latency')]:
        fig, ax = plt.subplots(figsize=(9, 5)); values = [r[field] for r in comparisons]
        bars = ax.bar(LABELS, values, color=colors); ax.bar_label(bars, fmt='%.2f', padding=4)
        ax.set(title=title, xlabel=f'Controller (n={n} each)', ylabel=unit, ylim=(0, max(values)*1.2)); save(fig, name)
    fig, ax = plt.subplots(figsize=(9, 5))
    for r, color in zip(comparisons, colors):
        if r['mean_assistant_quality'] is not None:
            ax.scatter(r['mean_total_tokens'], r['mean_assistant_quality'], color=color, s=90, label=r['controller'])
    ax.axhline(.75, color='gray', linestyle='--', label='Provisional acceptance floor')
    ax.set(title='Quality and token usage (assistant rubric review)', xlabel='Mean total tokens per response', ylabel='Mean rubric quality (0–1)', xlim=(0, max(r['mean_total_tokens'] for r in comparisons)*1.2), ylim=(0, 1.05)); ax.legend(fontsize=10); save(fig, '03_quality_tokens')
    fig, ax = plt.subplots(figsize=(9, 5))
    for i, r in enumerate(complexity):
        if r['responses']:
            bar = ax.bar(i, r['mean_total_tokens'], color='#2369a0'); ax.bar_label(bar, fmt='%.2f')
        else: ax.text(i, 15, 'No observations', ha='center')
    ax.set_xticks(range(3), [f"{r['complexity']}\n{r['queries']} queries / {r['responses']} responses" for r in complexity])
    ax.set(title='Token usage by logged query complexity (controllers pooled equally)', xlabel='Existing complexity category', ylabel='Mean total tokens per response'); ax.set_ylim(bottom=0); save(fig, '04_complexity_tokens')
    fig, ax = plt.subplots(figsize=(9, 5)); bottoms = [0]*3
    for tier, color in zip(range(1, 4), colors):
        values = [100*(r[f'tier{tier}_selection_rate'] or 0) for r in complexity]
        ax.bar(range(3), values, bottom=bottoms, label=f'Tier {tier}', color=color); bottoms = [a+b for a,b in zip(bottoms, values)]
    ax.text(2, 5, 'No observations', ha='center') if not complexity[2]['responses'] else None
    ax.set_xticks(range(3), [r['complexity'] for r in complexity]); ax.set(title='Initial tier selection by complexity (controllers pooled equally)', xlabel='Existing complexity category', ylabel='Share of completed responses (%)', ylim=(0, 105)); ax.legend(); save(fig, '05_complexity_tiers')
    behaviors = ('retrieval_success_rate', 'verification_rate', 'escalation_rate')
    if any(r[k] for r in comparisons for k in behaviors):
        fig, ax = plt.subplots(figsize=(9, 5))
        for i, (key, label) in enumerate(zip(behaviors, ('Retrieval success', 'Verification', 'Escalation'))):
            ax.bar([x+(i-1)*.25 for x in range(4)], [100*(r[key] or 0) for r in comparisons], width=.25, label=label, color=colors[i])
        ax.set_xticks(range(4), LABELS); ax.set(title='Recorded framework behaviour by controller', xlabel='Controller', ylabel='Completed responses with behaviour (%)', ylim=(0, 105)); ax.legend(); save(fig, '06_behaviour')


if __name__ == '__main__':
    main()
