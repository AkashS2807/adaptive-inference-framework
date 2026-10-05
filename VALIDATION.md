# Phase 1 validation record — 6 October 2026

**Phase 1 implementation and functional validation complete; empirical calibration remains provisional due to limited sample size/provider instability.**

This closes the implementation/feasibility milestone, not a statistically convincing research comparison. Settings remain `phase1-uncalibrated-v1`, `calibrated=false`. No weights, thresholds, tiers, reward coefficients, prompts, or trained states were tuned on test answers. Existing experiments were resumed, not rebuilt.

## Environment and functional evidence

Windows 11 (build 26200), Python 3.12.2, CPU PyTorch 2.14.1+cpu, NumPy 2.5.3, Streamlit 1.65.0, sentence-transformers 6.1.0. Dates use Asia/Calcutta. Local package inventory: `outputs/environment-lock-windows.txt` (ignored). Prior Linux development checks remain historical evidence; `requirements-tested-linux.txt` is not a Windows lock.

- **27/27 automated tests passed**, before and after the reporting change. Coverage: features, semantic centroids, retrieval, four controllers, bounded escalation/full trajectory accounting, exactly-once feedback, missing usage, quota/key/free-plan guards, API/judge failures, sequential training, frozen isolation, resume, grading and reports. The existing grading test now also verifies assistant/human provenance separation and no updates from test grades.
- Existing headless Streamlit AppTest passed: submission, response/report/history, Online learning and saved feedback, using mocked APIs and a temporary database. Prior manual UI/real MiniLM validation is reported in the handoff; this session also loaded the pinned CPU MiniLM for real held-out inference.
- CLI doctor passed: keys present (values hidden), free-plan confirmation true, packages installed, calibrated false.
- SQLite integrity: `ok`; no historical attempts deleted. Consistent local backup: `outputs/phase1-final-snapshot.sqlite`.
- Successful real calls to all three configured models exist in the call ledger. Original API preflight/manual checks are reported in the handoff; they were not repeated unnecessarily. This session resumed real Gemini/Groq inference and recorded actual provider tokens.

## Pilot and training

Means use completed responses only. Earlier failed attempts remain in raw exports. These tiny samples are feasibility evidence.

`phase1-pilot`: Formula completed 2/2; mean active latency 1.142 s, 231 tokens, one call, recorded free-plan cost ₹0. Three earlier API errors retained (five total calls).

`phase1-pilot-all`: **12/16 planned cells** complete, paired on pilot-01..03. Pilot-04 Online incomplete; its other three modes unattempted. No independent quality grades imported.

| Mode | Completed | Active seconds | Tokens | Tier-3 generation share |
|---|---:|---:|---:|---:|
| Formula | 3 | 0.722 | 257.00 | 0% |
| Online | 3 | 0.973 | 261.33 | 0% |
| Hybrid | 3 | 1.118 | 265.67 | 0% |
| Baseline | 3 | 1.123 | 361.33 | 100% |

Formula pilot mean wall time is 31.785 s including recorded waiting, not inherent controller compute time. Pilot-all history: 19 attempts/calls, seven API errors, 3,436 reported tokens. Failed-call token consumption is unknown.

`phase1-train-fast`: **8/16 planned cells** complete, paired on train-01..02. Train-03 Online incomplete; seven cells unattempted. Existing user-entered blind grades cover all eight completed responses: human mean quality/pass rate 1.0 per mode, only two questions each. Empty failed response remains unscored.

| Mode | Completed / human scored | Active seconds | Tokens |
|---|---:|---:|---:|
| Formula | 2 / 2 | 1.213 | 224.0 |
| Online | 2 / 2 | 1.242 | 287.5 |
| Hybrid | 2 / 2 | 1.210 | 225.5 |
| Baseline | 2 / 2 | 0.748 | 284.0 |

Training history: 12 attempts, 13 calls, three API-error attempts, one evaluation-unavailable attempt, 2,437 reported tokens. Infrastructure/evaluator failures are not answer-quality failures and did not train the policies. This is not convergence evidence.

## Frozen held-out comparison

`phase1-test-fast`: **16/16 planned cells completed**, four identical questions per controller (test-01..04: factual, sampling reasoning, palindrome code, caching/indexing comparison). Other four supplied test queries are outside `--limit 4`, not validated by this live comparison.

Original frozen namespaces were reused. Online version 3 has arm counts [1,1,1], including prior manual feedback; Hybrid version 2 has [1,1,0]. Hybrid remains in cold-start exploration and selects untried tier 3 throughout the frozen test. Neither is well trained. Every test decision's snapshot hash matches its final frozen state; all learning flags false and rewards null, including after grade import.

| Mode | Completed | Assistant quality | Assistant pass | Active seconds | Wall seconds | Tokens | Tier-3 share |
|---|---:|---:|---:|---:|---:|---:|---:|
| Formula | 4 | 0.9750 | 4/4 | 1.165 | 1.165 | 307.75 | 0% |
| Online | 4 | 1.0000 | 4/4 | 1.081 | 8.259 | 372.25 | 25% |
| Hybrid | 4 | 0.9750 | 4/4 | 1.653 | 8.604 | 449.00 | 100% |
| Baseline | 4 | 0.9833 | 4/4 | 1.990 | 13.701 | 449.50 | 100% |

Each completed cell used one generation call with complete reported token usage and recorded free-plan cost ₹0. None triggered live retrieval, verification or escalation; those paths have automated/prior functional evidence, not this held-out measurement. Active latency excludes recorded quota waits but includes provider/network latency; wall latency includes waits. Neither isolates model/controller compute time.

Quality is **blinded assistant rubric review, not independent human grading**. Scores were decided from the exported query/rubric/response CSV before reading the mapping. Relevance/completeness/correctness were scored 0..1 and averaged. All met the provisional 0.75 floor; specific correctness deductions are recorded for statistical explanations, code examples, Unicode claims or latency overstatements. Reviewer had project context, so blinding is limited, not an independent study. Human held-out coverage: **0/16**. Imports/reports preserve `blinded_assistant` separately from `blinded_human`; no human scores fabricated.

Held-out history: 18 attempts/calls, 16 completed plus the original API failure and one sandbox-blocked API failure during takeover; 6,314 reported tokens. Failed-call token/quota consumption is unknown. Authorized network resume added exactly 12 successful calls and skipped the four already completed cells. No transport replacement or repeated completed experiments.

## Infrastructure, reproducibility and conclusions

Historical ledger contains WinError 10054 connection resets alongside successes from both Groq models. These are provider/network-path failures, not model-quality evidence. First takeover attempt encountered sandbox socket denial (WinError 10013), distinct from historical resets. Authorized network resume completed the held-out set; failures remain retained.

Historical runs have multiple source hashes, consistent with the handoff's temporary transport experiment/reversion. Exact hashes/config/dataset signatures remain in aggregate and raw exports; historical source equivalence is not assumed. Successful takeover resume loaded one engine before grading-provenance edits, which affect imports/reports, not inference. Config/dataset hashes are constant. Seed 42 is recorded, but only one training order/run was evaluated. Provider aliases and network conditions can change; size labels do not prove tier ordering.

Supported: functioning implementation, real API inference, resume, feedback, frozen-policy feasibility, full response coverage on these four test questions, and assistant-reviewed core rubric satisfaction. All measurements are descriptive.

Not supported: reliable superiority/generalization, converged bandits, established tier capability ordering, calibrated thresholds/rewards, validated judge correctness, live web retrieval, measured FLOPs/energy, or monetary savings between modes. ₹0 relies on user-confirmed free plans; tokens are a resource proxy. Two training and four test questions cannot justify calibration.

## Artifacts and exact commands

Committed aggregate evidence: `docs/phase1-results.json` contains settings, summaries, planned/missing coverage, all-attempt counts/usage, paired IDs, source/config/dataset hashes and frozen-state audit. No keys, raw responses or grading mappings.

Ignored local evidence: `outputs/runs.sqlite`, final SQLite snapshot, `phase1-*-report/{summary.csv,routing_by_category.csv,runs.jsonl,all_attempts.jsonl,usage.json,README.txt}`, existing training grades, new held-out grading CSV/key, Windows package lock, local grading/finalization scripts. Do not expose the mapping to graders or force-add ignored evidence/secrets.

```powershell
.\.venv\Scripts\python.exe -m aai.cli doctor
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/check_ui.py
.\.venv\Scripts\python.exe -m aai.cli benchmark --experiment phase1-test-fast --split test --modes formula online hybrid baseline --limit 4
.\.venv\Scripts\python.exe -m aai.cli export-grades --experiment phase1-test-fast --folder outputs/phase1-test-fast-grades
.\.venv\Scripts\python.exe outputs/grade_heldout.py
.\.venv\Scripts\python.exe -m aai.cli import-grades --folder outputs/phase1-test-fast-grades --source blinded_assistant
.\.venv\Scripts\python.exe -m aai.cli report --experiment phase1-test-fast --folder outputs/phase1-test-fast-report
.\.venv\Scripts\python.exe -m aai.cli report --experiment phase1-pilot --folder outputs/phase1-pilot-report
.\.venv\Scripts\python.exe -m aai.cli report --experiment phase1-pilot-all --folder outputs/phase1-pilot-all-report
.\.venv\Scripts\python.exe -m aai.cli report --experiment phase1-train-fast --folder outputs/phase1-train-fast-report
.\.venv\Scripts\python.exe -m pip freeze > outputs/environment-lock-windows.txt
.\.venv\Scripts\python.exe -m outputs.finalize_phase1
git diff --check
git diff
git status --short
```

Tests/UI passed; export/import accepted 16 assistant-reviewed responses; reports succeeded; finalization verified frozen states and backed up SQLite. Benchmark ran twice: sandbox attempt paused with an API error, authorized network resume finished exit 0. No extra preflight calls.

Panel statement: “Phase 1 implementation and functional validation are complete. All 27 tests and the UI check pass. A real-API frozen four-question/four-controller feasibility comparison completed, with infrastructure failures retained. Held-out quality has assistant rubric review, not independent human validation. Settings remain uncalibrated and results do not establish superiority.”

No further work is required for this explicitly limited milestone. If the guide requires independent held-out quality evidence, the smallest next task is human review of the 16 exported answers without the mapping, assigning their own scores before importing with the default human source. Broader calibration is separate future work using representative development data, not these test answers.
