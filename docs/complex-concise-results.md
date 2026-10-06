# Amended concise-format Complex extension results — 6 October 2026

Experiment `performance-complex-concise-01` completed **8/8 genuine cells** on two unchanged Complex tasks across four frozen controllers. All three health checks passed; the benchmark ran once, with no API failures, evaluation failures, needs_review outcomes, truncation or retry. All eight cells used one generation and one verification call: 16 calls, 16,605 reported tokens (7,904 generation; 8,701 verification). Seven responses incurred local quota waits, totalling 396.907 seconds; guards were not bypassed or weakened. Preflight used three additional calls, excluded from benchmark means.

The exact approved suffix from `complex-concise-instruction.txt` was applied only to generation, identically across controllers/attempts. Original queries reached analysis/retrieval/judging unchanged; reference rubrics and configuration stayed unchanged. The suffix SHA-256 (excluding its final newline) is `ea8dcb4c37e0677d98f23d3e9bf5afd1fbe59983eb2c7c3589458d7f18c3b2f7`. Actual generation-prompt hashes and suffix text/hash are stored per run; the new experiment signature includes the suffix hash, rejecting changed conditions on resume. Legacy experiment signatures remain untouched.

**Format deviation:** all eight answers exceeded the instructed 300-word ceiling: 305–502 whitespace-delimited words (mean 411.375). This is the amended **concise-instruction condition**, not proof of 250–300-word output compliance. No post-hoc truncation, rewriting, exclusion or rerunning was used to manufacture compliance. The substantive original rubric was used for grading; verbosity compliance is reported separately.

## Quality review and limitations

Only these eight genuinely completed answers received new grades. Query/rubric/answer exports were reviewed under blind IDs and the relevance/completeness/correctness scores were fixed before reading the mapping. Scores were imported as `blinded_assistant`, not human grading. Project context and knowledge of execution limit blinding; this is subjective assistant review, not independent validation. Dimension scores and response-specific reasons remain in local grading exports and run records. No historical truncated response was graded and no reward was applied.

The fixed operational judge scored every answer 1.0. Subsequent assistant rubric review found substantive problems: invented numerical constraints, unsupported latency/privacy guarantees, network-dependent designs for an offline task, and incorrect technical claims. All four caching answers met the provisional 0.75 rubric floor; all four offline-retrieval answers fell below it. This discrepancy demonstrates a limitation of the operational judge on these tasks; a pipeline `completed` status does not establish factual correctness or benchmark adequacy. No judge parameters or calibration were changed.

## Separate Complex-cohort controller comparison

All controllers initially selected tier 3 (GPT-OSS-120B) for both queries. Tier-3 generation share is 100%, verification rate 100%, retrieval/escalation rates 0%, mean calls 2. Identical selected models mean observed token/quality variation cannot be attributed to different routing choices; stochastic generation, evaluator output and service timing remain confounders.

| Controller | Queries | Mean trajectory tokens | Active seconds | Wall seconds | Assistant Q | Assistant pass | Token reduction vs baseline | Quality delta vs baseline |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Formula | 2 | 1989.00 | 3.537 | 60.304 | 0.6667 | 50% | 2.952% | −0.1000 |
| Online | 2 | 2133.50 | 3.542 | 60.340 | 0.7333 | 50% | −4.099% | −0.0333 |
| Hybrid | 2 | 2130.50 | 3.514 | 31.772 | 0.6000 | 50% | −3.952% | −0.1667 |
| Always-Strongest | 2 | 2049.50 | 3.320 | 59.951 | 0.7667 | 50% | 0% | 0 |

Formula's small token reduction coincides with lower rubric quality and slower active service time; Online/Hybrid used more tokens than baseline with lower rubric quality. No adaptive advantage, quality equivalence, superiority, significance or convergence is established. Hybrid's shorter wall time mostly reflects quota/order effects. INR 0 remains the confirmed free-plan monetary record, not measured compute cost. Tokens include verification and are not FLOPs.

## Descriptive complexity comparison

| Complexity | Prompt condition/cohort | Unique queries | Responses | Mean C | Tokens | Active seconds | Wall seconds | Calls | Assistant Q | Initial T1/T2/T3 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Simple | Original Phase 1 | 2 | 8 | 0.1912 | 309.75 | 1.132 | 4.123 | 1 | 0.9917 | 12.5% / 37.5% / 50% |
| Moderate | Original Phase 1 | 2 | 8 | 0.3849 | 479.50 | 1.813 | 11.741 | 1 | 0.9750 | 0% / 37.5% / 62.5% |
| Complex | Amended concise-format extension | 2 | 8 | 0.7989 | 2075.625 | 3.479 | 53.092 | 2 | 0.6917 | 0% / 0% / 100% |

The two original Phase 1 groups retain their original data/grades; historical `performance-complex-01` failures/truncated/evaluation-unavailable attempts are excluded from this successful amended cohort and remain preserved separately. Different prompt conditions and collection times make this a **descriptive cross-cohort comparison, not a controlled causal estimate of complexity effects**. Complex calls also include verification, unlike the observed original Simple/Moderate calls. Thus the token increase cannot be attributed solely to generation difficulty. Only two independent questions per group were evaluated; eight response cells are not eight independent questions.

## Artifacts and reproducibility

Original Phase 1 artifacts were not overwritten. New directories:

- `outputs/performance-complex-concise-01-report/`: existing raw/report exports.
- `outputs/performance-complex-concise-01-grades/`: assistant grading CSV/key (ignored; keep the mapping away from independent graders).
- `outputs/performance-analysis-concise/`: separate amended-cohort tables/graphs.
- `outputs/performance-analysis-concise-combined/`: explicitly labelled descriptive tables/graphs combining original and amended cohorts.

Both analysis directories contain `performance_metrics.csv`, `controller_comparison.csv`, `complexity_analysis.csv`, `controller_by_complexity.csv`, `cohort_controller_comparison.csv`, `reliability.json`, and `tables.md`. The CSVs include `Prompt condition/cohort`; amended response counts/word counts/over-300 counts are included. Token savings = 100×(1−controller mean tokens/baseline mean tokens); Q delta = controller mean Q−baseline mean Q. Means use fully completed query pairs and recorded counts only.

Graph pairs (300-DPI PNG and SVG) in each directory: `01_tokens`, `02_latency`, `03_quality_tokens`, `04_complexity_tokens`, `05_complexity_tiers`, `06_behaviour`. Combined graphs explicitly note the amended Complex condition and descriptive/non-causal interpretation. The behaviour graph is now meaningful because Complex verification occurred; original observed tool rates remain zero.

```powershell
.\.venv\Scripts\python.exe -m aai.cli report --experiment performance-complex-concise-01 --folder outputs/performance-complex-concise-01-report
.\.venv\Scripts\python.exe scripts/analyze_performance.py --experiment performance-complex-concise-01 --output outputs/performance-analysis-concise
.\.venv\Scripts\python.exe scripts/analyze_performance.py --extension-experiment performance-complex-concise-01 --output outputs/performance-analysis-concise-combined
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Execution command (historical record, **do not rerun merely to reproduce reports**): `python -m aai.cli benchmark --dataset data/performance-extension.jsonl --experiment performance-complex-concise-01 --split test --namespace default__frozen__phase1-test-fast --generation-format-file docs/complex-concise-instruction.txt`.

## Implementation and preservation audit

Minimal optional suffix support was added in `aai/pipeline.py`, `aai/experiments.py`, `aai/cli.py`; associated tests in `tests/test_pipeline.py`, `tests/test_experiments.py`. `scripts/analyze_performance.py` records condition labels, validates suffix provenance, reports format adherence and labels plots. Configuration/model/query/rubric/judge/retrieval/escalation parameters were not changed. The amended runner stops on incomplete/structural outcomes rather than repeatedly retrying. Existing safe local waiting behaviour remains intact.

34 tests passed before inference; the final suite has 35 tests including structural-stop coverage. All pre-existing run payloads, states and configuration/dataset/instruction bytes match the pre-run audit. New frozen snapshots equal their original Phase 1 source states; all eight learning flags are false, all rewards null. SQLite integrity is `ok`; `calibrated=false`. New benchmark/signature/snapshot/call records and eight assistant grades were added only for this cohort. No commit or push was made.
