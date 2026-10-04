# Validation record — 3 October 2026

## Passed in the development environment

- 27 distinct automated unit/integration tests: preprocessing, feature bounds, semantic centroids, local retrieval, all four controllers, escalation limits, whole-trajectory reward, exactly-once feedback, missing usage, quota reservation, credential guards, API/judge failure behavior, sequential learning, frozen state isolation, benchmark resume, blind grading import, and report export.
- Real pinned MiniLM embedding download and CPU inference; real semantic routing and evidence retrieval combined with mocked provider responses.
- Streamlit AppTest: startup without credentials disables submission; mocked-API submission displays a response/report/history; Online mode accepts human feedback and updates persistent state.
- CLI doctor identifies missing local keys without printing any key value.

Development environment: Linux, Python 3.12.14, CPU PyTorch 2.14.1+cpu. Top-level dependency versions are pinned in requirements.txt; the complete development package inventory is recorded in requirements-tested-linux.txt. Windows installation commands are supplied but have not been executed on your laptop.

## Not yet established

- Live Gemini/Groq calls with your account keys, exact access, remaining quota, and response compatibility. Run `python -m aai.cli check-apis` locally; it makes three API requests.
- Empirical capability ordering of the three provisional tiers.
- Calibrated feature weights, thresholds, judge validity, reward coefficients, or a statistically convincing controller comparison.
- Live web retrieval: not included. Local evidence is implemented; current-fact requests are explicitly flagged unavailable.

No simulated answer, timing, reward, or token count is presented as a real benchmark result. The supplied benchmark references are authored grading rubrics, never hard-coded generation answers. Test databases are temporary and not included in the delivery.

## Repeat checks

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/check_ui.py
.\.venv\Scripts\python.exe -m aai.cli prepare
```

The first two use mocked APIs and spend no API quota. The last downloads/loads the free local embedding model. See README.md for real-account checks and experiments.
