# Data Card — Brazil SI-PNI MMR1 sample (Rio de Janeiro, 2014–2022)

| | |
|---|---|
| **Dataset ID** | `brazil_sipni_tabnet` |
| **Version** | Snapshot retrieved 7 Nov 2026 (UTC 23:16), 3 files, 23,161 bytes |
| **Publisher** | Ministério da Saúde, Brazil: DATASUS TabNet (SI-PNI immunization data; SINASC live births) |
| **Access** | Public, no login, aggregate tables only |
| **Connector** | `signalcheck.connectors.BrazilSIPNIConnector` (fetch: `scripts/fetch_tabnet.py`) |
| **Provenance** | `data/raw/brazil_sipni/manifest.json`: URLs, exact query selections, timestamps, SHA-256 |
| **Raw data in Git?** | No. `data/raw/` is git-ignored; run the fetch script to reproduce |

---

## 1. Purpose and intended use
To support **investigation** of changes in recorded measles-containing vaccine first-dose (MMR1) activity in Rio de Janeiro municipalities. Typical questions: "Did recorded doses fall, or did the denominator change?" and "Which municipalities show changes worth checking?"

**Not intended for:** official coverage estimates, ranking municipal performance, causal attribution, or individual-level analysis.

## 2. Geography
- Rio de Janeiro state (IBGE UF code **33**), **92 municipalities**, each identified by a 6-digit IBGE code (`33xxxx`).
- SINASC also has a row "MUNICIPIO IGNORADO – RJ" (births with unknown residence, 5–23 a year). It is **excluded and reported**, not redistributed.

## 3. Time periods
| Measure | Years | Status |
|---|---|---|
| Doses administered | 2015–2022 | Final (TabNet last updated May 2023) |
| Published coverage | 2015–2022 | Final (same) |
| Live births (SINASC) | 2014–2021 | Final. SINASC is revised over time; its footnote says final data runs to 2024, extracted 2 Dec 2025 |

**Supported comparison window: 2015–2022.** The connector refuses comparisons that cross 2023 (see §7).

## 4. Measures (kept separate in the `measure` column)
| `measure` | Definition | Unit | Attribution | Kind |
|---|---|---|---|---|
| `doses_administered` | Recorded doses of Tríplice Viral (SCR) [TabNet codes 21, 70, 57], **1st dose**, given to children **aged 1 year** | count | `place_of_recording` (municipality where the dose was recorded) | numerator |
| `published_coverage_pct` | Ministry indicator "Tríplice Viral D1" (code `021`) = doses ÷ target population × 100 | percent | `as_published` | published indicator |
| `live_births` | SINASC live births by **mother's municipality of residence** | count | `mother_residence` | denominator (sensitivity only) |

Schema (`signalcheck.schema.COLUMNS`): `source_id, country_iso3, admin1_code, unit_code, unit_name, year, measure, value, attribution, system_period`.

## 5. Methodology
1. **Collection:** `scripts/fetch_tabnet.py` sends the documented TabNet queries and saves TabNet's own CSV byte-for-byte, recording hashes in the manifest.
2. **Loading:** the connector checks every hash (and stops if any file is altered or missing), parses the Latin-1, semicolon-separated tables with Brazilian number formatting, and checks codes, years and that the municipality set is the same in every file.
3. **Missing values:** unparseable or blank cells (`-`, empty) become `NaN` and are listed in the quality report. **Nothing is imputed.**
4. **Coverage:** the tool **does not recalculate official coverage**. `signalcheck.coverage.sensitivity_coverage()` computes doses ÷ SINASC births of the previous year only when both values exist, the denominator is greater than 0, the pair is declared compatible, and the years are comparable. The result is labelled *"sensitivity estimate … not official coverage"*.
5. **Validation:** 29 automated tests (`pytest`). See §8.

### How we confirmed the dose numerator
At national level, TabNet doses ÷ TabNet coverage reproduces the target population Brazil reported to WHO within 0.1% (2019: 2,921,800 vs 2,923,441; 2020: 2,923,358 vs 2,923,441; 2021: 2,848,999 vs 2,849,064).

## 6. Data quality (observed in this snapshot)
| Check | Result |
|---|---|
| Missing or unparseable cells | 0 |
| Municipalities, identical across files | 92 / 92 |
| Municipal doses sum to TabNet total | Yes, every year |
| Zero dose counts | 0 (minimum 6) |
| Municipalities with published coverage >100% | 59, 68, 42, 56, 31, 14, 6, 6 (2015→2022) |
| Municipalities with >50% fewer recorded doses, 2019→2020 | 16 |
| Statewide change in recorded doses, 2019→2020 | −36.4% |

## 7. Known limitations
1. **2023 reporting-system break (confirmed).** Data entry into the old SI-PNI ended on 31 May 2023, and a new SI-PNI integrated with RNDS began on 1 Jun 2023. TabNet's series ends in 2022. **Do not compare 2022 with 2023 or later.** The connector raises `ComparabilityError`.
2. **New coverage method from 2024 (not directly verified).** It reportedly uses an RNDS-only numerator and counts people once by CPF/CNS. Treated as a second break.
3. **Unpublished denominator.** Published coverage uses an internal target population. At state level it approximates SINASC births from **two years earlier, from an older extract**, and it can't be reproduced exactly from current SINASC. 2019 and 2020 share the same national denominator.
4. **Mismatched attribution.** Doses are counted where recorded and births where the mother lives. This explains much of the coverage above 100% and the swings between neighbouring municipalities.
5. **Recorded is not the same as vaccinated.** Changes may reflect vaccination, recording, transmission between systems, migration or denominator effects. **The data can't tell these apart.**
6. **2020–2021** may combine COVID-19 service disruption with registration-system effects.
7. **Small municipalities** give volatile percentages: 9 municipalities had fewer than 100 births in at least one year (minimum 60).
8. **Not included:** facility-level reporting completeness, monthly data, place of residence of vaccinated children, and confidence intervals (administrative data has none).
9. **Unresolved discrepancy:** national TabNet doses are higher than the doses in Brazil's WHO submission (2019: +2.2%). This fits records added later, but is not confirmed.

## 8. Reproducible reference example: São Gonçalo (330490), 2019 → 2020
Tested in `tests/test_connector.py::test_sao_goncalo_2019_2020_reproducible`.

| | 2019 | 2020 |
|---|---:|---:|
| Doses administered (observed) | 13,396 | 4,096 (−69.4%) |
| Published coverage (observed) | 121.66% | 35.77% |
| SINASC births, previous year (observed) | 10,969 (2018) | 10,432 (2019) (−4.9%) |
| Sensitivity estimate (doses ÷ previous-year births) | 122.13% | 39.26% |

**Permitted reading:** "Recorded MMR1 doses in São Gonçalo fell 69% between 2019 and 2020, while births changed by about 5%. The fall in published coverage is therefore driven by recorded doses, not the denominator."
**Not permitted:** "Fewer children were vaccinated", or any statement of cause.

## 9. Permitted and prohibited interpretations
| ✅ Permitted | ❌ Not permitted |
|---|---|
| Describe observed changes in recorded doses and published coverage within 2015–2022 | Present a recalculated percentage as official coverage |
| Say whether a change in coverage is driven by the numerator or the denominator | Compare 2015–2022 values with 2023+ dashboards |
| Flag municipalities for **investigation** (large drops, values >100%, swings) | Infer causes (COVID, hesitancy, stock-outs, system problems) without other evidence |
| Use SINASC-based coverage as a labelled sensitivity check | Rank or judge municipal performance on this data alone |
| | Treat a change in reporting as a confirmed change in uptake |

## 10. Derived values and signals (Milestone 4)
Signals are **review triggers** computed by `signalcheck.signals` (thresholds in `config/signal_thresholds.toml`). They are packaged as evidence packets that follow `schemas/evidence_packet.schema.json`.

| Derived label | Meaning |
|---|---|
| `observed_change` | Arithmetic on observed values (e.g., relative change in doses) |
| `back_calculated_not_observed` | doses ÷ published coverage × 100. **Not observed, and not SINASC** |
| `mathematical_decomposition` | Identity of published values; **cannot establish cause** |
| `state_benchmark_weighted` | Ratio of summed doses over all units (not an average of percentages) |
| `independent_reference_change` | Change in SINASC births. **Context only; never used to classify a change** |

Classifications: `recorded_dose_change`, `reported_coverage_change`, `implausible_coverage`, `state_benchmark_divergence`, `small_denominator_caution`, `insufficient_evidence`. A statewide scan of 644 municipality-year pairs raised 173 recorded-dose-change, 188 reported-coverage-change, 347 implausible-coverage, 205 state-divergence and 38 small-denominator signals. Reference example: `docs/examples/evidence_packet_330490_2019_2020.json`.

## 11. Privacy and AI use
- The data is aggregate (municipality × year counts and percentages) and contains no personal identifiers.
- **Only validated, aggregate evidence packets** (reduced to observation statements, limitations and prohibited interpretations) may be sent to the Claude API. No identifiable health records are used at any stage. See `docs/SECURITY_AND_GOVERNANCE.md`.
- In investigation briefs, every number comes from Python-generated observations. Claude writes narrative only, and each brief is validated and labelled accepted, needs human review, or rejected. **Acceptance does not prove any public-health conclusion.**

## 12. Citation
Ministério da Saúde, Brasil. DATASUS TabNet: *Imunizações – Cobertura* and *Imunizações – Doses Aplicadas* (SI-PNI/CGPNI/DEIDT/SVS/MS, 1994–2022), and *Nascidos Vivos – Rio de Janeiro* (SINASC/CGIAE/SVSA). Accessed 7 Nov 2026 via http://tabnet.datasus.gov.br/.
