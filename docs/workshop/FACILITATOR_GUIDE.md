# Facilitator Guide: "Real decline or records problem?"
### A simulated tabletop exercise for an immunization programme team

> **SIMULATED WORKSHOP.** This material was designed for a *simulated* programme team as part of a portfolio
> project. It has **not** been delivered to any health ministry, municipality or organisation. All figures are real
> public data (DATASUS TabNet). The **injects** in Part 4 are **fictional scenario elements** written for practice;
> they are not facts about São Gonçalo.

| | |
|---|---|
| **Audience** | Regional/municipal immunization coordinators, M&E officers, a programme lead (6–20 people) |
| **Duration** | 90 minutes |
| **Materials** | Dashboard running locally (`README.md` → *Install on Windows*), projector, printed `PARTICIPANT_EXERCISE.md`, the evidence packet `docs/examples/evidence_packet_330490_2019_2020.json` |
| **Learning goals** | 1) Separate recorded doses, published coverage and data-quality warnings. 2) List the questions to investigate before acting. 3) Name what the data cannot establish. 4) Explain findings to leadership without overstating them. 5) Know how AI-written text is checked and where a person must decide. |

## Agenda
| Time | Block | Facilitator actions |
|---|---|---|
| 0–10 | Welcome and framing | The problem: Rio de Janeiro's published MMR1 coverage went from 96.58% (2019) to 61.61% (2020). Ask: *"What would you do first on Monday morning?"* Note the answers |
| 10–25 | Dashboard tour | Sidebar: period **2019 → 2020**, region **Metropolitana II**, municipality **São Gonçalo**. Show Overview → Signals → Municipality trends → Investigation brief → Data & limitations |
| 25–40 | Part 1: What changed? | Participants complete Part 1 of the worksheet using the dashboard/packet |
| 40–55 | Part 2: Data-quality questions | Small groups list investigation questions; share back |
| 55–70 | Part 3: What we cannot conclude | "Supported or not?" card sort (worksheet Part 3) |
| 70–85 | Part 4: Briefing leadership + injects | Groups draft a 3-sentence leadership message; facilitator plays injects |
| 85–90 | Debrief | Key messages; how the tool keeps AI text grounded; feedback form |

## Part 1 — What changed? (answer key, all observed values)
| Measure | 2019 | 2020 | Source |
|---|---:|---:|---|
| Recorded MMR1 doses, age 1 (São Gonçalo) | 13,396 | 4,096 (**−69.4%**) | Packet F1, F2, D2 |
| Published coverage (São Gonçalo) | **121.66%** | 35.77% (−85.89 pts) | F3, F4, D5 |
| SINASC births, previous year (independent reference) | 10,969 (2018) | 10,432 (2019) (−4.9%) | F5, F6, D1 |
| Statewide recorded doses | 215,599 | 137,112 (−36.4%) | D3 |
| Metropolitana II recorded doses (region) | — | −64.7% vs 2019 | Dashboard Overview |

**Teaching points**
- Recorded doses fell far more than births changed. The fall in published coverage is therefore mainly a fall in **recorded doses**, not a change in the reference population. This is arithmetic on published values, **not** a cause.
- 121.66% in 2019 is **implausible as true coverage**. It can arise when doses are counted where they were *recorded* but the target population is counted where mothers *live*.
- São Gonçalo's fall (−69.4%) is about 33 points worse than the statewide fall (−36.4%).

## Part 2 — Questions worth investigating (examples to draw out)
1. Did any vaccination rooms stop sending records, or switch registration systems, in 2020? Compare monthly entries.
2. Do the municipal registers or vaccination cards show doses that are missing from the national database?
3. Were sessions suspended or reduced in 2020 (service disruption)? Check session logs.
4. Did vaccine stock movements fall in line with recorded doses? (Stock issued but no doses recorded points to a records gap.)
5. How many 2019 doses were given to children living in neighbouring municipalities (the >100% value)?
6. Did 2021–2022 recover? (Dashboard: 3,509 doses in 2021, 4,696 in 2022.)

## Part 3 — Supported or not? (answer key)
| Statement | Verdict | Why |
|---|---|---|
| "Recorded MMR1 doses in São Gonçalo fell by 69.4% between 2019 and 2020." | **Supported** | F1, F2, D2 |
| "Fewer children were vaccinated in São Gonçalo in 2020." | **Not supported** | Records ≠ vaccinations; recording gaps are possible |
| "The drop was caused by vaccine hesitancy." | **Not supported** | No evidence about causes in this data |
| "Coverage was 121.66% in 2019, which is implausible as true coverage." | **Supported** | F3; the cause of >100% isn't established |
| "The decline is denominator-driven." | **Not supported** | Denominator unpublished; the tool forbids this label |
| "São Gonçalo's recorded-dose fall was larger than the statewide fall." | **Supported** | D3, D4 |
| "Comparing 2020 with 2024 dashboard figures shows recovery." | **Not supported** | Crosses the 2023 reporting-system break |
| "Some doses may not have been transmitted to the national system; this should be checked." | **Supported as a hypothesis to check** | Hedged, framed as an investigation step |

## Part 4 — Briefing leadership, with injects
**Task:** each group writes three sentences for the programme director: *what changed, what we don't know yet, what we will check by when.*

**Injects** (read one every ~4 minutes; **all fictional**):
1. *"The director asks: 'So vaccination collapsed in São Gonçalo — should we announce an outbreak-risk campaign today?'"* → Separate records from vaccination. Recommend verification, with a deadline, before announcing anything.
2. *"A municipal nurse says one large clinic changed its registration software mid-2020."* (fictional) → A **hypothesis**, not a finding. Which check would confirm it? (monthly entries by clinic, stock vs records)
3. *"An AI-written brief says 'the decline indicates a service problem'."* → Show how the validator sends interpretive wording to **human review**. Who signs off?

**A good example message**
> "Recorded first-dose measles vaccinations in São Gonçalo fell about 69% from 2019 to 2020, while births changed about 5%, so the fall in published coverage mainly reflects fewer *recorded* doses. We do not yet know whether fewer children were vaccinated or whether records are missing. By [date] we will compare monthly clinic entries and stock movements, and report back."

## Debrief: key messages
1. Look at **recorded doses** and the **reference population** separately before reading a coverage percentage.
2. Values above 100%, small numbers and system changes are **data-quality warnings**, not results.
3. The data shows *what* changed, never *why*. Possible explanations are things to check.
4. In this tool, AI writes only narrative around verified observations. Every number comes from code, and a person reviews every brief.

## Facilitator notes
- Keep the dashboard in **offline demonstration mode**. The brief shown is a hand-written example, **not Claude output**. Say so explicitly.
- Collect feedback: clarity (1–5), which panel helped most, what was missing, would you use it (yes/no/why).
