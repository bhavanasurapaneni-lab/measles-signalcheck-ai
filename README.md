# Measles SignalCheck AI

A portfolio project that helps **regional and municipal immunization coordinators**
investigate drops in measles first-dose coverage and tell real declines apart from
data-quality problems. It uses official public data (Brazil's SI-PNI, with WHO/UNICEF
estimates for cross-checking), Python, Streamlit and the Claude API.

> **Status:** Milestone 3 complete: a validated data connector for Brazil SI-PNI (Rio de Janeiro,
> 2015–2022) with a data card and 29 automated tests. No dashboard or Claude API integration yet.
> See `PROJECT_PLAN.md`, `DATA_CARD.md`, `DATA_SOURCES.md`, `PROJECT_DECISIONS.md` and
> `ANTHROPIC_ROLE_ALIGNMENT.md`.

## What it does now
- Fetches three small public, aggregate DATASUS TabNet tables (MMR1 doses, published MMR1 coverage,
  and SINASC live births for the 92 Rio de Janeiro municipalities) and records where they came from.
- Loads them through a reusable connector into one table format, keeping **doses**, **denominators**
  and **published coverage** separate.
- Refuses invalid coverage calculations and any comparison that crosses the 2023 SI-PNI/RNDS change.

## Planned
- Deterministic signal rules (Milestone 4) → Claude-written investigation briefs with
  cited evidence (Milestone 5) → Streamlit app (Milestone 6).

## Project structure

```
measles-signalcheck-ai/
├── scripts/fetch_tabnet.py     # Reproducible download of the raw TabNet sample
├── src/signalcheck/
│   ├── schema.py               # Shared observation table format
│   ├── tabnet.py               # TabNet CSV parser
│   ├── coverage.py             # Guarded coverage / change calculations
│   └── connectors/             # base.py (contract) + brazil_sipni.py
├── tests/                      # pytest (connector, validation, failure cases)
├── data/raw/                   # Raw downloads + manifest (NOT committed to Git)
├── app/  notebooks/  docs/     # Later milestones
├── DATA_CARD.md  DATA_SOURCES.md  PROJECT_PLAN.md  PROJECT_DECISIONS.md
├── ANTHROPIC_ROLE_ALIGNMENT.md
├── requirements.txt  .env.example  .gitignore
```

## Setup (once Python 3.11+ is installed)

```powershell
# 1. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your Claude API key
copy .env.example .env
# then edit .env and paste your key
```

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
