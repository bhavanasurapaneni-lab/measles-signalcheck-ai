# Security, Privacy and Responsible AI — Measles SignalCheck AI

*Version 2, Milestone 7 (Nov 2026). Each control is marked* **[Implemented]** *(in code and tested),*
**[Implemented – process]** *(a documented practice, not enforced by code), or* **[Proposed]**
*(required for a production deployment; not built).*

> **Status:** this is an independent prototype. Its only deployment is a public **offline demonstration** on Streamlit
> Community Cloud (https://measles-signalcheck-ai.streamlit.app/): public aggregate data, no API key, no live Claude
> calls, no accounts. It has **not** been deployed for any health organisation and has **not** been through any
> organisation's security review. The Claude API path is implemented but **has never been called with a real key**
> (live validation deferred, PROJECT_DECISIONS.md D-025).

---

## 1. Data classification
| Data | Classification | Where it lives |
|---|---|---|
| SI-PNI doses and coverage, SINASC births, CIR mapping (municipality × year aggregates) | **Public, aggregate, non-personal** (Brazil Ministry of Health open data) | `data/raw/` (git-ignored), hash-checked |
| Evidence packets, briefs | Derived from public aggregates | In memory, downloads, `docs/examples/` |
| Anthropic API key | **Secret** | Only in the git-ignored `.env`, entered by the owner |
| Personal or patient-level health data | **Not used anywhere** | — |

- **[Implemented]** Connectors accept only the declared aggregate tables. A test checks that the export headers contain only municipality and year columns.
- **[Proposed]** If a partner later supplies facility-level data, reclassify it, run a privacy and data-protection review (Brazil's LGPD or local law), and apply small-cell suppression rules **before** any data reaches the model.

## 2. Privacy
- **[Implemented]** No personal data is collected or processed. The dashboard has no user accounts and no analytics. Streamlit usage statistics are turned off (`.streamlit/config.toml`).
- **[Implemented]** The smallest unit is a municipality-year count. The minimum observed dose count is 6. **[Proposed]** For production: a documented small-number disclosure policy, even for public aggregates.

## 3. What is sent to the model
- **[Implemented]** Only a **validated, aggregate evidence packet**, reduced to `brief_input`: municipality code and name, two years, observation statements O#, "cannot conclude" items, limitations and prohibited interpretations. Raw files, hashes and other municipalities' data are not sent.
- **[Implemented]** `preflight()` re-validates every packet before sending (schema, references, number grounding, causal language, unit-name character set). Contradictory or tampered packets never reach the API (tested).

## 4. Prompt-injection risks and mitigations
| Risk | Mitigation | Status |
|---|---|---|
| Instructions hidden in source data (e.g. a municipality name) | The packet schema forbids free-text fields (`additionalProperties: false`). The unit name is checked against a character set. Packet content goes inside `<brief_input>` tags and the prompt says it is data | **[Implemented]** (tested with a synthetic injected unit name) |
| The model repeats injected text or follows it | The validator rejects instruction-like text, causal claims, numbers and other places | **[Implemented]** (offline) |
| A tampered packet file | Hash-checked raw data; packets rebuilt from source and re-validated before sending | **[Implemented]** |
| An all-caps injection that passes the character set | Caught by the output validator, not the input check | **[Implemented]**, but **live behaviour not observed** |
| Injection through future data sources (DHIS2 comments, free-text fields) | Exclude free text from connectors; separate security review per connector | **[Proposed]** |

## 5. API key management
- **[Implemented]** The key is read by the SDK from the git-ignored `.env`. The code never prints or logs it, and a test checks that no key material is in the source. `scripts/check_api_key.py` reports only presence, length and format.
- **[Implemented]** Tests force offline mode (`SIGNALCHECK_OFFLINE=1`). The dashboard's live switch needs both a key **and** `SIGNALCHECK_ENABLE_LIVE=1`.
- **[Implemented – process]** Keys are never pasted into chat, logs or commits. Staged changes are scanned before each commit.
- **[Proposed]** For production: a secret manager (cloud KMS or vault), per-environment keys, rotation, Console workspace spend limits, and keys held server-side, never in a browser.

## 6. Access controls
- **[Implemented]** None. It's a single-user local application on `localhost`.
- **[Proposed]** For a shared deployment: SSO (organisation identity provider), roles (viewer, analyst, admin), HTTPS, network restriction (VPN or allow-list), session timeouts, and separate permission to trigger paid live briefs.

## 7. Provider data handling
- **[Implemented – process]** Nothing has been sent to Anthropic: no live calls, and $0 spent.
- Anthropic's commercial terms and Trust Center (https://trust.anthropic.com) govern API data. Anthropic states that it does not train on customer data by default. **Verify the current terms, data-retention options and region settings before any real deployment**; this project hasn't relied on any specific retention setting.
- **[Proposed]** Record the provider, model, region and retention configuration in the deployment's data-protection impact assessment.

## 8. Human oversight
- **[Implemented]** Every brief is labelled **accepted**, **needs_human_review** or **rejected**, with the notice: *"Automated validation checks traceability and wording; it does not prove any public-health conclusion. A person must review this brief."*
- **[Implemented]** Possible explanations appear only under "Unverified possibilities to investigate (not findings)". Demo briefs are labelled "NOT generated by Claude".
- **[Implemented]** Rejected briefs are never automatically repaired or regenerated.
- **[Proposed]** For a pilot: a named reviewer per brief, sign-off recorded before a brief is shared with leadership, and an escalation path for briefs flagged for human review.

## 9. Auditability
- **[Implemented]** Provenance on every packet: source file hashes, retrieval time, rules version, and the SHA-256 of the config file. Briefs carry the model, effort, prompt hash and packet hash. Evaluation runs record status, tokens, cost and latency (spend ledger for live runs).
- **[Implemented]** Decision log (`PROJECT_DECISIONS.md`) and versioned prompt (`prompts/brief_v1.md`).
- **[Proposed]** Tamper-evident audit log of who generated or viewed or exported which brief; retention policy; periodic review of rejected and human-review briefs.

## 10. Realistic security requirements for a production pilot (all [Proposed])
1. Hosting inside the partner's approved environment (internal server or approved cloud) with HTTPS and SSO.
2. Server-side key in a secret manager, spend limits, and a monitoring alert on unusual usage.
3. Data-protection review (LGPD or equivalent), even for aggregate data, plus partner sign-off on what may be sent to the provider.
4. Audit logging and incident response contacts. Pinned dependencies and vulnerability scanning in CI.
5. A live evaluation on the partner's own cases **before** use, with acceptance and rejection rates reviewed by epidemiologists.
6. Written limits of use: briefs support investigation; they are not decisions or official statistics.

## 11. Known limits of the current safeguards
- The validator is deterministic and rule-based. It **cannot guarantee semantic faithfulness**: it may pass a subtly misleading sentence made of allowed words, or reject a legitimate one.
- Hedged possible explanations can still mention sensitive topics. They are labelled unverified, but a person must read them.
- No real model output has been evaluated, so live acceptance, refusal and injection behaviour are **unknown**.
