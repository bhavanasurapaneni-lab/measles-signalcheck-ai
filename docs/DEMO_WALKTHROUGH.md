# Five-minute demonstration: São Gonçalo, 2019 → 2020

*A reproducible script for a recorded or live demo. Every figure below is an observed public value or a tested
calculation. The brief shown is an **offline demonstration fixture**, not Claude output. No health impact, deployment
or live model accuracy is claimed.*

**Before you start:** dashboard running (`README.md` → *Install and run on Windows*), browser at
`http://localhost:8501`, window about 1400 px wide. Sidebar: **2019 → 2020**, **All health regions**, **São Gonçalo**.

| Time | Screen | Say (paraphrase freely) |
|---|---|---|
| 0:00–0:40 | **Overview**: problem text and KPI tiles | "Rio de Janeiro's published MMR first-dose coverage fell from 96.58% to 61.61% in 2020. Recorded doses fell 36.4% statewide; 30 of 92 municipalities crossed the 30% recorded-dose threshold. The question for a coordinator is *real decline or records problem*, and what to check first." |
| 0:40–1:20 | **Overview**: regional bar chart | "Weighted by doses, Metropolitana II fell 64.7%, the most of the nine regions. All totals are ratios of sums, never averages of municipal percentages." |
| 1:20–2:10 | **Signals**: legend and table | "Signals are review triggers: change signals, data-quality warnings, and no causes. São Gonçalo is flagged for a −69.4% recorded-dose change, a coverage swing, coverage above 100% in 2019, and a large gap from the state." |
| 2:10–3:00 | **Municipality trends** (São Gonçalo) | "Recorded doses, indexed to 2015, against the state; published coverage was 121.66% in 2019, implausible as true coverage. SINASC births changed only about 5%: a reference series, not the official denominator." |
| 3:00–4:15 | **Investigation brief** | "Four verified observations, each with evidence IDs (F#, D#). Under each: what the data *cannot* tell you. The yellow banner says this sample brief is **hand-written, not Claude output**. In live mode Claude writes only the narrative: no numbers, every claim cites O1–O4, causes appear only as hedged possibilities. The validator accepted this one. Download the evidence packet to show traceability." |
| 4:15–5:00 | **Data & limitations**; then the README box | "Sources, the 2023 reporting-system break, and permitted versus prohibited readings. Honest status: 123 tests pass; the Claude API path is implemented but **not yet validated with a live call**; nothing has been used by a real health team." |

**Key message to close:** *Python computes and verifies every number; Claude only explains verified evidence and
proposes checks; a person decides.*

## Screenshots to include in the README
Capture per `docs/screenshots/README.md`. Recommended order and captions:
1. `01_overview.png`: "Statewide and regional change in recorded MMR1 doses, 2019→2020 (official DATASUS data)."
2. `02_signals.png`: "Signals are review triggers: change signals vs data-quality warnings; causes are never shown."
3. `03_trends.png`: "São Gonçalo: recorded doses indexed to 2015 vs the state; published coverage above 100% in 2019."
4. `04_brief.png`: "Verified observations with evidence IDs and a clearly labelled offline demonstration brief."
