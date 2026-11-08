# Project Plan — Measles SignalCheck AI

*Revised 7 Nov 2026 after the Milestone 2 data review. Decisions are in `PROJECT_DECISIONS.md`.*

## Problem statement
In Rio de Janeiro state (Brazil), MMR first-dose coverage recorded in the national
immunization system (SI-PNI) fell from **96.6% in 2019 to 61.6% in 2020 and 59.5% in 2021**.
Health regions moved very differently: Metropolitana II went from 100.1% to 35.6%, while
Serrana went from 98.5% to 82.6%. Nationally, WHO/UNICEF estimates confirm a real fall
(96% in 2015 → 73% in 2021). Below the national level, though, a coordinator has to decide **for each
health region and municipality** whether a drop reflects fewer children vaccinated, a
changed denominator, or a recording/reporting artefact, and what to check first.

**Measles SignalCheck AI** computes these signals transparently and uses Claude to turn
them into a short, cited **investigation brief**: what changed, the possible explanations
the data supports or rules out, what it cannot tell you, and the next checks to make.

## Users
- **Primary:** state, regional and municipal immunization coordinators (non-technical).
- **Secondary:** epidemiologists and M&E staff; portfolio reviewers.

## Success measures
1. **Grounding:** 100% of numbers in a brief can be traced to the evidence packet (automated check).
2. **Correct classification** of each evaluation case's signal type (numerator-driven, denominator-driven, implausible value, abrupt drop) by the deterministic layer: ≥ 90% on the case set.
3. **No unsupported causal claims:** 0 in the evaluation set (rubric plus pattern checks).
4. **Usefulness:** an independent reviewer (a peer, or the owner acting as reviewer) rates briefs as "actionable" on ≥ 80% of cases using the published rubric.
5. **Reproducibility:** a fresh clone reproduces all results with documented commands.

## Architecture (planned)
```
TabNet exports (raw, dated, hashed)
   → adapter → canonical table (unit, year, doses, target, coverage, source)
   → deterministic signal checks (Python, pytest-tested)
   → evidence packet (JSON, every fact has an ID)
   → Claude API (versioned prompt; must cite IDs; must state limits)
   → grounding validator (rejects numbers not in the packet)
   → Streamlit view + Markdown brief export (labelled "advisory")
```

## Tech stack
Python 3.12 · pandas · Streamlit · Plotly · Claude API (`anthropic`) · python-dotenv · pytest · Git

## Milestones
- [x] **0. Environment & scaffolding**
- [x] **1. Local tooling:** Python 3.12.10, Git 2.56.0, `.venv`, initial commit
- [x] **2. Data discovery & validation:** `DATA_SOURCES.md`, `PROJECT_DECISIONS.md`, `ANTHROPIC_ROLE_ALIGNMENT.md`
- [x] **3. Data acquisition, connector & data card** (7 Nov 2026): `BrazilSIPNIConnector`, canonical schema, coverage safeguards, `DATA_CARD.md`, 29/29 tests pass
- [x] **4. Deterministic signals & evidence packets** (7 Nov 2026): rules R1–R5 + `insufficient_evidence`, configurable thresholds, weighted state benchmark, labelled arithmetic decomposition, schema-validated packets with grounding and language checks; 63/63 tests pass
- [x] **5. Claude integration & evaluation: OFFLINE COMPLETE, LIVE VALIDATION DEFERRED** (7 Nov 2026). The integration is implemented and passes 106 offline tests, but **it has not been validated with a live API call**. The owner chose not to set up API billing for now.
- [x] **6. Streamlit dashboard** (7 Nov 2026): `app/streamlit_app.py` with 5 tabs, health-region filters, signal summaries, verified observations, labelled offline demonstration briefs, a disabled live-Claude option, and safe handling of missing, altered or empty data; 122 tests pass. *Original scope:* filters, charts, signal table, "Draft investigation brief", export; `docs/SECURITY_AND_GOVERNANCE.md`
- [x] **7. Portfolio readiness, responsible AI and enablement** (Nov 2026): `docs/ARCHITECTURE.md`, `docs/SECURITY_AND_GOVERNANCE.md` (v2), `docs/EVALUATION_REPORT.md`, `docs/REUSE_GUIDE.md`, `prompts/templates/brief_template.md`, `docs/workshop/` (simulated), `docs/PILOT_PLAN.md` (proposal), recruiter-facing README. No new integrations, no paid calls. *Original scope:* reference design, adapter guide (WHO admin2 / DHIS2 format), prompt and eval templates, workshop/tabletop kit, field notes
- [x] **8. Publication readiness and GitHub publication** (Nov 2026): full-history secret scan, noreply commit identity, pinned dependencies, MIT licence; published at https://github.com/bhavanasurapaneni-lab/measles-signalcheck-ai
- [x] **9. Portfolio improvements** (Nov 2026): real dashboard screenshots in the README, offline GitHub Actions CI, deep links, in-app official data download, hosted-demo plan (not deployed), `docs/RESUME_PROJECT_SUMMARY.md`; 133 tests pass

## Milestone 5: status (7 Nov 2026): OFFLINE COMPLETE, LIVE VALIDATION DEFERRED
**The Claude API integration is implemented but has NOT been validated with a live API call.** No real Claude output has been evaluated, and $0 has been spent. Everything below was measured offline with a fake client and labelled synthetic drafts. The live harness (`evals/run_live.py`, with a spend ledger and per-call worst-case gate) is kept for if and when the owner enables live testing.
- Built: `briefing.py` (observations, BriefDraft contract, rendering), `brief_validator.py` (claim-level grounding), `brief_client.py` (single call, explicit failure handling), `prompts/brief_v1.md`, `evals/` (cases, fake client, offline and live harnesses), `docs/SECURITY_AND_GOVERNANCE.md`.
- **Offline results:** 106/106 tests pass. 20/20 labelled draft cases get the expected verdict (18/18 known-bad drafts rejected or sent to review, 2/2 known-good accepted). 11 simulated API outcomes each map to an explicit status.
- **Live evaluation (deferred):** 14 packets (12 real, 2 synthetic). Expected about $0.84, maximum $2.41. It would run only if the owner explicitly enables live testing and configures a key. Until then, all development uses offline tests.
- **Unknown until a live run:** real acceptance, rejection and refusal rates; how often Claude complies with the no-digits rule; prompt-cache hits; latency; actual cost.

## Milestone 5: original proposed scope
**Goal:** Claude turns **one validated evidence packet** into a short investigation brief, and an evaluation harness measures whether the brief is grounded, cautious and useful. No UI and no deployment.

1. **Prompt and output contract:** a versioned system prompt (`prompts/brief_v1.md`). The packet is passed as data inside clearly delimited tags and treated as untrusted. Output is structured JSON: summary, observations (each citing F/D/S IDs), what the data cannot show, suggested checks, and limitations. Claude may only restate packet facts and propose *checks*, never causes.
2. **Client:** `src/signalcheck/brief.py`, which calls the Claude API (model from `.env`, default `claude-opus-5-5`) with structured output. Its only input is the packet: no raw files and no free text.
3. **Post-validation:** reuse the M4 grounding, language and reference checks on the brief. Reject and report, rather than auto-repair, any brief that fails.
4. **Evaluation set:** about 12 real packets (the 5 reference cases, stable controls, small-denominator and implausible cases) plus adversarial packets (for example a unit name containing an instruction, or an extreme value). The rubric scores grounding, absence of causal claims, coverage of limitations, and actionability. Deterministic checks are the gate; an optional model-graded rubric is reported separately.
5. **Prioritisation:** a transparent ordering of signals within a packet (no ML), because statewide signal counts are high.
6. **Security notes:** what is sent to the API (aggregate packet only), key handling, logging (no packets logged by default), and the provider data-use statement.

**Acceptance criteria:** 100% of evaluation briefs pass the grounding and language checks, or are correctly rejected. Results go in `evals/results/` with the model, prompt version and config hash. Cost and latency are recorded. Live API tests are opt-in (they need a key), and offline tests use recorded responses.

## Milestone 4: original scope (completed)
**Goal:** deterministic, tested signal rules that turn canonical observations into an **evidence packet** (JSON, each fact with an ID). No Claude API and no UI.

**Signals** (each states what it can and cannot mean):
1. **Recorded-dose drop:** relative change in `doses_administered` between comparable years, above a documented threshold (e.g., −30%).
2. **Driver of the coverage change:** dose change vs SINASC birth change, classified as *numerator-driven*, *denominator-driven*, *both* or *unclear*.
3. **Implausible published value:** coverage >100%, or a year-to-year swing of more than X points.
4. **Out of line with the state:** a municipality's dose change differs strongly from the statewide change.
5. **Small-population caution:** flag units under 100 births, where percentages are volatile.

**Acceptance criteria:** every signal is unit-tested on real cases (São Gonçalo, Niterói, Trajano de Moraes) and on **clearly labelled injected-anomaly fixtures** for recall. Thresholds are documented in a config file. The evidence packet validates against a schema and contains only aggregate values. Signals use neutral wording ("recorded doses fell 69%") and never causal wording.

## Milestone 3: original scope (completed)
**Goal:** a reproducible, documented raw-data snapshot for Rio de Janeiro state, loaded into the canonical schema and checked for internal consistency. No application code beyond loading and validation scripts.

**In scope**
1. Export from DATASUS TabNet (public, no login), **Tríplice Viral D1**, 2015–2022:
   - coverage (%) by health region (CIR) and by municipality, RJ state;
   - doses applied by the same units.
2. Save raw files unchanged in `data/raw/brazil_sipni/`, with a `manifest.json` recording the URL, query selections, retrieval date and SHA-256 hash of each file.
3. Write a loader (adapter) to the canonical schema, keeping the Portuguese names and IBGE codes.
4. Derive the implied denominator (doses ÷ coverage) and document it as *derived*.
5. Write `docs/DATA_CARD.md`: source, definitions, the TabNet caveat ("do not use the TOTAL row/column"), the 2023+ break, known limitations.

**Acceptance criteria**
- [ ] Raw files and manifest present; hashes match; `data/` stays git-ignored.
- [ ] Canonical table has the expected units (9 health regions; 92 municipalities, or a documented reason if different) and 8 years each.
- [ ] Recomputed coverage (doses ÷ derived denominator) matches TabNet within ±0.1 pp for every row.
- [ ] RJ state totals reproduce the published values checked on 7 Nov 2026 (2019: 96.58%, 2020: 61.61%, 2021: 59.48%).
- [ ] Missing, zero and >100% values are counted and listed, not silently dropped.
- [ ] Tests pass (`pytest`); data card written; no Claude API calls in this milestone.
- [ ] Commit made only after owner review.

**Out of scope for M3:** dashboard, Claude API, other states, Zambia adapter, DHIS2 adapter.

## Guardrails
- No synthetic data presented as observations (synthetic only as labelled test fixtures).
- Never commit API keys or raw data.
- AI output is advisory, cites evidence, and states what the data cannot show.
- Ask before installing software, downloading data, contacting anyone, or publishing.
