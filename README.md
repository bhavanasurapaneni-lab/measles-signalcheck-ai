# Measles SignalCheck AI

A portfolio project that helps **regional and municipal immunization coordinators**
investigate drops in measles first-dose coverage and tell real declines apart from
data-quality problems. It uses official public data (Brazil's SI-PNI, with WHO/UNICEF
estimates for cross-checking), Python, Streamlit and the Claude API.

> **Status:** Milestone 5 **offline complete, live validation deferred**. The Claude API integration
> for evidence-grounded briefs is implemented, with claim-level validation and 106 offline tests,
> but it **has not been validated with a live API call**. Milestone 6 adds a local Streamlit dashboard
> (offline demonstration mode). Example packet: `docs/examples/`.
> See `PROJECT_PLAN.md`, `DATA_CARD.md`, `DATA_SOURCES.md`, `PROJECT_DECISIONS.md` and
> `ANTHROPIC_ROLE_ALIGNMENT.md`.

## What it does now
- Fetches three small public, aggregate DATASUS TabNet tables (MMR1 doses, published MMR1 coverage,
  and SINASC live births for the 92 Rio de Janeiro municipalities) and records where they came from.
- Loads them through a reusable connector into one table format, keeping **doses**, **denominators**
  and **published coverage** separate.
- Refuses invalid coverage calculations and any comparison that crosses the 2023 SI-PNI/RNDS change.
- Applies deterministic, configurable **signal rules** and builds schema-validated **evidence packets**
  (Milestone 4).
- Includes a Claude API integration for evidence-grounded investigation briefs, with claim-level
  validation. It is tested offline only; **live validation is deferred** (Milestone 5).
- Provides a local **Streamlit dashboard** for coordinators, with region, municipality and period filters,
  signal summaries, verified observations and clearly labelled offline demonstration briefs
  (Milestone 6).

## How to use the dashboard
1. Choose a **comparison period** (e.g. 2019 → 2020), a **health region**, and a **municipality** in the sidebar.
2. **Overview**: state or region trend and the change in recorded doses by health region.
3. **Signals**: which municipalities crossed a review threshold; filter by signal and download the table.
4. **Municipality trends**: recorded doses (indexed against the state) and published coverage.
5. **Investigation brief**: verified observations with evidence IDs; demonstration briefs for
   São Gonçalo and Niterói (2019 → 2020) are hand-written fixtures, **not Claude output**.
6. **Data & limitations**: read before drawing conclusions.

## Project structure

```
measles-signalcheck-ai/
├── app/streamlit_app.py        # Dashboard (offline demonstration mode)
├── scripts/                    # fetch_tabnet.py, fetch_health_regions.py, run_signals.py, check_api_key.py
├── src/signalcheck/
│   ├── schema.py  tabnet.py  coverage.py   # canonical schema, TabNet parser, guarded calculations
│   ├── connectors/             # base.py (contract) + brazil_sipni.py
│   ├── signals.py  evidence.py # deterministic rules + validated evidence packets
│   ├── briefing.py  brief_validator.py  brief_client.py  demo_briefs.py   # briefs (offline-tested)
│   └── dashboard_data.py       # dashboard aggregation (weighted)
├── config/  schemas/  prompts/ # thresholds, packet JSON Schema, versioned prompt
├── evals/                      # evaluation cases, fake client, offline and live harnesses
├── tests/                      # pytest suite (122 tests)
├── data/raw/                   # Raw downloads + manifests (NOT committed to Git)
├── docs/                       # examples, security & governance
├── DATA_CARD.md  DATA_SOURCES.md  PROJECT_PLAN.md  PROJECT_DECISIONS.md
├── ANTHROPIC_ROLE_ALIGNMENT.md
├── requirements.txt  .env.example  .gitignore
```

## Install on Windows (step by step)

You need **Python 3.11 or later** (python.org; tick "Add python.exe to PATH" during install) and the
project folder on your computer. **No API key is needed**: the dashboard and all tests run offline.

```powershell
# 1. Open PowerShell in the project folder (e.g. VS Code: File > Open Folder, then Terminal > New Terminal)

# 2. Create the virtual environment and install dependencies (once)
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 3. Download the public data sample (about 23 KB) and the health-region mapping (once)
.\.venv\Scripts\python.exe scripts\fetch_tabnet.py
.\.venv\Scripts\python.exe scripts\fetch_health_regions.py

# 4. Start the dashboard - your browser opens http://localhost:8501
.\.venv\Scripts\python.exe -m streamlit run app\streamlit_app.py
```

**Optional (not required):** live Claude briefs need an Anthropic API key in a git-ignored `.env`
(copy `.env.example`). Live validation is currently deferred (PROJECT_DECISIONS.md D-025), and the
dashboard's live option stays disabled unless `SIGNALCHECK_ENABLE_LIVE=1` is also set.

## Get the data (raw data is not in this repository)

Raw files are excluded from Git. Recreate them from the official public source:

```powershell
.\.venv\Scripts\python.exe scripts\fetch_tabnet.py
```

This sends three documented queries to DATASUS TabNet (http://tabnet.datasus.gov.br/) and saves
TabNet's CSV exports **unchanged** to `data/raw/brazil_sipni/`, with a `manifest.json` recording
the URLs, query selections, retrieval time and SHA-256 hashes. The download is about 23 KB and
needs no login.

- The snapshot described in `DATA_CARD.md` was retrieved on 7 Nov 2026. TabNet's immunization
  tables were last updated in May 2023, but SINASC birth data can be revised, so a new download
  may have different hashes. In that case the reference-value tests (for example São Gonçalo)
  show exactly what changed.
- The connector checks every file against the manifest and refuses to load altered files.

## Open the dashboard (Windows)

```powershell
.\.venv\Scripts\python.exe scripts\fetch_health_regions.py   # once, for health-region filters
.\.venv\Scripts\python.exe -m streamlit run app\streamlit_app.py
```

Then open http://localhost:8501 in your browser. Press `Ctrl+C` in the terminal to stop it. The dashboard
runs in **offline demonstration mode**: no Claude API calls are made, and the sample briefs are hand-written
fixtures that are clearly labelled as such.

## Run the tests

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

Tests that need the raw data are skipped (not failed) if `data/raw/brazil_sipni/` is empty.

## Data source

Ministério da Saúde (Brazil), DATASUS TabNet: SI-PNI *Imunizações – Cobertura* and
*Doses Aplicadas* (1994–2022), and SINASC *Nascidos Vivos – Rio de Janeiro*. WHO/UNICEF
national estimates are used for cross-checking. Details, limitations and permitted
interpretations are in `DATA_CARD.md`.

## Disclaimer

This is a learning/portfolio project. It is not an official WHO or Brazilian Ministry of
Health tool, and its outputs should not replace official programme review. Changes in
recorded doses are not proof of changes in vaccination uptake.
