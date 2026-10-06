# Amended concise-format Complex extension — proposed protocol

Status: approved by the user and executed on 6 October 2026. The original preparation used no inference; execution results and deviations are recorded in [complex-concise-results.md](complex-concise-results.md). No policy updates occurred.

## Exact response-format instruction

Canonical instruction: [complex-concise-instruction.txt](complex-concise-instruction.txt). Its final newline is removed when used as a system-instruction suffix:

> Keep the answer concise: aim for 250 words and do not exceed 300 words. Fully address every part of the task; retain all requested alternatives, trade-offs, constraints, justification, and failure scenarios with mitigations or validation steps, as applicable. State necessary assumptions explicitly and do not invent constraints or measured results. Use compact bullets with short headings. Omit introductions, restatement of the question, repeated explanations, duplicate tables, and optional examples or code. Brevity must not replace substantive reasoning or omit required content.

Append this once to the existing generation system prompt, separated by two newline characters, identically for every controller and every generation attempt in the amended cohort. Do not append it to the query analyzed by the router. Do not change the operational judge prompt. The original substantive task and reference rubric remain the grading criteria; concise formatting is an output condition, not a replacement correctness rubric. The instruction reiterates the existing rubric requirement to state assumptions rather than adding a new domain task. Approximately 250 words is the target; 300 is the instructed upper bound. Compliance is not guaranteed by an instruction.

## Cohort and preserved settings

Proposed new ID: **`performance-complex-concise-01`**. Display label: **Amended concise-format Complex extension (250–300 words)**. It is not a resume of `performance-complex-01`; that historical experiment and all its attempts remain intact.

Reuse the exact bytes of `data/performance-extension.jsonl`: both query texts, IDs, test split, categories and reference rubrics stay unchanged. Compare three alternatives/designs, their trade-offs/advantages/disadvantages, a choice justified under stated constraints, and three failure scenarios plus mitigations or three validation steps. No simpler replacement task, deletion of requirements, or answer-based tuning is allowed.

Preserve the existing configuration byte-for-byte: Gemini `gemini-3.5-flash-lite`, Groq `openai/gpt-oss-20b` and `openai/gpt-oss-120b`; all generation maximum outputs 1536; judge output 1536 and fixed tier 2; temperature 0.2; GPT-OSS reasoning effort low; complexity thresholds 0.32/0.65 and weights; verification threshold 0.45; acceptance 0.75; routing/bandit parameters; retrieval/escalation rules; quota limits/headroom/wait settings; embedding revision/prototypes; and `calibrated=false`.

Use all four original controllers, seed 42 and test evaluation. Copy the original Phase 1 frozen Online/Hybrid states from `default__frozen__phase1-test-fast` into the new cohort's frozen namespace using the existing mechanism; verify copied hashes against the source. No training, tuning, automatic proxy rewards, human-feedback rewards or state updates. No API-model or transport substitution. Generation/verification/escalation calls count in measurements. A provider or evaluation-availability failure stops the run, with no repeated retry. Only genuinely `completed` cells count as success; truncation, needs_review, API errors and evaluation_unavailable do not. No historical truncated response is graded.

## Token-budget feasibility (estimate, not measurement)

Generation allowance remains 1536 completion tokens, including provider-accounted reasoning where applicable. A 250–300-word compact English answer would ordinarily use roughly 350–650 visible tokens; technical vocabulary may increase this. The historical query-1 calls reported seven reasoning tokens, but future reasoning usage is not guaranteed. The proposed length should plausibly fit with substantial headroom; this is not evidence that completion or correctness will occur. Do not change limits or auto-truncate an answer if it does not comply.

The judge reserves UTF-8 bytes, not tokenizer counts. With the unchanged judge system and empty evidence, reservation equals:

`1536 + 572 + serialized_query_answer_payload_UTF8_bytes`.

Query-specific overhead is computed with the actual unchanged query and an empty answer; JSON-escaped answer bytes are added to it. For illustration, 300 ordinary words averaging five ASCII letters plus a separator occupy about 1800 bytes; using eight letters plus a separator gives about 2700 bytes. Both estimates leave room under 6400. Markdown, non-ASCII punctuation, escapes and longer terms can increase bytes, so word count alone is insufficient. See the exact constants in the review response. Before any judge call, the existing guard still evaluates the real request and recent reservations; no silent evidence/answer truncation or guard bypass is proposed. A request fitting individually can still wait or pause because of earlier tier-2 calls. Waiting helps accumulated-window pressure, but not an individually oversized request.

Offline reconstruction gives fixed judge reservations of **2384** for query 1 and **2382** for query 2, before adding serialized answer-content bytes. Maximum answer-content allowances at an empty minute window are therefore **4016** and **4018** bytes. An 1800–2700-byte serialized answer gives reservations **4184–5084** and **4182–5082**, below 6400. These are illustrative byte estimates, not provider token measurements. The exact proposed generation-system suffix is 584 UTF-8 bytes; generation reservations become **2681** and **2679**, also individually below the tier-3 effective 6400 limit. Neither calculation removes accumulated quota pressure.

## Scientific presentation

Keep the original Phase 1 four-query table and graphs unchanged. Report the eight amended Complex cells in their own controller comparison, cohort coverage/reliability, quality-efficiency table and graphs. Use separate outputs: `outputs/performance-analysis-concise/` (after approval and actual collection).

If displaying Simple/Moderate/Complex together, include a mandatory **Prompt condition / cohort** column: Simple and Moderate = Original Phase 1; Complex = Amended concise format. Include a note: **Different prompt conditions; descriptive cross-cohort comparison, not a controlled estimate of complexity effects.** Any graph combining groups must show that note and identify Complex as concise-format; token/latency differences may reflect the brevity instruction as well as task complexity. Controller comparisons within the amended Complex cohort share the same format condition and frozen policies. Quality remains assistant rubric review unless independently human graded; no significance, equivalence, superiority, FLOPs or cost-saving claim follows from this tiny cohort.

## Implementation scope after approval

Historical implementation plan as approved before execution; these changes are now implemented and tested. Final outcomes, including word-limit noncompliance, are recorded in [complex-concise-results.md](complex-concise-results.md).

No source-code change is necessary to review this protocol. Source changes will be needed before execution because the current engine always sends a fixed system prompt and the runner cannot select a separately signed response-format condition. Editing query text would also change its analysis/context, so it is inappropriate.

Small proposed changes after approval: `aai/pipeline.py` adds an explicitly optional generation-format suffix, logs its text/hash and the actual generation system-prompt hash, and retains analysis of the unchanged query; `aai/experiments.py` passes the suffix and binds its hash into the new experiment signature only when used (legacy signatures/default behaviour stay unchanged); `aai/cli.py` exposes the instruction file for the new experiment. A frozen-test-only restriction prevents accidental training use. `tests/test_pipeline.py` and `tests/test_experiments.py` verify identical routing inputs, suffix propagation to every controller/generation, correct prompt provenance, signature mismatch rejection, no learning/rewards and unchanged legacy operation. `scripts/analyze_performance.py` adds the explicit prompt-condition labels and concise-cohort planned coverage, without changing the original report's measured data. Documentation is updated with actual results only after collection.

Before inference, audit original run/state/config/dataset bytes/hashes; validate the amended option offline; show final exact prompt/signature and tests. The new experiment state must not be created until the benchmark is approved. No files containing historical attempts are overwritten or deleted. No commit or push.

Files changed during preparation: only `docs/complex-concise-instruction.txt` and `docs/complex-concise-protocol.md`. All implementation files listed above are prospective; none have been edited for this protocol yet.
