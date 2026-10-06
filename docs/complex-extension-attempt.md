# Complex extension attempt — 6 October 2026

Historical record of the original-prompt extension. Do not resume it to reproduce reports. The guide-requested work was subsequently completed in the separately approved [amended concise-format cohort](complex-concise-results.md); failed and needs_review attempts below remain preserved.

All three API health checks succeeded: Gemini, GPT-OSS-20B and GPT-OSS-120B each returned `4`. Exactly three preflight requests were made. The authorized benchmark then used `data/performance-extension.jsonl`, experiment `performance-complex-01`, seed 42, test split, and source namespace `default__frozen__phase1-test-fast`. The runner copied the original frozen states into a new frozen namespace; learning remained disabled.

The first cell was Hybrid on Complex query 1, initially tier 3 (GPT-OSS-120B). Its one generation call failed with `API connection failed or timed out; no automatic retry was made.` The adapter does not retain the underlying exception, so this cannot be identified specifically as WinError 10054. The runner exited 1 and was **not retried**. No response completed, and no verification, escalation, grading, reward or learning update occurred.

Extension coverage: **0/8 completed cells, 1 attempted, 7 unattempted**. Failed-call tokens are unknown, not measured zero. This failure is infrastructure evidence, not answer-quality evidence. No failed response was graded; the original 16 assistant-reviewed responses retain their grades. Three preflight calls plus one extension request were made in this task.

Original run payloads, all pre-existing states and configuration bytes were verified unchanged against a pre-run audit. `calibrated=false`; SQLite integrity is `ok`. No commit or push was made. Raw failure/usage evidence remains in `outputs/performance-complex-01-report/`.

| Complexity | Completed paired queries | Responses | Mean complexity | Mean tokens | Active seconds | Assistant quality |
|---|---:|---:|---:|---:|---:|---:|
| Simple | 2 | 8 | 0.1912 | 309.75 | 1.1316 | 0.9917 |
| Moderate | 2 | 8 | 0.3849 | 479.50 | 1.8132 | 0.9750 |
| Complex | 0 | 0 | unmeasured | unmeasured | unmeasured | unmeasured |

Complex queries have prepared offline demand scores, but no completed resource or answer-quality measurements. The four-controller averages remain exactly as reported in [performance-analysis.md](performance-analysis.md). No new quality-efficiency or MoE conclusion is supported.

Reproduce original and separately labelled extension-aware reports:

```powershell
.\.venv\Scripts\python.exe -m aai.cli report --experiment performance-complex-01 --folder outputs/performance-complex-01-report
.\.venv\Scripts\python.exe scripts/analyze_performance.py
.\.venv\Scripts\python.exe scripts/analyze_performance.py --extension-experiment performance-complex-01 --output outputs/performance-analysis-extension
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Extension-aware outputs include `cohort_controller_comparison.csv` and per-cohort planned/attempted/completed counts in `reliability.json`; empty extension resource/quality means remain blank. The five PNG/SVG graph pairs are regenerated with sample labels read from data. Original and extension datasets remain separate, and no original measurements are overwritten in the database. Graph 06 remains unwarranted without completed behaviour data.

Across both cohorts, history contains 19 attempts, three API failures, 19 benchmark calls, and 6,314 reported tokens with three unknown-usage calls. Preflight calls remain separately logged and excluded from benchmark resource means. Original Phase 1 still has 16/16 final completion, while the extension has 0/8; pooling completion counts must not hide that distinction.

Validation: all 31 automated tests pass; repeated generation reproduces CSVs and PNG/SVG graphs byte-for-byte, PNGs decode, and analysis leaves database bytes unchanged. The remaining task is a future explicitly authorized resume after connectivity stabilizes. No additional retries were made in this session.

## Authorized resume — 6 October 2026

The same experiment, dataset, seed and namespace were resumed once without another preflight or a new experiment. Hybrid query 1 returned a truncated output (`output_truncated`), ending as `needs_review`: 1,707 reported tokens, one generation call, 4.070 active seconds. No judge call occurred because the structural check failed. Its operational score of zero is a structural-failure indicator, not an independently assigned benchmark grade. The preserved terminal cell will be skipped by the existing resume mechanism.

The next cell, Online query 1, failed with the same generic connection/timeout API error. The runner stopped (exit 1) and was not retried. Current latest-cell coverage: zero `completed`, one `needs_review`, one `api_error`, six unattempted cells, and zero fully paired queries. History retains three attempts (the first-session failure, Hybrid's truncated response, and Online's failure).

The raw experiment report was regenerated in `outputs/performance-complex-01-report/`. No grading or final comparison regeneration occurred because all eight responses have not completed. The original Simple/Moderate comparison and graphs remain applicable; no measured paired Complex comparison exists. Original Phase 1 run payloads, all pre-existing states and configuration bytes were rechecked unchanged; extension runs have learning disabled and no rewards. No controller changes, commit or push occurred. Earlier validation results above remain historical; tests were not rerun for this data-only resume and documentation update.

## Controlled resume after network change — 6 October 2026

All three existing health checks passed. One controlled benchmark invocation resumed the same experiment, dataset, seed and frozen namespace. An explicit `--retry-needs-review` option was added to the existing runner/CLI because its default resume treats needs_review as terminal. The option is restricted to test evaluation, preserves every previous attempt, and still skips genuinely completed cells. It does not change the experiment signature, inference prompts, model IDs, budgets, thresholds, rubrics, configuration or policies. Default resume behaviour remains unchanged. Source hashes differ because the runner/CLI now include this option; this is not a change to inference settings.

| Query | Controller | New attempt status | Reason |
|---|---|---|---|
| performance-complex-01 | Hybrid | needs_review | output_truncated |
| performance-complex-01 | Online | needs_review | output_truncated |
| performance-complex-01 | Always-Strongest | needs_review | output_truncated |
| performance-complex-01 | Formula | needs_review | output_truncated |
| performance-complex-02 | Always-Strongest | evaluation_unavailable | local tier-2 minute token-budget guard blocked verification |

Each query-1 attempt reported 1,707 tokens, including 1,536 output tokens. Query-2 Baseline reported 1,567 tokens and passed structural checks, but its required judge could not run: `Local minute token budget for openai/gpt-oss-20b reached. Wait or resume later; no API request was sent.` The benchmark stopped (exit 1) without another invocation. There was no new network/API failure in this controlled attempt; the guard failure is evaluation availability, not bad answer quality. Three preflight calls and five generation calls were made; no verification request was sent.

Strict latest-cell coverage: **0 completed, 4 needs_review, 1 evaluation_unavailable, 0 api_error, 3 unattempted**. Historical attempts: **0 completed, 5 needs_review, 1 evaluation_unavailable, 2 api_error** (eight records total). Previous API failures and the earlier Hybrid needs_review record remain unchanged. Genuine final Complex coverage is **0/8**, with no fully completed four-controller query pair.

No grades were assigned and no final quality-efficiency comparison was created because the eight-cell completion condition was not met. Original controller results and Simple/Moderate graphs remain unchanged. Raw reports are refreshed in `outputs/performance-complex-01-report/`; their legacy `completed_responses` field includes needs_review, so **it must not be used as genuine success coverage**. `strict_coverage.json` in that folder provides completed-only counts. The analysis script already excludes needs_review from fully paired comparisons.

Validation: **32/32 automated tests passed**, including a new test that retrying needs_review preserves its history, skips completed cells and leaves learning/rewards disabled. All pre-existing run payloads and states (including extension snapshots) and configuration bytes match the pre-invocation audit. Only new run/call records were appended; no policy or reward update occurred. SQLite integrity is `ok`; `calibrated=false`. No commit or push was made.
