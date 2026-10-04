# Phase 1 design and experiment notes

## Deployment and model selection

Python 3.12, CPU sentence-transformers/MiniLM, NumPy, stdlib HTTP/SQLite, and Streamlit fit the specified 16 GB Windows laptop. Three LLMs run through free API access. No local LLM GPU assumption, FastAPI server, vector database service, or supervised Phase 2 classifier is required.

Configured provisional tiers:

| Tier | Provider / API ID | RPM | RPD | TPM | TPD |
|---|---|---:|---:|---:|---:|
| 1 | Gemini / gemini-3.5-flash-lite | 15 | 500 | 250000 | not configured |
| 2 | Groq / openai/gpt-oss-20b | 30 | 1000 | 8000 | 200000 |
| 3 | Groq / openai/gpt-oss-120b | 30 | 1000 | 8000 | 200000 |

These values come from the account setup discussion and require preflight/dashboard confirmation. They are not promises of future access. Model names, size, and branding alone do not prove a capability hierarchy. The pilot must confirm quality, usable output, and service latency. Do not claim tier 3 is universally strongest. Changing tier order requires a new configuration and new experiments. Keep exact returned model-version information where supplied; aliases can change and free APIs may not support immutable snapshots.

Official references for checking current contracts:
- https://ai.google.dev/gemini-api/docs/pricing
- https://ai.google.dev/gemini-api/docs/rate-limits
- https://ai.google.dev/api/generate-content
- https://console.groq.com/docs/models
- https://console.groq.com/docs/rate-limits
- https://console.groq.com/docs/reasoning
- https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2

## Flow and common policy

Original query → normalized analysis → explicit features + semantic prototype similarities → complexity → controller chooses starting tier → conditional evidence retrieval → generation → structural checks / conditional judge → accept, flag, or escalate → store full trajectory → optional feedback update.

All four modes share retrieval, verification, escalation, prompts, and output budgets. The only learned action is the **initial model tier**, so LinUCB has three arms. Retrieval and verification remain explicit common policies. This avoids an unjustified explosion of scarcely sampled arm combinations. This build does not claim that the bandit learns retrieval or verification policies.

Always-Strongest always starts generation at tier 3, with the same tool policy and evaluator. Evidence-unavailable queries stop in every mode. This is a fair starting-model baseline, not an always-retrieve/always-verify baseline.

## Explicit features and prototypes

Preserve the original query; collapse whitespace only for normalized text. Regex matching uses lowercase without changing what the LLM receives. Features are weak indicators, not proof of difficulty:

| Feature | Initial definition | Limitation |
|---|---|---|
| Length | min(word count / 100, 1) | Long does not necessarily mean hard |
| Reasoning | min(distinct matched reasoning patterns / 3, 1) | Implicit reasoning can be missed |
| Requirements | min((distinct multi-requirement patterns + max(requested count−1,0)/2) / 3, 1) | Linguistic heuristic, not actual reasoning-step count |
| Technical | min(distinct technical pattern groups / 2, 1) | Vocabulary coverage and domain bias |
| Recency | explicit current/latest/time expressions and officeholder pattern | False positives/negatives; e.g. general discussion of updating data |
| Sources | source/citation/evidence/URL/document expressions | Does not fetch arbitrary URLs |
| Task hints | code, calculation, creative, requested count | Avoid a second learned task classifier |

There are ten hand-authored example queries per category (Factual, Reasoning, Analytical, Creative, Technical). Encode each, normalize, average per category, normalize the centroid. Store SHA-256 of prototype data. Query cosine similarities are retained in full. They are **not class probabilities**. Categories overlap; a dominant label is a signal, not ground truth.

MiniLM revision is pinned. Text is split into 220-wordpiece chunks to fit its context; normalized chunk embeddings are averaged and renormalized. A gap below .025 or maximum cosine below .20 marks uncertain semantic classification. These cutoffs require validation. The small prototype set is a seed, not a representative research dataset.

## Complexity and formula routing

Initial H = .10 length + .30 reasoning + .35 requirements + .25 technical.
Initial semantic S = positive-cosine-weighted category scores: factual .15, reasoning .65, analytical .80, creative .40, technical .60. Normalize the positive cosine weights; if all are zero use .50 as an explicitly provisional neutral fallback.

C = .70 H + .30 S. Simple C < .32; Moderate .32 ≤ C < .65; Complex C ≥ .65. Recency controls evidence requirements independently and is not itself added to difficulty.

Formula rules, in priority order:
1. Tier 3 if C ≥ .65, or requirements ≥ 2/3 and either a reasoning indicator exists or the semantic task is Analytical.
2. Otherwise tier 2 if C ≥ .32, any reasoning/technical indicator, code/calculation, or semantic task Analytical/Reasoning/Technical.
3. Otherwise tier 1; uncertain semantic classification raises this to tier 2.

Therefore complexity class does not map mechanically to model tier. All reasoning is logged. These are baseline engineering rules, not validated optimal rules.

Retrieval: recency or explicit source requirement. Verification: retrieval, C ≥ .45, code, calculation, or explicit requested count. Universal structural checks are separate. Top three local documents above .22 cosine, with a 3500-character evidence budget; each selected excerpt and source ID are logged. Recency currently stops with an honest evidence limitation.

## Evaluation and reward

The operational judge is fixed to tier 2 to control cost and avoid switching judges by routed tier. It scores relevance, completeness, task quality, and (only with evidence) evidence consistency. Applicable dimensions receive equal weights. Mean ≥ .75 is provisionally adequate. This is a quality proxy with self/family bias risk and no correctness guarantee. Empty/truncated generations are structural failures. Invalid judge output/HTTP/quota errors are evaluator failures, not negative model feedback.

For no-judge answers, `score=null`, `status=unchecked`. Never substitute 1.0 for unknown quality. Human feedback is the default reward source for all eligible online/hybrid runs. Automatic operational-proxy rewards are opt-in (`automatic_proxy_rewards`) and must be reported as a different experimental condition; conditional availability can bias that feedback.

Context x: intercept; length/reasoning/requirements/technical/recency/sources/code/calculation; C; five cosine similarities. Dimension 15.

LinUCB arm a: mean = xᵀ A_a⁻¹ b_a; bonus = .30 sqrt(xᵀ A_a⁻¹ x). Select the highest score after balanced deterministic cold-start exploration. A starts as I, b as zero. Each eligible feedback update adds xxᵀ to A and reward*x to b. Formula does not update. Hybrid adds .12 to the formula-recommended arm's score; cold start prefers the formula arm if untried, then explores remaining arms.

Reward = Q − .15 min(T/6000,1) − .10 min(L/60,1) − .40 I(Q < .75).

Q is human mean relevance/completeness/correctness by default. T counts **all** generation and verification tokens, including escalations. L is active trajectory latency, excluding recorded quota waits. A successful escalation does not erase earlier costs. The initial arm receives the reward. Human grading time is not inference latency. Token count is an imperfect cross-model resource proxy; it is not actual money, FLOPs, or energy. Actual free usage cost is ₹0, so there is no empirical monetary-cost difference to optimize. This design uses tokens and latency as the efficiency terms.

No update on API errors, unavailable evidence, missing usage, or absent quality. Feedback is transactional and exactly once. Persistent states include configuration/prototype hashes, counts, version, and full A/b matrices. Testing clones training states into experiment-specific frozen namespaces.

## Arbitrary parameters and calibration protocol

**Every numeric feature divisor, task score, mixture weight, complexity/semantic/retrieval/acceptance threshold, exploration value, hybrid bonus, and reward coefficient above is an initial engineering choice requiring calibration.** They are exposed/documented, not claimed universal. Max input/output, timeout, evidence size, and quota headroom are operational limits; pilot them for feasibility and record changes.

Before a publishable experiment:
1. Expand and split representative queries by task/domain/difficulty before tuning; remove duplicates and near-duplicates. Keep prototype examples separate from evaluation queries.
2. On pilot/development queries, run each candidate tier with the same prompts and evidence. Blindly grade answer quality and record actual usage/latency. Select tier order empirically. Small free quotas may require several days.
3. Label query requirements/complexity independently; measure feature/task mistakes. Adjust vocabularies and prototypes only on development data.
4. Search a small documented grid of feature/mixture weights and thresholds on development data. Select a quality floor first, then lower resource use. Retain all candidate settings and results rather than selecting favorable examples.
5. Grade a development subset independently and compare operational-judge decisions against human judgments (false acceptance/rejection). Choose adequacy threshold and assess judge bias. Do not claim perfect factual verification.
6. Choose reward scales from development token/latency distributions and report sensitivity to coefficient changes. Cap values to prevent outliers dominating; report saturation rates.
7. Freeze configuration, source hash, dataset, prompts, prototype hash, dependency lock, model IDs/versions, trained states, and random seed before held-out evaluation. Do not tune on the eight smoke test items and then call them unseen research results.
8. For the final report, use paired quality differences, uncertainty intervals, repeated online training orders/seeds, coverage/failure rates, and per-category results. The supplied smoke dataset is insufficient for reliable superiority claims.

## Budget and benchmark design

Included dataset: 4 pilot, 8 train, 8 test. Tonight's training is 8 queries × 2 adaptive controllers = 16 trajectories; test is 8 × 4 = 32 cells (four current-evidence cells stop before an API call). These are small feasibility checks.

Conservative ceiling without relying on skips: training 16×3 generations +16×3 judge calls =96 calls; test per query (Formula3 + Online3 + Hybrid3 + Baseline1)×2 =20, so 8×20=160 calls. Combined256 calls +3 preflight calls; pilot runs add their own calls. Real calls should usually be fewer. Requests-per-day alone do **not** guarantee this fits: shared tier-2 judging and token-per-day limits can bind. The local ledger pauses rather than overruns configured caps. Start with `--limit 2` if time or remaining quota is tight.

Local byte-based reservations deliberately overestimate tokens and can constrain long responses. Keep output concise. One oversized judge request must be addressed in the pilot (output/evidence budget), not silently truncated and treated as complete.

No online experiment reuses cached LLM answers as if freshly generated. Resuming skips finished cells and retains failed overhead. Retrieval snapshots are local and deterministic. Mode order is seeded and shuffled to reduce order confounding. Mixed providers, network variation, rate limiting, hidden reasoning token accounting, and alias changes limit speed/resource comparisons.

## Logging schema

SQLite `runs`: ID, Unix UTC timestamp, JSON payload.
Payload: schema/config/source hashes, config snapshot, Python/embedding revision, original/normalized query, features, full similarities, prototype hash, complexity components/class, selected mode, namespace, initial model, formula prior, action scores, state key/version/hash/snapshot, decision reasons, evidence IDs/text/provenance/hash, each generated answer and evaluation, returned final tier/answer, status, all call records, token completeness, generation/verification counts, active/API/wall/quota latency, escalations, tier-3 use, free-cost basis, feedback quality/source/reward, benchmark split/category/query ID/rubric/dataset hash, optional independent human grade.

SQLite `calls`: ID/run/model/time/reservation and per-call JSON: provider/purpose/status, finish reason, returned model version, input/output/total/reasoning tokens where available, latency, quota wait. Reservation is retained even after failed calls because quota consumption is uncertain. Preflight calls are present here even though not benchmark trajectories.

SQLite `states`: persistent bandits, experiment signatures, and provider cooldowns. `feedback`: unique run ID and applied quality/reward. No keys or authorization headers are logged. Query and answer content is logged intentionally; avoid sensitive material in research demonstrations.
