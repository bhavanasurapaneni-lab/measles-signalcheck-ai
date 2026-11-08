# Measles SignalCheck AI

**Evidence-grounded investigation support for immunization coordinators: real decline or records problem?**

In 2020, the measles first-dose (MMR1) coverage published for Rio de Janeiro state, Brazil, fell from **96.58% to
61.61%**. Some municipalities fell much further (São Gonçalo: 121.66% → 35.77%). A regional coordinator has to decide,
municipality by municipality, whether this reflects fewer children vaccinated, missing or late records, a shifting
denominator, or implausible data, and **what to check first**. Dashboards show the numbers. They don't separate
those possibilities, and generic AI summaries can state causes the data cannot support.

**Measles SignalCheck AI** turns official public data into **traceable evidence packets** with transparent,
tested rules. It then lets Claude write a short **investigation brief** under strict constraints: Claude may not
write a single number, every claim must cite verified evidence, and possible causes may only appear as hedged
hypotheses to check. Each brief is validated claim by claim before a person sees it.

> **What has actually been demonstrated** (details in [docs/EVALUATION_REPORT.md](docs/EVALUATION_REPORT.md))
> - ✅ Reproducible ingestion of official Brazilian Ministry of Health data (SI-PNI and SINASC via DATASUS TabNet) with SHA-256 provenance
> - ✅ Deterministic signal rules and schema-validated evidence packets: **644 municipality-year packets validated**
> - ✅ Claim-level grounding validator: **20/20 expected verdicts** on labelled synthetic drafts (offline)
> - ✅ Local Streamlit dashboard for non-technical coordinators; **122 automated tests pass**
> - ⏸️ **Claude API integration implemented but NOT validated with a live API call** (deferred; $0 spent)
> - ❌ Not demonstrated: use by real health teams, health impact, production reliability, clinical validation

*Portfolio project by Bhavana Surapaneni, prepared for Anthropic's Applied AI Architect, Beneficial Deployments
(Global & Public Health) role. Not an official tool of WHO, Anthropic or the Brazilian Ministry of Health.*

---

## Five-minute tour
1. **Read this page** (2 min): the problem, the approach, what's demonstrated.
2. **Look at one evidence packet** (1 min): [docs/examples/evidence_packet_330490_2019_2020.json](docs/examples/evidence_packet_330490_2019_2020.json). Every value has an ID (F#, D#), a source file, and a method.
3. **Skim the architecture** (1 min): [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), especially the diagram and "Demonstrated vs not demonstrated".
4. **See how AI output is checked** (1 min): the adversarial cases table in [docs/EVALUATION_REPORT.md](docs/EVALUATION_REPORT.md#adversarial-and-failure-cases).

## How it works
```mermaid
flowchart LR
    A["DATASUS TabNet<br/>(SI-PNI doses & coverage,<br/>SINASC births)"] --> B["Connector<br/>hash-checked, validated"]
    B --> C["Signal rules<br/>(configurable thresholds)"]
    C --> D["Evidence packet<br/>F# facts · D# calcs · S# signals"]
    D --> E["Dashboard"]
    D --> F["Observations O#<br/>(Python writes every number)"]
    F --> G["Claude brief<br/>(narrative only, cites O#)"]
    G --> H["Claim validator<br/>accept · human review · reject"]
    H --> E
```
- **Doses, denominators and published coverage are kept separate.** The official denominator is unpublished, so the tool never presents a recalculated percentage as official.
- **Signals are review triggers, not conclusions.** They cover a recorded-dose change of 30% or more, a coverage swing of 30 points or more, coverage above 100%, a 25-point or larger difference from the weighted state benchmark, and small numbers. Missing data yields `insufficient_evidence`, never zero.
- **Comparisons stop at the 2023 SI-PNI/RNDS reporting-system transition.** Analyses across it are refused.
- **Claude is constrained by design:** one structured-output call (`messages.parse`), a cached system prompt, explicit effort setting, no refusal fallback (for reproducible evaluation), and a validator that rejects numbers, wrong places, wrong indicators, wrong directions, causal claims and prompt-injection echoes.

## Demonstration walkthrough
1. Install and launch (below). The dashboard opens in **offline demonstration mode**.
2. Sidebar: period **2019 → 2020**, region **Metropolitana II**, municipality **São Gonçalo**.
3. **Overview**: statewide recorded doses fell 36.4%; Metropolitana II fell 64.7%.
4. **Signals**: 30 of 92 municipalities crossed the recorded-dose threshold; filter and export the list.
5. **Municipality trends**: São Gonçalo's doses (indexed to 2015) against the state; published coverage above 100% in 2019.
6. **Investigation brief**: four verified observations with evidence IDs, what the data cannot show, and a **labelled demonstration brief** (hand-written fixture, *not* Claude output) that passed the validator.
7. **Data & limitations**: sources, the 2023 break, and permitted and prohibited interpretations.

**Screenshots:** see [docs/screenshots/README.md](docs/screenshots/README.md) for the four views to capture.
They aren't committed yet.

## Install and run on Windows
You need **Python 3.11+** (python.org; tick "Add python.exe to PATH"). **No API key is needed.**

```powershell
# from the project folder
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# download the public data (raw files are not in Git; ~23 KB sample + 2.1 MB TabNet form page for regions)
.\.venv\Scripts\python.exe scripts\fetch_tabnet.py
.\.venv\Scripts\python.exe scripts\fetch_health_regions.py

# launch the dashboard, then open http://localhost:8501 in your browser (stop with Ctrl+C)
.\.venv\Scripts\python.exe -m streamlit run app\streamlit_app.py

# run the tests and the offline evaluation
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m evals.run_offline
```
- Raw files are saved **unchanged**, with a manifest (URLs, query selections, retrieval time, SHA-256). The connector refuses altered files.
- The reference snapshot was retrieved on 7 Nov 2026. SINASC can be revised, so a fresh download may change hashes. Reference-value tests then show exactly what changed.
- Tests that need raw data are skipped (not failed) if `data/raw/` is empty.
- **Optional live Claude briefs** need your own key in a git-ignored `.env` (copy `.env.example`) **and** `SIGNALCHECK_ENABLE_LIVE=1`. The live evaluation harness (`evals/run_live.py`) refuses to run without an approved spending cap.

## Evaluation results (summary)
| Area | Result |
|---|---|
| Automated tests | 122 passed (connector, signals, packets, briefs, dashboard, failure modes) |
| Agreement with published figures | State coverage within 0.3 pts of TabNet totals; national dose filter reproduces the WHO-reported target within 0.1% |
| Evidence packets | 644/644 statewide packets pass schema, reference, number-grounding and language checks |
| Brief validator (offline) | 20/20 expected verdicts across 18 failure modes: wrong number, place, year, indicator or direction; causal or uptake claims; injection; uncovered evidence |
| Live Claude evaluation | **Deferred: not run, no results claimed** |

## Responsible AI and limitations
- **Recorded doses are records, not confirmed vaccinations.** The data shows *what* changed, never *why*.
- **Human oversight:** every brief is labelled accepted, needs human review, or rejected, and states that validation doesn't prove any public-health conclusion. Rejected briefs are never automatically repaired.
- **Privacy:** only public, aggregate municipality-year data. Only validated packets would be sent to the API. Keys stay in a git-ignored `.env` and are never logged.
- **Limits:** one state, one indicator, 2015–2022. Rule-based validation can't guarantee semantic faithfulness. There's no ground truth for real data-quality problems. Not tested with real coordinators. Light theme only.
- Details: [docs/SECURITY_AND_GOVERNANCE.md](docs/SECURITY_AND_GOVERNANCE.md) · [DATA_CARD.md](DATA_CARD.md)

## Documentation
| Document | Purpose |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Components, data flow, decisions, deployment options |
| [docs/EVALUATION_REPORT.md](docs/EVALUATION_REPORT.md) | Tests, grounding checks, adversarial cases, unresolved risks |
| [docs/SECURITY_AND_GOVERNANCE.md](docs/SECURITY_AND_GOVERNANCE.md) | Data classification, injection, keys, oversight (implemented vs proposed) |
| [docs/REUSE_GUIDE.md](docs/REUSE_GUIDE.md) | Adapter spec, packet schema reference, prompt template, evaluation method |
| [docs/workshop/](docs/workshop/FACILITATOR_GUIDE.md) | Simulated 90-minute tabletop exercise (facilitator guide + participant sheet) |
| [docs/PILOT_PLAN.md](docs/PILOT_PLAN.md) | Proposed 12-week pilot with a go/no-go framework (no partnership exists) |
| [DATA_CARD.md](DATA_CARD.md) · [DATA_SOURCES.md](DATA_SOURCES.md) | Dataset documentation and source research |
| [PROJECT_DECISIONS.md](PROJECT_DECISIONS.md) · [PROJECT_PLAN.md](PROJECT_PLAN.md) | Decision log (D-001…) and milestones |
| [ANTHROPIC_ROLE_ALIGNMENT.md](ANTHROPIC_ROLE_ALIGNMENT.md) | Mapping to the role's responsibilities |

## Repository map
```
app/streamlit_app.py            dashboard (offline demonstration mode)
src/signalcheck/                connectors/, schema, tabnet, coverage, signals, evidence,
                                briefing, brief_validator, brief_client, demo_briefs, dashboard_data
scripts/                        fetch_tabnet, fetch_health_regions, run_signals, check_api_key
config/ schemas/ prompts/       thresholds, packet JSON Schema, versioned prompt + template
evals/                          cases, fake client, offline and (gated) live harnesses
tests/                          122 tests
docs/                           architecture, evaluation, security, reuse, workshop, pilot, examples
```

## Resume-ready project bullets
*Accurate as of Nov 2026; each is supported by code or documents in this repository.*
- Built an evidence-grounded immunization data-quality tool on official Brazilian Ministry of Health data (SI-PNI and SINASC, 92 municipalities, 2015–2022), with reproducible, hash-verified ingestion and a reusable connector interface.
- Designed deterministic signal rules and schema-validated evidence packets (644 validated), separating recorded doses, unpublished denominators and published coverage, and refusing comparisons across a 2023 national reporting-system change.
- Architected a Claude API integration (structured outputs, prompt caching, explicit failure handling) in which code generates every number and the model writes cited narrative only. In offline evaluation, a claim-level validator correctly rejected or sent to human review all 18 known-bad drafts. Live model evaluation was scoped and cost-gated but deferred.
- Delivered a Streamlit dashboard for non-technical coordinators with 122 automated tests, plus a security and governance pack, a reuse guide, a simulated tabletop workshop and a proposed pilot plan with go/no-go criteria.

## Data source and disclaimer
Ministério da Saúde (Brazil), DATASUS TabNet: SI-PNI *Imunizações – Cobertura* and *Doses Aplicadas* (1994–2022);
SINASC *Nascidos Vivos – Rio de Janeiro*; CIR health-region mapping. Accessed 7 Nov 2026. This is a learning and
portfolio project. Its outputs must not replace official programme review, and changes in recorded doses are not
proof of changes in vaccination uptake.
