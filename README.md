# Measles SignalCheck AI

A portfolio project that helps **district immunization officers** investigate
changes in measles vaccination coverage (MCV1 / MCV2) and spot possible
data-quality issues, using public WHO data, Python, Streamlit, and the Claude API.

> **Status:** Initial scaffolding only. No data, dashboard, or AI features yet.

## What it will do (planned)

- Load public WHO/UNICEF measles immunization coverage data.
- Flag notable coverage changes year over year (drops, spikes, gaps).
- Flag data-quality signals (e.g., coverage > 100%, missing years,
  big gaps between administrative and official estimates).
- Use Claude to explain each signal in plain language and suggest
  follow-up questions an officer could investigate.
- Present everything in an interactive Streamlit dashboard.

## Project structure

```
measles-signalcheck-ai/
├── app/              # Streamlit dashboard (later)
├── src/signalcheck/  # Reusable Python code: loading, checks, AI helpers
├── data/
│   ├── raw/          # Original downloaded data (not committed to Git)
│   └── processed/    # Cleaned data (not committed to Git)
├── notebooks/        # Exploration notebooks
├── tests/            # Automated tests (pytest)
├── docs/             # Notes, screenshots, design decisions
├── README.md
├── PROJECT_PLAN.md
├── requirements.txt
├── .env.example      # Template for secrets — copy to .env
└── .gitignore
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

## Data source

WHO / UNICEF Estimates of National Immunization Coverage (WUENIC) and related
public WHO immunization datasets. Data will be downloaded in a later step and
is **not** stored in this repository.

## Disclaimer

This is a learning/portfolio project. It is not an official WHO tool and its
outputs should not replace official programme review.
