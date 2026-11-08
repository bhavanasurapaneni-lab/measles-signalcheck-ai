# Evaluation Report — Measles SignalCheck AI

*Milestone 7, Nov 2026. Every number below comes from the repository's automated tests and scripts, run locally
(Windows 11, Python 3.12.10, pytest 9.2.0, anthropic SDK 2.6.0, Streamlit 1.67.0).*

> **Scope statement.** This report covers data validation, deterministic rules and an **offline** evaluation of
> the brief-validation layer. **No live Claude API evaluation has been performed (deferred, D-025)**, so this report
> makes no claim about Claude's real accuracy, refusal rate, latency or cost on this task. Nothing here amounts to
> clinical or epidemiological validation, or evidence of production reliability.

## 1. Summary
| Area | Result |
|---|---|
| Automated tests | **133 passed, 0 failed, 0 skipped** with data (`pytest -q`, about 60–120 s). Without data (fresh clone, and the GitHub Actions CI): 30 passed, 103 skipped, 0 failed |
| Data integrity | 3 raw exports match their SHA-256 manifest. 92 municipalities; years complete; 0 missing or unparseable cells |
| Agreement with published figures | State coverage reconstructed from municipal values is within 0.3 pts of TabNet totals (2019–2021). National dose filter reproduces Brazil's WHO-reported target population within 0.1% |
| Evidence packets | 644 municipality-year packets (92 × 7) built and validated: 0 failures of schema, reference, grounding or language checks |
| Brief validator (offline, synthetic drafts) | **20 / 20** expected verdicts (18 / 18 known-bad drafts rejected or sent to review; 2 / 2 known-good accepted) |
| Simulated API outcomes | 11 / 11 mapped to the intended explicit status |
| Live Claude evaluation | **Deferred. Not run. $0 spent.** |

## 2. Test inventory
| File | Tests | What it covers |
|---|---:|---|
| `tests/test_brazil_poc.py` | 11 | Manifest hashes, aggregate-only headers, IBGE codes, years, types, totals, published state values, São Gonçalo reference values |
| `tests/test_connector.py` | 18 | Canonical schema; separate measures; raw files unchanged; reproducible São Gonçalo case; coverage safeguards; refusal across 2023; altered, missing or invalid inputs; NaN reported, not imputed |
| `tests/test_signals.py` | 35 | Real reference cases; stable control; weighted state benchmark; reproducible packets for all units; synthetic anomaly fixtures; negative tests for unsupported interpretations |
| `tests/test_briefs.py` | 43 | Observations; request contract; 20 draft cases; capital-name rule; accuracy metrics; every API failure path; refusal without fallback; truncation; offline mode; no key in source |
| `tests/test_dashboard.py` | 18 | Region mapping; weighted series; region totals equal state; signal table; demo briefs validate; headless app run; all periods and regions; empty results; missing or altered data; app never imports the API client |
| `tests/test_fetch_safety.py` | 8 | Download scripts contact only tabnet.datasus.gov.br (incl. redirects); HTML error pages rejected; existing snapshots never overwritten without `--force` |
| **Total** | **133** | |

## 3. Numerical and citation grounding checks (verified)
**Data layer (observed values)**
- São Gonçalo (IBGE 330490): doses 13,396 → 4,096 (−69.4%); published coverage 121.66% → 35.77%; SINASC births 10,969 → 10,432 (−4.9%). Asserted in three test files.
- State totals: summed doses 215,599 (2019) and 137,112 (2020) equal TabNet's Total row. Weighted coverage 96.46 / 61.91 / 59.44, against TabNet 96.58 / 61.61 / 59.48. An unweighted mean would give 72.72% for 2020 (guarded by a test).

**Packet layer**
- Every number in every signal statement and caution must equal a fact or derived value (at the displayed rounding), a year in scope, or a configured threshold. Otherwise the packet is rejected.
- Every evidence and input ID must resolve. Back-calculated denominators must carry the `back_calculated_not_observed` label. SINASC facts must carry `independent_reference`.

**Brief layer** (`brief_validator.py`): Claude's text may contain **no digits or spelled-out numbers**. Every number shown comes from Python-generated observations. Claim checks:

| Check | Method | Deterministic? |
|---|---|---|
| Value and units | No numbers allowed in model text; values come only from O# statements | Yes |
| Municipality | Names any of the other 91 RJ municipalities or a Brazilian state → reject | Yes (gazetteer) |
| Year or period | Digits banned, so no years can be written | Yes |
| Indicator | Words for doses, coverage, births or state must match the cited observations' indicators | Yes (lexical) |
| Direction and magnitude | Increase or decrease words must match the observation's direction; minimising words rejected | Yes (lexical) |
| Citations | IDs exist; evidence claims cite; every observation is discussed or explicitly skipped | Yes |
| Causal or uptake claims | Pattern lists; possible explanations must be hedged and not asserted | Yes (lexical) |
| Interpretation supported by the evidence | **Not fully verifiable**; interpretive verbs go to `needs_human_review` | No |

**Metrics reported per brief:** `citation_accuracy` (share of evidence-citing claims with valid, consistent citations) and `grounding_accuracy` (share of evidence-supported claims that pass every check). On the known-good draft both are 1.0. On the wrong-indicator draft both are below 1.0.

## 4. Offline evaluation methodology
1. **Inputs:** 12 real evidence packets (reference cases, stable controls, a small-denominator case, the capital, and a recovery year) plus 2 synthetic packets (`SYNTHETIC_TEST_FIXTURE`).
2. **Drafts:** 20 hand-written `BriefDraft`s for the São Gonçalo packet: 2 compliant, and 18 each embodying one failure mode.
3. **Simulated API:** `evals/fake_client.py` raises real SDK exception classes, or returns scripted responses, through the production `generate_brief()` code path.
4. **Gate:** every verdict must match the expected verdict (`evals/run_offline.py`; results in `evals/results/offline_20261107.json`).

### Adversarial and failure cases
| Case | Expected | Result |
|---|---|---|
| Correct citation ID, incorrect number ("fell by 72%") | rejected | ✅ |
| Number in words ("seventy percent") / multiplier ("twice") | rejected | ✅ ✅ |
| Correct observation, wrong municipality (Niterói) | rejected | ✅ |
| Correct observation, wrong years ("2020 and 2021") | rejected | ✅ |
| Wrong direction ("rose") / minimised ("slightly") | rejected | ✅ ✅ |
| Wrong indicator (coverage claim citing a doses observation) | rejected | ✅ |
| Dangling citation (O9) / observation silently omitted | rejected | ✅ ✅ |
| Causal claim (vaccine hesitancy) / uptake claim ("fewer children were vaccinated") | rejected | ✅ ✅ |
| Explanation asserted as fact / "could be confirmed as…" / action asserting a cause | rejected | ✅ ✅ ✅ |
| Prompt-injection echo in the headline | rejected | ✅ |
| No verification action | rejected | ✅ |
| Interpretive wording ("indicates a service problem") | needs_human_review | ✅ |
| Contradictory (tampered) packet | invalid_packet, API not called | ✅ |
| Injection in unit name (synthetic packet) | passes preflight by design; output validator is the control | ✅ (offline only) |
| Missing evidence (synthetic packet) | `insufficient_evidence`, never treated as zero | ✅ |
| Rate limit, 5xx, connection, timeout, bad request | api_error | ✅ |
| Authentication or permission / unknown model | auth_error / config_error | ✅ |
| Refusal | refused (no fallback) | ✅ |
| Truncation / missing structured output | truncated / rejected | ✅ |

## 5. Limitations of simulated model responses
- All 20 drafts were **written by the project author**. They test the validator, **not Claude**. Real model output may fail in ways not anticipated here (paraphrased numbers, subtle overstatement, unusual phrasing), or may pass more or less often than these cases suggest.
- The fake client reproduces SDK exception types and response shapes. It doesn't reproduce real latency, rate limits, token usage, prompt-cache behaviour or refusal categories.
- Lexical checks can be bypassed by wording outside the pattern lists. They can also wrongly reject valid text (for example, a municipality name used in another sense).

## 6. Signal rules on real data (descriptive, not a performance claim)
Statewide scan of 644 municipality-year pairs, consecutive years from 2015 to 2022:

| Signal | Pairs flagged |
|---|---:|
| recorded_dose_change (≥30%) | 173 |
| reported_coverage_change (≥30 pts) | 188 |
| implausible_coverage (>100%) | 347 |
| state_benchmark_divergence (≥25 pts) | 205 |
| small_denominator_caution | 38 |

These counts show high volatility in municipal administrative data. Thresholds are review triggers, not tuned or validated cut-offs, and **no ground truth exists to measure precision or recall of real data-quality problems**.

## 7. Live Claude API evaluation — DEFERRED
- **Prepared (not run):** `evals/run_live.py`. It covers 14 cases (12 real, 2 synthetic), with a spend ledger, a per-call worst-case gate and `--only`/`--skip` smoke testing. The offline estimate was about $0.84 expected and $2.41 maximum.
- **Would measure:** acceptance, review, rejection and refusal rates; citation and grounding accuracy on real output; compliance with the no-digit rule; prompt-cache hits; latency; cost.
- **Status:** not executed. No API key configured. $0 spent.

## 8. Unresolved risks
1. Real model behaviour is unmeasured.
2. Semantic faithfulness is only partly verifiable by rules.
3. The official denominator is unpublished, and recorded doses ≠ vaccinations.
4. 2020–2021 mixes possible service disruption with registration effects.
5. Signal volume is high, so prioritisation is still needed.
6. The 2024 method change isn't verified from the primary source. TabNet vs WHO-reported doses differ by +2.2% (2019), unexplained.
7. There's no ground truth for real data-quality problems.
8. Untested with real coordinators.

## 9. Reproduce
```powershell
.\.venv\Scripts\python.exe -m pytest -v          # 133 tests
.\.venv\Scripts\python.exe -m evals.run_offline   # validator evaluation + simulated API outcomes
.\.venv\Scripts\python.exe scripts\run_signals.py # statewide scan (counts in section 6)
```
