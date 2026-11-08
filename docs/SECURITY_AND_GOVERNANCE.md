# Security and Governance: Claude API use (Milestone 5)

*Draft, 7 Nov 2026. This applies to the investigation-brief feature. Review it before any deployment.*

> **Status:** the live API path is implemented but **has never been exercised with a real key**. Live validation is deferred by owner decision (PROJECT_DECISIONS.md D-025).

## 1. What is sent to the Claude API
| Sent | Not sent |
|---|---|
| One **validated evidence packet**, reduced to a compact `brief_input`: municipality code and name, two years, verified observation statements (O#), "cannot conclude" items, limitations, prohibited interpretations | Raw files, manifests, file hashes, other municipalities' data |
| The versioned system prompt `prompts/brief_v1.md` | Any personal or patient-level data (none exists in this project) |

- Every packet is **re-validated before sending** (`preflight`): schema, references, number grounding, causal-language checks, and the unit-name character set.
- An invalid or contradictory packet never reaches the API, and a test checks this.
- **Data classification:** public, aggregate, municipality × year statistics from Brazil's Ministry of Health (DATASUS TabNet).

## 2. Credentials
- The API key lives only in the git-ignored `.env` (the template is `.env.example`). The SDK reads it from the environment.
- The code never prints, logs or stores the key, and a test checks that no key material appears in the source.
- Owners add the key themselves; it must never be pasted into chat or committed.
- Tests set `SIGNALCHECK_OFFLINE=1`, so they cannot create a real client even if a `.env` exists.

## 3. Cost control
- Live calls run only through `evals/run_live.py --run --approve-max-usd <cap>`. The cap must be at least the computed maximum.
- The run stops once actual spend reaches the cap.
- `max_tokens` (8,000) bounds the cost of each call.
- `--estimate` needs no network and no key.

## 4. Model behaviour controls
- **Model:** `claude-opus-5-5`, effort `medium`, set explicitly and configurable in `.env`.
- **No cross-model refusal fallback:** a refusal is recorded as `refused`, which keeps evaluation runs reproducible.
- **Structured output:** `messages.parse(output_format=BriefDraft)`. Claude may not write numbers, and Python supplies every numeric statement.
- **Prompt-injection posture:** packet content is passed inside `<brief_input>` tags and declared to be data. The only source-derived free text is the municipality name, which is checked against a character set. Outputs with instruction-like text are rejected.

## 5. Human oversight
- Each brief is labelled **accepted**, **needs_human_review** or **rejected**.
- Even an accepted brief carries the notice: *"Automated validation checks traceability and wording; it does not prove any public-health conclusion. A person must review this brief."*
- Possible explanations are shown under "Unverified possibilities to investigate (not findings)".

## 6. Logging and retention
- Evaluation results (`evals/results/`) record status, token usage, cost, latency, model, prompt hash, packet hash and request ID, plus Claude's draft (aggregate only). No key and no raw data.
- Anthropic's handling of API data is governed by its commercial terms and the Trust Center (https://trust.anthropic.com). Check the current terms before a real deployment.

## 7. Known limits of the safeguards
- The validator uses deterministic rules, not full semantic understanding. It can miss a subtly misleading sentence that uses only allowed words, or reject a legitimate one, for example a place name used in another sense.
- Interpretive wording is sent to human review rather than accepted.
- Possible explanations may mention sensitive topics if they're hedged. They're displayed as unverified, but a reviewer should still read them.
