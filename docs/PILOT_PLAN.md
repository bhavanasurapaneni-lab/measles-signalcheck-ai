# Proposed Pilot Plan: Measles SignalCheck AI

> **PROPOSAL ONLY.** No public-health organisation has agreed to a pilot, and nothing has been deployed. This plan
> describes how a pilot *could* be run with a ministry, state or municipal health department, or an NGO supporting
> one. Targets below are **proposed success measures to agree with a partner**, not results.

## 1. Pilot shape
| | |
|---|---|
| **Partner type** | A state or regional immunization team (e.g. one Brazilian state's health region coordinators), or an NGO supporting district immunization data review |
| **Duration** | 12 weeks: 3 discovery · 2 setup and governance · 6 use · 1 review |
| **Users** | 5–15 coordinators and M&E officers; 1 epidemiologist reviewer; 1 programme lead (sponsor) |
| **Scope** | MMR1 (optionally DTP3) recorded doses and published coverage; one region; historical years within one reporting system |
| **Mode** | Starts in **offline mode** (deterministic signals and evidence packets). Live Claude briefs only after the governance gate (§4) and a separate live evaluation |

## 2. Stakeholder discovery (weeks 1–3)
- **Interviews (6–10):** coordinators, M&E, the information-system (SI-PNI/DHIS2) focal point, the programme lead, IT/security, the data-protection officer.
- **Questions:** How are monthly or annual coverage reviews done today? Who decides what to investigate? What data do you trust least? Which tools exist (TabNet, DHIS2 dashboards, WHO DQ Tool)? What connectivity and devices do you have? What would make you stop using a tool?
- **Output:** a one-page use-case statement and success measures signed by the sponsor.

## 3. Baseline workflow assessment
Measure before introducing the tool, using the partner's own last review cycle:
- Time from data availability to a list of units to investigate.
- Number of units reviewed per cycle, and how they were chosen.
- How often investigations found a records problem versus a real service change (if recorded).
- Format and turnaround of messages to leadership.

## 4. Governance review (gate before use)
- Data classification and the data-protection assessment (aggregate data; confirm no personal data), signed by the partner's data-protection officer.
- Confirmation of what may be sent to an external AI provider. Provider terms, retention and region reviewed (`SECURITY_AND_GOVERNANCE.md` §7).
- Hosting decision (local, internal server, approved cloud), authentication, key management, audit log.
- Written limits of use: briefs support investigation; they are not official statistics or decisions.
- **Live-AI gate:** a live evaluation on 10–20 of the partner's own cases, reviewed by an epidemiologist, with acceptance and rejection rates reported **before** any coordinator sees live briefs.

## 5. Training
- The 90-minute simulated workshop (`docs/workshop/`), adapted to the partner's own cases.
- A one-page quick guide plus a 15-minute refresher at week 4.
- A "how to brief leadership" template (three sentences: what changed · what we don't know · what we'll check by when).

## 6. Connectivity and device constraints
- The deterministic layer runs fully offline on a laptop (Python + Streamlit). Only live briefs need internet.
- For field teams: pre-generate briefs centrally and share them as files (HTML or Markdown export; this is the IRC case-study pattern). This needs an export feature, which isn't built yet.
- Low bandwidth: the data sample is small (about 23 KB plus the region mapping). Refresh monthly or quarterly.

## 7. Support procedures
- A named support contact; a response target agreed with the partner (e.g. 2 working days).
- An issue log for data problems, wrong signals, and confusing wording.
- Monthly review of rejected and human-review briefs and of threshold settings with the epidemiologist.
- A rollback plan: return to the baseline workflow at any time; nothing in the pilot changes official systems.

## 8. Success measures and go/no-go framework
**Proposed measures (agree targets with the partner; none are results):**

| Dimension | Measure | Example target to negotiate |
|---|---|---|
| Usefulness | Coordinators rating the evidence view "useful for deciding what to check" | ≥ 70% |
| Time | Time from data availability to an investigation list | Lower than baseline |
| Accuracy | Signals matching the source data in spot checks | 100% (deterministic) |
| Safety | Accepted briefs with an unsupported causal or uptake claim (epidemiologist review) | 0 |
| Grounding | Live briefs passing validation without human-review flags | Report, then set a threshold |
| Follow-through | Flagged units where a verification step was completed and the outcome recorded | Track |
| Adoption | Active users in weeks 6–11 | ≥ 60% of trained users |

**Go/no-go at week 12:**
- **Go (expand):** safety measure met (0 unsupported claims accepted); usefulness and adoption targets met; governance has no open high-risk issues.
- **Iterate:** useful but safety or grounding issues found. Fix, re-evaluate, repeat a short pilot.
- **No-go:** any accepted brief misled a decision; data cannot be refreshed reliably; or users do not find it more useful than the baseline.

## 9. Risks specific to a pilot
- Over-trust in AI text → keep human review and an "unverified" label on explanations; train on Part 3 of the workshop.
- Too many signals → agree prioritisation with the partner (e.g. largest populations first, or multiple signals).
- System changes mid-pilot → declare as a `SystemBreak`; do not compare across them.
- Staff turnover → quick guide plus recorded walkthrough.
