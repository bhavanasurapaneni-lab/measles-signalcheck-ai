# Project Plan — Measles SignalCheck AI

## Goal

Give a district immunization officer a simple tool to answer:
1. *Where did measles vaccination coverage change meaningfully?*
2. *Is that change real, or might it be a data-quality problem?*
3. *What should I check next?*

## Users

- **Primary:** District immunization officers (non-technical).
- **Secondary:** Portfolio reviewers / hiring managers.

## Tech stack

| Purpose            | Tool                          |
|--------------------|-------------------------------|
| Language           | Python 3.11+                  |
| Data handling      | pandas                        |
| Dashboard          | Streamlit                     |
| Charts             | Plotly                        |
| AI explanations    | Claude API (`anthropic` SDK)  |
| Secrets            | `.env` file + python-dotenv   |
| Tests              | pytest                        |
| Version control    | Git (+ GitHub later)          |

## Milestones

- [x] **0. Environment & scaffolding** — folders, README, plan, requirements, .gitignore, .env.example
- [x] **1. Local tooling** — install Python 3.11+ and Git, create virtual env, `git init`
  (Python 3.12.10, Git 2.56.0, `.venv` with all requirements installed; initial commit created)
- [ ] **2. Data acquisition** — choose WHO dataset(s), download to `data/raw/`, document source & date
- [ ] **3. Data cleaning** — load, standardise columns, save to `data/processed/`
- [ ] **4. Signal detection** — rules for coverage changes and data-quality flags, with tests
- [ ] **5. Claude integration** — prompt that explains a flagged signal and suggests follow-up checks
- [ ] **6. Streamlit dashboard** — filters, charts, signal table, "Explain with AI" button
- [ ] **7. Polish & publish** — screenshots, README walkthrough, push to GitHub (with approval)

## Initial signal ideas (to refine in Milestone 4)

- Year-over-year coverage drop greater than N percentage points
- Coverage reported above 100%
- Missing years in a time series
- Large gap between MCV1 and MCV2 coverage
- Large gap between administrative and WUENIC estimates

## Guardrails

- Never commit API keys (`.env` is git-ignored).
- Never commit raw datasets (`data/` contents are git-ignored).
- AI output is advisory and must be clearly labelled as such.
- Ask before installing software, downloading data, or publishing.
