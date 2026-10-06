# Phase 1 performance analysis

The original measurements below remain unchanged. The completed, separately labelled amended Complex cohort and descriptive three-group comparison are documented in [complex-concise-results.md](complex-concise-results.md); this supersedes earlier statements that all Complex coverage is unmeasured. Historical failed extension attempts remain preserved separately.

This page describes the original Phase 1 reporting cohort. Its configuration (`calibrated=false`), benchmark, answers, grades and learned states remain unchanged. The initial analysis used no new inference. The later original-prompt Complex extension stopped without a fully completed pair; its history is in [the attempt record](complex-extension-attempt.md). The subsequent amended concise-format cohort completed 8/8 cells, as documented in [its separate results](complex-concise-results.md). Optional generation-format support was added for that new cohort without changing the original inference condition. Source for the original tables below: `outputs/runs.sqlite`, experiment `phase1-test-fast`; regenerated through read-only SQLite access. The script checks logged complexity classes against saved thresholds and frozen policy hashes. Prior aggregates in `docs/phase1-results.json` agree with the four-controller means.

## Reproduce and artifacts

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-analysis.txt
.\.venv\Scripts\python.exe scripts/analyze_performance.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Use `--db`, `--experiment`, `--output` for alternative inputs; default is the original held-out experiment. Raw local database is necessary for dimensions and complexity analysis; the tracked aggregate alone cannot reconstruct these. Outputs are ignored intentionally. No model loading/network calls occur in the analysis script.

Generated under `outputs/performance-analysis/`: `performance_metrics.csv` and `controller_comparison.csv` (same wide controller table for convenient export), `complexity_analysis.csv`, `controller_by_complexity.csv`, `reliability.json`, `tables.md`, `moe_comparison.md`, and `graphs/01_tokens`, `02_latency`, `03_quality_tokens`, `04_complexity_tokens`, `05_complexity_tiers` (each PNG at 300 DPI and SVG). Architectural comparison source is [moe-comparison.md](moe-comparison.md).

## Metric definitions

Efficiency/quality/routing means use the latest **completed**, fully paired query IDs shared by all four controllers. There are four independent query IDs and 16 responses, not 16 independent questions. Complexity pooling weights controllers equally. Empty groups stay blank/unmeasured. Component token coverage is reported separately; no missing count is treated as zero. Quality provenance stays separate.

| Metric / output columns | Calculation | Unit/range | Relevance |
|---|---|---|---|
| queries, responses | distinct query IDs; completed paired cells | count | sample size |
| mean_complexity | mean recorded C | 0–1 | logged demand estimate |
| mean input/output/total tokens | mean per-response sum of all successful call counts, only when every call reports the component | provider tokens | trajectory resource proxy including verification/escalation |
| token component coverage | eligible responses for each component | count | prevents unknown usage being hidden |
| mean active latency | mean recorded wall time minus quota waits | seconds | service latency with local processing/network/provider time |
| mean wall latency | mean elapsed whole-run time | seconds | user-observed delay including waiting |
| mean quota wait | mean summed recorded call waits | seconds | identifies rate-limit overhead |
| mean API latency | mean summed call durations | seconds | provider/network component, not pure model speed |
| mean API/generation/verification calls | mean recorded call counts by purpose | calls/response | extra framework work |
| mean actual cost | mean logged confirmed free-plan charge | INR | recorded monetary charge; not compute cost |
| tier 1/2/3 selection rates | initial decisions at tier / completed responses | 0–1 | query routing; not final-tier selection |
| tier3_generation_share | tier-3 generation calls / all generation calls | 0–1 | strongest configured tier use including escalation |
| retrieval request / success rates | required / retrieved runs divided by responses | 0–1 | separates demand from evidence availability |
| verification rate | runs with at least one verification call / responses | 0–1 | actual attempted judging, not merely a policy flag |
| escalation rate | runs with recorded escalation count > 0 / responses | 0–1 | additional model attempts |
| assistant/human scored | completed responses with corresponding grading provenance | count | grading coverage |
| mean relevance/completeness/correctness | means of stored rubric dimension scores, separately by provenance | 0–1 | task satisfaction and correctness proxy |
| mean assistant/human quality | mean stored equal-weight three-dimension quality | 0–1 | comparison with quality retained |
| assistant/human pass rate | graded responses with Q ≥ saved acceptance (0.75) / graded responses | 0–1 | provisional adequacy, not an exact-answer accuracy test |
| feedback_updates, mean_recorded_reward | runs with applied reward; mean stored reward over those runs | count; reward | controller learning evidence; unknown if no feedback |
| token reduction vs baseline | 100 × (1 − controller mean tokens / baseline mean tokens) | percent | resource trade-off without inventing a composite score |
| assistant quality delta vs baseline | controller mean Q − baseline mean Q | quality points | contextualizes token reduction |
| planned/latest attempted/latest completed cells | experiment signature planned cells; latest cell records; completed records | count | coverage; completion = completed/planned (16/16 here) |
| all-attempt status counts | count every historical attempt by recorded status | count | reliability and resume history |
| infrastructure failure rate | (api_error + quota_paused + evaluation_unavailable) attempts / all attempts | 0–1 | separate infrastructure/evaluator availability from answer quality |
| all-attempt calls/reported tokens/unknown-token calls | sums over all attempts; count calls missing total usage | calls/tokens/count | retained retry overhead; reported total is a lower bound when missing |
| training feedback updates/mean reward | recorded benchmark train feedback only, by mode | count/reward | learning audit without mixing training into held-out quality |
| frozen version/counts/unchanged | logged decision snapshot compared with stored frozen state | version/count/bool | verifies no held-out learning |

No precision, recall, F1, FLOPs, parameter-token score, or invented cost estimates are reported.

## Measured controller results and derived trade-off

| Controller | Queries | Mean tokens | Active s | Wall s | Assistant Q | Token reduction | Q delta | Tier-3 generation |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Formula | 4 | 307.75 | 1.165 | 1.165 | 0.9750 | 31.535% | −0.0083 | 0% |
| Online | 4 | 372.25 | 1.081 | 8.259 | 1.0000 | 17.186% | +0.0167 | 25% |
| Hybrid | 4 | 449.00 | 1.653 | 8.604 | 0.9750 | 0.111% | −0.0083 | 100% |
| Always-Strongest | 4 | 449.50 | 1.990 | 13.701 | 0.9833 | 0% | 0 | 100% |

Every controller has four assistant-scored answers, pass rate 100%, human coverage zero, mean one generation/API call, INR 0 recorded cost, and retrieval/verification/escalation rates zero. No held-out reward/state updates occurred. Online frozen version 3 counts [1,1,1]; Hybrid version 2 counts [1,1,0]. Hybrid repeatedly chooses the untried tier 3 because cold-start state remains frozen; this is not converged adaptation. Two recorded benchmark training updates per learned mode have mean rewards Online 0.990743 and Hybrid 0.992345; Online's extra prior manual update explains version 3. Reward is Q − .15 min(T/6000,1) − .10 min(L/60,1) − .40 I(Q<.75). No held-out reward was computed or applied.

Formula and Online used fewer reported tokens while meeting the assistant rubric floor on these four questions. Hybrid had essentially baseline token use. Quality changes are reported alongside resource reductions; there is no demonstrated equivalence, superiority, significance, convergence or generalization. Wall time highlights quota-wait confounding. All-attempt completion is 16/18 (88.89%); final planned coverage is 16/16. Two historical API-error attempts (11.11%) are not scored as incorrect answers. There were 18 calls and 6,314 reported tokens; two failed-call usages are unknown.

## Existing complexity analysis

The system already defines Simple C<0.32, Moderate 0.32≤C<0.65, Complex C≥0.65. No analysis-only thresholds were introduced. C=.70H+.30S; H=.10 length+.30 reasoning+.35 requirements+.25 technical. S uses normalized positive cosine weights over the five category demand scores. Semantic task is the highest prototype-centroid cosine, not a probability or ground-truth label. See DESIGN.md for feature/routing definitions. Complexity does not mechanically dictate a tier: technical/reasoning overrides and LinUCB decisions can select stronger models for Simple queries.

| Complexity | Unique queries | Responses | Mean C | Mean tokens | Active s | Calls | T1 % | T2 % | T3 % | Retrieval/verification/escalation | Assistant Q |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| Simple | 2 | 8 | 0.1912 | 309.75 | 1.1316 | 1 | 12.5 | 37.5 | 50 | 0% / 0% / 0% | 0.9917 |
| Moderate | 2 | 8 | 0.3849 | 479.50 | 1.8132 | 1 | 0 | 37.5 | 62.5 | 0% / 0% / 0% | 0.9750 |
| Complex | 0 | 0 | unmeasured | unmeasured | unmeasured | unmeasured | unmeasured | unmeasured | unmeasured | unmeasured | unmeasured |

Controller-by-complexity token/latency data are generated in `controller_by_complexity.csv`. Two queries per observed group only support an illustrative table. The pooled difference cannot establish a causal effect of complexity, since tasks and answers differ.

| Complexity | Formula tokens / s | Online tokens / s | Hybrid tokens / s | Always-Strongest tokens / s |
|---|---:|---:|---:|---:|
| Simple (2 queries) | 212.5 / 1.103 | 261.5 / 0.770 | 371 / 1.257 | 394 / 1.397 |
| Moderate (2 queries) | 403 / 1.227 | 483 / 1.392 | 527 / 2.050 | 505 / 2.583 |
| Complex | unmeasured | unmeasured | unmeasured | unmeasured |

## Graph interpretation and limits

01 compares reported whole-trajectory tokens; 02 compares active service time; 03 shows quality and tokens with the full 0–1 quality scale and provisional floor; 04 shows only observed groups, explicitly marking missing Complex; 05 shows initial tier shares including the baseline, with an empty Complex group. Bars start at zero; empty categories are not measured zeros. PNGs suit reports/PPT, SVGs allow vector export. Graph 06 is omitted because all held-out retrieval, verification and escalation rates are zero; the table reports these facts without a redundant all-zero graph.

These are descriptive point estimates, not uncertainty bounds. Four queries, one seed, mixed providers/tokenizers, mutable model aliases, incomplete training, quota waits and limited assistant blinding restrict inference. Independent human held-out grading is absent. Tier ordering is provisional. No calibration changes, monetary savings claims, or assertions that fewer tokens imply better answers are warranted. This establishes reporting and API-routing feasibility only.

## Additional complexity coverage

The following records the initial coverage assessment and historical extension plan, not a request to resume inference. The guide-requested extension is now complete under the separately approved amended condition; use [complex-concise-results.md](complex-concise-results.md) for the final comparison.

Existing measured held-out groups contain two Simple and two Moderate queries, no Complex. Keep the original `--limit 4` experiment frozen. Additional Complex measurements, if required, belong to a separate extension, with no controller tuning and separately reported collection dates. Minimum balanced illustrative coverage is two held-out Complex queries (eight new controller cells) alongside the original two-per-group coverage; this is still not statistically persuasive. Draft queries and offline scores are provided separately once checked against the existing analyzer. Each extension query should have a reference rubric fixed before inference. First run the existing three-call API health check, then use a new experiment ID and existing resume mechanism; pause on failures rather than repeated retries. Judging/escalation can require more than eight calls (up to 40 across two complex queries, plus three preflight calls). Do not claim Complex results until these are actually collected and graded.

Offline inspection of **all 20** existing benchmark queries with the cached pinned MiniLM found 16 Simple, four Moderate, zero Complex. Existing unmeasured test-05/07/08 are Simple and test-06 Moderate, so merely finishing that dataset cannot fill Complex. `data/performance-extension.jsonl` contains two new disjoint held-out queries with fixed rubrics. Offline scores are 0.750216 and 0.847545 (both Complex), selected for genuine multiple constraints/analysis requirements, not favorable controller outcomes. The extension was subsequently attempted and stopped without any completed response; no answer quality is assigned. Original benchmark/hash and train/test separation are preserved.

If the guide requires this extension, use the frozen policy namespace as source (never retrain), and retain separate results:

```powershell
.\.venv\Scripts\python.exe -m aai.cli check-apis
.\.venv\Scripts\python.exe -m aai.cli benchmark --dataset data/performance-extension.jsonl --experiment performance-complex-01 --split test --namespace default__frozen__phase1-test-fast
```

Proceed with the second command only if health checks pass. Repeating the exact benchmark command resumes failed cells; do not repeatedly run preflight on instability. Independently grade the eight new answers using existing blind export/import before any quality comparison. Report the extension separately because collection time and quota/provider conditions differ. The analysis defaults to the original benchmark; --extension-experiment adds a separately identified cohort and coverage table without changing Phase 1 records.
