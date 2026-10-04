# Agentic Adaptive Inference Framework — Phase 1

A modular Python application for CPU query analysis and three-tier API inference. Includes Formula, contextual LinUCB, Hybrid, Always-Strongest, conditional local retrieval, conditional rubric verification, bounded escalation, SQLite logs, human feedback, and reproducible benchmark commands.

**Status:** implementation and offline/integration checks are supplied. Your account's three real API calls must still pass the preflight. Model capability ordering and policy constants are **provisional**, not experimentally established. No Phase 2 supervised router is included.

## 1. Open in VS Code (Windows)

Extract the ZIP. Open the `adaptive-inference` folder, not the ZIP. Use VS Code **Terminal → New Terminal**, with PowerShell. Install **Python 3.12, 64-bit** if unavailable. These commands do not require activating a PowerShell script:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` in VS Code. Insert your keys **only in this local file**. Confirm both provider projects are on free plans, then set `FREE_TIER_CONFIRMED=true`. Do not enable paid billing. Do not paste keys into chat, screenshots, Git, or benchmark exports.

In VS Code, use **Python: Select Interpreter** and choose `.venv\Scripts\python.exe`.

If `py` is not recognized but Python 3.12 is installed as `python`, use `python -m venv .venv` for the first command.

## 2. Run checks, in this order

```powershell
.\.venv\Scripts\python.exe -m aai.cli doctor
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m aai.cli prepare
.\.venv\Scripts\python.exe -m aai.cli check-apis
```

`prepare` downloads the pinned MiniLM embedding model once and runs it on CPU. It needs internet on the first run but no paid inference API. `check-apis` makes **one small real request to each tier** and logs their usage. It does not prove their capability ordering. If any fails, stop the benchmark and inspect the displayed error. Do not substitute paid models to make a test pass.

## 3. Launch the application

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the localhost URL printed in the terminal. Restart Streamlit after changing `.env` or configuration. Initial model loading may take time. Subsequent queries reuse the embeddings.

Try a factual question, an explanation, then:

> According to the provided notes, compare the two Aurora batteries and explain the experiment's limitations.

The last example retrieves a **clearly labelled synthetic evidence note**. Answers are generated through the selected API; no demonstration answers are hard-coded.

Use **Online Adaptive**, enable learning, submit a query, and give relevance/completeness/correctness feedback. Repeat with varied queries. Human feedback updates the policy once per run. Hybrid maintains a separate learned policy. Disable learning for a held-out comparison.

## 4. Tonight's small experiment

First use the app and API preflight. Then stop the app while running a benchmark to avoid competing for quotas. The included dataset has **4 pilot + 8 training + 8 test queries**; it is a smoke/pilot dataset, not a statistically convincing research benchmark.

Train Online and Hybrid sequentially. The terminal asks for three quality scores after each answer, using a reference rubric. This makes feedback available before the next decision:

```powershell
.\.venv\Scripts\python.exe -m aai.cli benchmark --experiment train-01 --split train --modes online hybrid --namespace phase1
```

Enter scores like `1,0.8,0.9`. Enter `skip` if you cannot grade an answer; that outcome will not update the policy. Do not give every response a perfect score just to advance.

Run all four modes on the held-out set:

```powershell
.\.venv\Scripts\python.exe -m aai.cli benchmark --experiment test-01 --split test --namespace phase1
```

The runner creates a frozen copy of each learned policy. It shuffles mode order deterministically per query and does not learn from test outcomes. If paused by a quota/provider/evaluator error, repeat the **same command** after resolving it. Completed cells are skipped. An incomplete cell is rerun, so its earlier calls remain in the overhead log. A rolling-day quota may require another day; no application can guarantee bypassing a provider's free quota tonight.

For an initial connectivity-only comparison, add `--limit 2` and use a separate experiment ID such as `smoke-01`. Do not call untrained Online/Hybrid results trained-policy performance.

Export answers for independent grading:

```powershell
.\.venv\Scripts\python.exe -m aai.cli export-grades --experiment test-01 --folder outputs/test-01
```

Fill the three 0–1 columns in `outputs/test-01/blind_grading.csv`. The file hides model and routing names; keep `grading_key.json` away from the grader. Use a CSV editor that preserves UTF-8 and commas. Leave unknown grades blank.

```powershell
.\.venv\Scripts\python.exe -m aai.cli import-grades --folder outputs/test-01
.\.venv\Scripts\python.exe -m aai.cli report --experiment test-01 --folder outputs/test-01
.\.venv\Scripts\python.exe -m pip freeze > outputs/environment-lock.txt
```

Outputs: `summary.csv`, `runs.jsonl`, `all_attempts.jsonl`, `usage.json`, and the grading files. Blank quality is **unmeasured**, not zero. Compare the same completed queries, include failures/coverage, and report mixed-provider latency as end-to-end service latency, not pure model speed.

## Free-tier budget controls

- Limits in `configs/settings.json` are account-observed/configurable caps; check your dashboards before running. API availability and limits can change.
- The application never enables billing, chooses a paid fallback, or silently retries an HTTP 429.
- Local reservations use 80% of configured caps and conservative UTF-8 byte estimates plus maximum output tokens. These are quota guards, not measured token counts.
- Minute limits can wait up to 65 seconds per call. Rolling 24-hour daily checks are conservative. Token quotas can stop a benchmark before request quotas do.
- Successful provider token counts are logged separately. Missing usage stays missing.
- All verification and escalation calls count. Other apps using the same account are outside this local ledger.
- The ₹0 guard relies on your account actually staying on a free plan. It cannot inspect or disable provider billing remotely.

## What retrieval and evaluation mean here

Retrieval uses `data/evidence.json`, a dated local collection with source IDs. You can replace/add authentic documents with clear provenance. The shipped notes are teaching/synthetic data, **not live web sources**. Queries explicitly requiring current facts return `evidence_unavailable` rather than presenting stale knowledge as current. Live web retrieval is not included in this build.

Every answer gets empty/truncation checks. Selected queries additionally receive a fixed-model JSON rubric judgment. Basic success is labelled **unchecked** with no invented adequacy score. The judge is an imperfect proxy, may share provider/model biases, and is not a truth oracle. The independent human benchmark grading remains separate.

Maximum escalation is tier 1 → 2 → 3, with no same-tier loop. If all judged attempts fail, the highest scored answer is displayed with `needs_review`. If verification fails because of an API/quota/format issue, the run is flagged instead of treating that as a bad model answer.

## Project layout

- `app.py` — Streamlit interface.
- `aai/config.py` — configuration and local environment loading.
- `aai/analysis.py` — preprocessing, features, prototypes, cosine similarity, complexity.
- `aai/controllers.py` — Formula, LinUCB, Hybrid, baseline, exactly-once reward updates.
- `aai/providers.py` — Gemini/Groq REST adapters, conservative quota reservations.
- `aai/retrieval.py` — local evidence retrieval.
- `aai/evaluation.py` — basic checks and conditional rubric judge.
- `aai/pipeline.py` — orchestration, escalation, trajectory metrics.
- `aai/storage.py` — transactional SQLite persistence.
- `aai/experiments.py` — resumable experiments, grading, exports.
- `aai/cli.py` — command-line entry point.
- `configs/settings.json` — all primary research parameters.
- `data/` — prototype queries, dated evidence, disjoint smoke splits.
- `tests/` — offline unit/integration checks using fake API responses.
- `outputs/` — runtime database/results; not bundled with keys or fabricated results.
- `DESIGN.md` — decisions, equations, calibration, limitations.
- `VALIDATION.md` — checks performed and remaining real-account checks.

## Troubleshooting

- **HTTP 400/404:** model ID/access may differ from the dashboard. Verify the exact API ID. Edit configuration only after verifying free access, then use a new experiment ID.
- **HTTP 401/403:** check your local key, project, and regional access. Do not publish the key.
- **HTTP 429 / local budget:** wait or resume later; do not upgrade billing.
- **Local minute-token cap even after waiting:** the single prompt reservation is too large. Shorten the query/source text/output budget, record the change, and start a new experiment. The app deliberately does not truncate evidence silently for judging.
- **Empty/truncated output:** reasoning tokens can consume the output budget. Inspect the logged finish reason; adjust the model's output budget during pilot calibration and rerun preflight.
- **Model download fails:** check internet access to Hugging Face and rerun `prepare`. No API key is normally required for MiniLM.
- **Few learned actions:** supply valid feedback; frozen policies cannot learn. Initial three-arm exploration needs at least three eligible feedback updates.
- **Want fresh facts:** add a documented retrieval service only after verifying its free allowance and reproducible evidence snapshots. The current local corpus cannot provide live facts.
