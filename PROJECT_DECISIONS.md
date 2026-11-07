# Project Decisions — Measles SignalCheck AI

A log of key decisions, the alternatives considered, and the trade-offs. Newest first.
Each entry gives its status: **Proposed** (awaiting owner approval), **Accepted**, or **Superseded**.

---

## D-019 · Evidence packet schema validated without a new dependency (Accepted, 7 Nov 2026)
- **Decision:** the packet format is documented as standard JSON Schema (`schemas/evidence_packet.schema.json`). It is enforced by `jsonschema_lite.py`, a roughly 60-line validator for the subset of keywords used, which **raises on any keyword it doesn't support** so it can't drift from the schema.
- **Alternative:** add the `jsonschema` package. That's reasonable later, but it needs an install and approval.
- On top of the structure check, packets must pass: every reference resolves, every number in the text is grounded, there's no causal or uptake language, and no forbidden classification is used.

## D-018 · State benchmark = ratio of summed doses (weighted) (Accepted, 7 Nov 2026)
- **Decision:** the state's relative dose change is Σdoses(y2)/Σdoses(y1) − 1 over the units observed in both years. State coverage, where shown, is Σdoses / Σ(back-calculated denominators).
- **Evidence:** the weighted reconstruction is within 0.3 points of TabNet's published state totals (2019–2021). The **unweighted** mean of municipal percentages would be 72.72% for 2020, against the published 61.61%. A test guards this.

## D-017 · Signals are review triggers; thresholds are configurable judgement calls (Accepted, 7 Nov 2026)
- **Decision:** five rules (R1–R5) plus `insufficient_evidence`, with thresholds in `config/signal_thresholds.toml`. Each packet records the SHA-256 of the config. Only consecutive years are compared, and missing values become `insufficient_evidence`, never zero.
- **Observed volume (reported, not tuned):** in 644 municipality-year pairs, 173 have a ≥30% change in recorded doses and 347 have at least one value above 100%. Rio de Janeiro's municipal data is volatile, so Milestones 5 and 6 need **prioritisation and grouping**. Thresholds must not be tuned to make the counts look tidy.

## D-016 · No numerator- or denominator-driven classification; decomposition labelled as arithmetic (Accepted, 7 Nov 2026)
- **Correction to the brief:** the connector does **not** calculate an implied denominator. SINASC births are downloaded separately from the official SINASC source, so they *are* independent. They are **not compatible** with the official denominator, though: they're assigned by the mother's residence, while doses are assigned to where they were recorded, and the official denominator is an older, unpublished extract. **So SINASC is reported only as an `independent_reference` and is never used to classify a change.**
- Milestone 4 *does* back-calculate denominators (doses ÷ coverage) for one purpose only: a **mathematical decomposition** of reported coverage (ln C₂/C₁ = ln N₂/N₁ − ln Den₂/Den₁). These values are labelled `back_calculated_not_observed`, and the decomposition `mathematical_decomposition`, with "cannot establish cause".
- **Forbidden classifications** (rejected by the validator): `numerator_driven`, `denominator_driven`, `uptake_decline`, `reporting_failure`.

## D-015 · Real cases vs synthetic fixtures are separated (Accepted, 7 Nov 2026)
- **Decision:** synthetic anomalies exist only in tests, carry `source_id = "SYNTHETIC_TEST_FIXTURE"`, and are run through `evaluate()` only. They're never wrapped in a packet that cites real source files. Real-case tests use observed values only.

## D-014 · Coverage is calculated only behind explicit safeguards (Accepted, 7 Nov 2026)
- **Decision:** `sensitivity_coverage()` only runs for a declared compatible pair (doses ÷ previous-year SINASC births), with both values present, a denominator greater than 0, and comparable years. Every result carries a "not official coverage" label. Official coverage is never recalculated.
- **Alternative:** derive the official denominator by working backwards from published coverage. Rejected, because it isn't an independent, valid denominator.

## D-013 · Small connector interface plus a canonical long schema (Accepted, 7 Nov 2026)
- **Decision:** `Connector` (an abstract base) provides `verify_manifest()`, `check_comparable()` (using declared `SystemBreak`s) and `load() -> LoadResult(observations, quality)`. Observations use one long schema where doses, denominators and published indicators are separate values of `measure`, each with an `attribution`.
- **Adding a dataset** (e.g., WHO admin2 or a DHIS2 export) means one new subclass that declares its files, measures and system breaks.
- **Rejected:** a plugin registry, a config-driven ETL framework, or a database. All are unnecessary at this scale.

## D-012 · `limitations.pdf`: remove the redundant local copy (Recommended; awaiting owner permission)
- **Fact:** `limitations.pdf` in the project root is byte-identical (SHA-256 `1ef7190aaa3010c3…`) to WHO's "Limitations related to globally reported immunization subnational data" (last updated 15 Jul 2026). It arrived through a browser save prompt on 7 Nov 2026.
- **Recommendation:** **remove the local copy and don't commit it.** Its content is already summarised and linked in `DATA_SOURCES.md` §7 (URL plus hash). It's not used by the code. WHO PDFs are better cited than redistributed. And it isn't the Brazil data source the project now relies on. Delete only with the owner's permission.

## D-011 · Comparison window limited to 2015–2022 (legacy SI-PNI) (Proposed)
- **Decision:** longitudinal comparisons use only TabNet 2015–2022. No series is joined across the 2023 SI-PNI/RNDS transition.
- **Alternative:** extend to 2023–2025 from the new coverage dashboards.
- **Trade-off:** we lose the most recent years, but avoid presenting a change of system or method as a change in uptake.

## D-010 · Doses are the primary observed signal; coverage is quoted as published (Proposed)
- **Decision:** the tool leads with recorded dose counts, which need no denominator. Published coverage is quoted only as the Ministry published it. Coverage recalculated with SINASC is labelled a *sensitivity check*.
- **Why:** the official denominator isn't published, and it can't be reproduced exactly from current SINASC (it's an older extract of births from about two years earlier). Inventing a denominator would break the "no coverage without a valid denominator" rule.
- **Trade-off:** coordinators think in coverage %, so the interface must explain why doses come first.

## D-009 · Reproducible raw snapshot with manifest (Accepted, 7 Nov 2026)
- **Decision:** `scripts/fetch_tabnet.py` re-runs the exact TabNet queries and saves TabNet's own CSV unchanged, with URLs, selections, timestamps and SHA-256 hashes in `manifest.json`. Tests check the hashes.
- **Trade-off:** TabNet export URLs are temporary and TabNet could change its form fields. The script fails loudly if a selection disappears.

## D-008 · Deployment approach: local first, aggregate data only (Proposed)
- **Decision:** the prototype runs locally (Streamlit on the user's machine). Only **aggregate, public** numbers are sent to the Claude API. Briefs can be exported as Markdown files to share.
- **Alternatives:** hosting on Streamlit Community Cloud; a single offline HTML file (the IRC pattern); a DHIS2 app.
- **Trade-off:** running locally avoids hosting secrets and handling anyone else's data, but reviewers can't click a live link. A hosted demo can be added later once security review notes exist. An offline HTML export is a good fit for low-connectivity field teams, but it's deferred so we don't build features before they're needed.

## D-007 · Claude explains; Python computes (Proposed)
- **Decision:** all statistics and flags are computed deterministically in Python. Claude receives a structured **evidence packet** (JSON with IDs) and writes an investigation brief that must cite those evidence IDs. An automated check rejects any number in the brief that isn't in the packet.
- **Alternatives:** letting Claude analyse the raw tables (e.g., via code execution); a free-form chat over the data.
- **Trade-off:** less flexible, but auditable and testable, and Claude can't invent statistics. This matches how public-health partners need to defend numbers to ministries.

## D-006 · Evaluate before adding features (Proposed)
- **Decision:** an evaluation set of real, documented cases plus deterministic tests is a Milestone 5 gate. A feature isn't "done" until it passes its evaluation.
- **Trade-off:** slower to demo, but this is exactly the evidence a Beneficial Deployments partner (and reviewer) would ask for.

## D-005 · Synthetic data only as labelled test fixtures (Proposed)
- **Decision:** no synthetic data is shown to users as observations. Synthetic anomalies may be **injected into copies of real data inside the test suite**, clearly marked, to measure whether detectors catch them.
- **Alternative:** a fully synthetic district dataset for the demo.
- **Trade-off:** synthetic demo data would remove the data gap but undermine the project's core claim (an evidence-grounded tool). Test-only injection keeps the benefit (known ground truth for recall) without misleading anyone.

## D-004 · Geographic scope: Rio de Janeiro state, by health region and municipality (Proposed)
- **Decision:** the first prototype covers **Rio de Janeiro state**: 9 health regions (Regiões de Saúde, CIR) and their 92 municipalities, MMR first dose (Tríplice Viral D1), 2015–2022.
- **Alternatives:** all of Brazil (5,570 municipalities); a state with a smaller drop; the national level only.
- **Trade-off:** one state keeps the data small and reviewable while still giving multi-year subnational analysis. Rio de Janeiro has the sharpest verified 2019→2020 change in the data (96.6% → 61.6% statewide), so it's a strong case for asking "real decline or data artefact?". The method is meant to carry over to other states and countries through the canonical schema (D-003).

## D-003 · Use a canonical schema with source adapters (Proposed)
- **Decision:** every source is converted to one internal table:
  `country, admin1, admin2, unit_id, year, vaccine, doses, target, target_type, coverage_reported, source, retrieved_at`.
  Brazil SI-PNI is the first adapter. The WHO 2018 admin2 file and a DHIS2 export are documented as future adapters.
- **Trade-off:** slightly more up-front design, but it is the main **reusable asset**: the next partner only needs a new adapter, not a new tool.

## D-002 · Primary dataset: Brazil SI-PNI via DATASUS TabNet (Proposed; supersedes D-001's dataset choice)
- **Decision:** use the Brazil Ministry of Health's official immunization system (SI-PNI), published on DATASUS TabNet: MMR1 coverage and doses by health region and municipality, 2015–2022.
- **Why:** it is the only source verified so far that is official, publicly downloadable, subnational, and covers **two or more comparable years**, with doses and coverage. The national series matches WHO/UNICEF estimates (96% in 2015 → 73% in 2021).
- **Alternatives considered:**
  - *Zambia, WHO district data:* only 2018 is public, so no district trends are possible (verified).
  - *Zambia, DHS provincial survey (2013/2018/2024):* real and comparable, but 10 provinces with about 130–310 children per province per survey. The API returns no confidence intervals, so provincial changes can't be called significant. Kept as a triangulation reference, not the core dataset.
  - *WHO subnational 2017–2025:* the ideal dataset, but access is by request only.
  - *India HMIS / NFHS:* plausible but not verified in this round.
- **Trade-offs accepted:**
  - Brazil doesn't use DHIS2, and it's an upper-middle-income setting rather than a humanitarian one.
  - The TabNet series ends in 2022. Data from 2023 on sits in different dashboards and may not be comparable.
  - Labels are in Portuguese.
  - 2020–2021 coverage may mix real disruption (COVID-19) with registration-system effects. Separating those is the core problem the tool helps investigate, not something it can settle.

## D-001 · Zambia as candidate country (Superseded by D-002 for the core dataset)
- **Original decision (Milestone 2):** Zambia, using WHO national and district-band data plus the 2018 admin2 snapshot.
- **Why superseded:** the owner asked whether the 2018-only district file supports multi-year analysis. **It does not.** It contains one year, so it cannot show change in any named district. Zambia's national, band-level and DHS data remain documented in `DATA_SOURCES.md` as a secondary, lower-data-context example.

---

## Open questions (owner decisions)
1. Approve Brazil / Rio de Janeiro (D-002, D-004) as the core scope?
2. Keep Zambia as a documented secondary case only (recommended), or build a second adapter later?
3. Optional: request WHO subnational data access by email (owner's decision; Claude won't send it).
