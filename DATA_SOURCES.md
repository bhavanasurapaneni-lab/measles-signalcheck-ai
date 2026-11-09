# Data Sources — Measles SignalCheck AI

**Milestone 2: WHO measles dataset discovery and validation**
Research date: 7 November 2026. Every number below was read live from official
sources on that date. No dataset has been saved to `data/` yet.

> **Update:** sections 1–9 record the first review, which proposed Zambia. Section 10 records the
> follow-up review: the Zambia district file covers 2018 only, so the core dataset recommendation
> is now **Brazil SI-PNI, Rio de Janeiro state** (see `PROJECT_DECISIONS.md`, D-001/D-002).

---

## 1. Summary

| Question | Answer |
|---|---|
| Is there an official WHO **multi-year, district-level** MCV1 dataset? | **Yes, but it is not publicly downloadable.** WHO has collected admin2 data annually since 2017 (2025 round: 147 Member States). The GHDx catalogue lists access as **"Microdata access: Request"**. I found no public file for 2017–2025. |
| Is any WHO district-level file public? | **Only one year.** An archived WHO file on HDX is described as "2016, 2017 and 2018", but its data tab contains **2018 rows only** (verified: 103,819 rows, all `Year = 2018`). |
| What *is* public and multi-year? | (a) National MCV1 **doses, target population and coverage** reported by each country (2000–2025). (b) WHO/UNICEF estimates (WUENIC), with every revision. (c) **The number of districts in each MCV1 coverage band**, plus the surviving infants living in those districts, per year. (d) District reporting completeness. (e) The country's own comments on its denominators. (f) Measles campaigns. |
| Recommended prototype country | **Zambia** |
| Recommended verifiable decline | **Zambia 2020 → 2021**: MCV1 fell 96% → 90% (WUENIC). WUENIC has kept that figure in every revision from 2021 to 2025. |
| Go / no-go | **Conditional GO.** See section 9. |

---

## 2. Datasets identified

### A. WHO subnational immunization coverage (admin1 / admin2), 2017–2025 (*restricted*)
- **Page:** https://www.who.int/teams/immunization-vaccines-and-biologicals/immunization-analysis-and-insights/global-monitoring/immunization-coverage/subnational-immunization-coverage-data
- **Catalogue record (2024 round):** https://ghdx.healthdata.org/record/subnational-immunization-coverage-data-reported-member-states-who-and-unicef-through-joint-7 (says "Microdata access: Request")
- **Contents (per WHO):** numerator (doses administered), denominator (eligible individuals) and coverage % for DTP1, DTP3 and **MCV1**, reported at admin2, or admin1 where admin2 isn't available. Collected through the WHO/UNICEF Joint Reporting Form (JRF).
- **Scale (2025 round, per WHO):** 147 Member States and more than 29,000 admin1/admin2 units, covering about 84% of the world's surviving infants. 102 countries report DTP3 at admin2 and 45 at admin1 only.
- **Status for us:** this is the ideal dataset, but I could **not verify a public download link**. WHO's limitations note gives `vpdata@who.int` as the contact for information.

### B. WHO subnational coverage, archived public file (2018 only in practice)
- **Page:** https://data.humdata.org/dataset/world-sub-national-immunization-coverage (marked "Archived", update frequency "Never", licence CC BY)
- **File:** XLSX hosted on Google Sheets, 5.0 MB, with sheets `ReadMe` and `Data`. Last update stated in the file: 20 Feb 2020.
- **Verified fields:** `iso, CountryName, WHORegion, Year, Admin1, Admin2, Vaccine, DenomType, Denominator, Numerator, Coverage`
- **Codes (from ReadMe):** DenomType 1 = live births, 2 = surviving infants. ND = −2222 (no data), NA = −4444 (not applicable).
- **Verified content:** all 103,819 data rows are `Year = 2018`. There are 24,889 MCV1 rows.
- **Usefulness:** a good format template and a single-year snapshot of data-quality problems. It **cannot show change over time**.

### C. WHO national coverage, multi-year (*public*)
- **Portal bulk download:** "All vaccination coverage data" →
  `https://srhdpeuwpubsa-geecgzbpd5h0fueu.z01.azurefd.net/whdh/WIISE/export/coverage-data.xlsx`
  (the link is published on https://immunizationdata.who.int/global; I haven't opened the file yet)
- **Same data via WHO's public API (queried live):** `https://xmart-api-public.who.int/WIISE/AD_COVERAGES`
- **Key fields:** `COUNTRY, YEAR, COVERAGE_CATEGORY (ADMIN | OFFICIAL | WUENIC), REVISION_YEAR, VACCINECODE, TARGETNUMBER, DOSES, PERCENTAGE, SOURCE`
- `ADMIN` = doses ÷ target as reported by the country. `OFFICIAL` = the country's official estimate. `WUENIC` = the WHO/UNICEF estimate, with one row per revision year.
- Missing values appear as `-9999` or blank.

### D. WHO "system performance": districts per coverage band (*public*)
- **API:** `https://xmart-api-public.who.int/WIISE/MT_RI_IND_DIST_LONG`
- For each country and year: **number of districts** with MCV1 coverage <50%, 50–79%, 80–89%, 90–94% or ≥95%, plus non-reporting districts. From 2020 onward, also the **surviving infants living in each band** (`*_POP_DISTRICTS_MCV1`).
- Gives a multi-year view of how coverage is spread across districts, but **not** which named district is in which band.

### E. WHO JRF programme indicators and comments (*public*)
- **API:** `MT_AD_IND_LONG` (e.g., `CALC_COMPLETENESS_PERCENT`, the % of district reports received nationally) and `AD_COMMENTS` (the country's own notes on denominators).

### F. WHO measles/rubella campaigns (SIAs) (*public*)
- **API:** `https://xmart-api-public.who.int/WIISE/V_SIA_MAIN_MR` (linked from the WHO portal)
- Campaign type, dates, age group, extent, target, doses and coverage.

> **Note on the API:** `xmart-api-public.who.int` is the public service that the WHO portal itself links to. I didn't find formal documentation promising it will stay stable, so in Milestone 3 we should save a dated copy (snapshot) of everything we use.

### Other sources checked (not suitable)
- **WHO AFRO data portal** (idataportal.afro.who.int): MCV1 coverage is country-level only. Its district-level datasets are for malaria vaccine.
- **PAHO measles country profiles:** municipal MMR1 tables, but as PDFs and Americas only.

---

## 3. Comparison of candidate countries

The admin2 columns are from source B (2018). The other columns are from sources C and D.

| Country | In 2018 admin2 file? | District count stable 2020–25? | Reported MCV1 doses & target every year? | Notable signal |
|---|---|---|---|---|
| **Zambia** | **Yes**: 110 districts, 10 provinces; 54 of 110 districts report >100% | **Yes**: 116 every year | Yes | A WUENIC-confirmed decline in 2021, *and* a large admin-only swing in 2022–23 |
| Philippines | **No** MCV1 rows | **No**: 120 units (2020) → 179 (2021) | Yes | Large WUENIC-confirmed decline in 2021 |
| Nigeria, Ethiopia, Afghanistan, India, Indonesia | Yes | Not checked in depth | Yes | Larger and more complex systems; better for a later stage |

**Why Zambia:** it is the only shortlisted country found in the public district file. Its 116 districts are a manageable number and stayed constant from 2020 to 2025. It has one decline WUENIC confirms and one admin-only change WUENIC does not, which is exactly the "real vs. data-quality" contrast this project is about. Zambia also explains its own denominator problems in its JRF comments.

---

## 4. Recommended prototype dataset: Zambia MCV1

### 4.1 National administrative data (source C, `COVERAGE_CATEGORY = ADMIN`, denominator = surviving infants)

| Year | Target (surviving infants) | MCV1 doses | Admin coverage | WUENIC (latest, rev 2025) |
|---|---:|---:|---:|---:|
| 2017 | 656,191 | 632,856 | 96.4% | 96% |
| 2018 | 675,509 | 634,999 | 94.0% | 94% |
| 2019 | 695,247 | 647,988 | 93.2% | 93% |
| 2020 | 735,358 | 703,631 | 95.7% | 96% |
| 2021 | 764,176 | 690,756 | 90.4% | 90% |
| 2022 | 824,726 | 824,063 | 99.9% | 88% |
| 2023 | 856,372 | 687,675 | 80.3% | 86% |
| 2024 | 887,246 | 752,148 | 84.8% | 91% |
| 2025 | 918,722 | 792,480 | 86.3% | 92% |

### 4.2 Districts per MCV1 coverage band (source D)

| Year | <50% | 50–79% | 80–89% | 90–94% | ≥95% | Total |
|---|---:|---:|---:|---:|---:|---:|
| 2020 | 0 | 28 | 28 | 15 | 45 | 116 |
| 2021 | 0 | 36 | 40 | 13 | 27 | 116 |
| 2022 | **39** | 22 | 4 | 1 | 50 | 116 |
| 2023 | 4 | 51 | 33 | 8 | 20 | 116 |
| 2024 | 1 | 40 | 39 | 9 | 27 | 116 |
| 2025 | – | 37 | 33 | 16 | 30 | 116 |

For 2020 and 2022, the infant populations across the five bands add up exactly to the national target (735,358 and 824,726), so the band data line up with the national figures.

### 4.3 Zambia's own JRF comments on denominators (source E)
- 2021–2024: "The denominators were extrapolated from the 2010 Zambia Statistical Agency (ZAMSTAT) Population Census."
- 2021–2024, listed factors affecting accuracy: "Use of obsolete population estimates", "Creation of new districts post the census".
- 2025: the denominators now come "from HMIS using ZAMSTAT populations extrapolated using the World Bank tool GFF FASTR tool."
- District reporting completeness (`CALC_COMPLETENESS_PERCENT`): **100%** every year 2020–2025. This counts **district reports reaching the national level**, not facility reports.

### 4.4 Measles/rubella campaigns recorded for Zambia (source F)
- Nov 2020: national follow-up campaign, ages 9–59 months.
- Nov–Dec 2022 and Jan 2023 to Jul 2024: several **subnational outbreak-response** campaigns, ages 6 months–10 years.
- Sep 2024 – Apr 2025: national follow-up campaign, ages 9–59 months.

---

## 5. Recommended verifiable decline: Zambia 2020 → 2021

| | 2020 | 2021 | Change |
|---|---:|---:|---:|
| WUENIC MCV1 | 96% | 90% | −6 points |
| Admin MCV1 | 95.7% | 90.4% | −5.3 points |
| Doses | 703,631 | 690,756 | −12,875 (−1.8%) |
| Target | 735,358 | 764,176 | +28,818 (+3.9%) |
| Districts ≥95% | 45 | 27 | −18 |

**Why this counts as independently verifiable:** WUENIC is a separate WHO/UNICEF review of the country's data. It has published 2021 as 90% in **every revision from 2021 to 2025**, and the WHO portal shows this publicly.

**What the arithmetic shows (and doesn't):** if the target had stayed at its 2020 size, the 2021 doses would give about 93.9%. So roughly 1.8 points of the drop come from fewer doses and roughly 3.5 points from the larger target, which Zambia itself says comes from 2010-census extrapolation. **The data do not tell us why doses fell.**

### Contrast case for the prototype: Zambia 2022 → 2023 (a likely data-quality signal, not a confirmed decline)
- Admin coverage: 99.9% → 80.3% (−19.6 points). WUENIC (rev 2025): 88% → 86% (−2 points).
- Doses rose **+19.3%** from 2021 to 2022, then fell **−16.6%** in 2023. The "decline" therefore follows an unusual one-year spike.
- **Internal inconsistency in 2022:** districts containing 454,481 surviving infants (55% of the national target) reported MCV1 **below 50%**. For the national total still to reach 99.9%, the remaining districts would need to average **at least about 161%**.
- WUENIC never accepted the 99.9% for 2022 (it published 90%, later revised to 88%).
- **Things to check, not conclusions:** outbreak-response campaign doses being counted as routine doses; problems mapping data to the newly created districts; denominator changes. None of these is confirmed by the data.

### Alternative headline example (not recommended as the base)
Philippines 2020 → 2021: admin coverage 72.0% → 57.1%, with doses down 20.5% and the target almost flat. WUENIC first published 72% → 57%, later revised to 79% → 64%. The decline is real and confirmed, but the Philippines has no public admin2 data, and its number of reporting units changed from 120 to 179.

---

## 6. What this data can and cannot prove

**It can show:**
- Whether a change in national MCV1 coverage comes from the numerator (doses), the denominator (target), or both.
- Whether WHO/UNICEF's independent estimate agrees with what the country reported, and how that estimate changed across revisions.
- Whether the spread of districts across coverage bands shifted, and how many infants live in low-coverage districts.
- Internal contradictions between the national figure and the district-band totals (as in Zambia 2022).
- In the 2018 file: named districts with coverage above 100%, missing values and implausible denominators.

**It cannot show:**
- **Which named districts declined after 2018.** That needs dataset A, or the country's own DHIS2/HMIS data.
- **Whether facility reports were missing.** WHO's completeness indicator counts district reports at national level, and it is 100% for Zambia in every year.
- The cause of a decline (outbreaks, stock-outs, staffing, conflict, policy).
- True coverage. WHO itself says it "has no means to challenge or validate district level administrative estimates".

**Additional data needed to investigate missing facility reports:**
1. **Facility reporting rates** (reports expected vs received, and on time) by month, for example DHIS2 dataset reporting rates.
2. **A master facility list** with opening and closing dates, so that new or closed facilities can be told apart from facilities that stopped reporting.
3. **Monthly MCV1 doses per facility**, to find facilities that suddenly report zero or stop reporting.
4. **Vaccine stock and stock-out records** (MCV / MR vaccine).
5. **Records of outreach and fixed sessions**, both planned and held.
6. **Campaign dose registers kept separate from routine doses.**
7. **Updated denominators** (the 2022 census-based projections) and the history of district boundary changes.
8. **Coverage surveys** (DHS/MICS) for triangulation, which are reliable at national or provincial level only.

---

## 7. WHO limitations (from WHO's own notes)
Sources: the WHO limitations PDF (last updated 15 July 2026), https://cdn.who.int/media/docs/default-source/immunization/data_statistics/limitations.pdf, and the HDX caveats.
(The copy retrieved on 7 Nov 2026 was 327,977 bytes, SHA-256 `1ef7190aaa3010c31b09047ff02c51e54b9e0709a0f3dba11e82427fbba94214`.)
- **Completeness:** for 2025, 47 Member States (about 24%) are missing. Reported admin2 units are about 62% of all admin2 worldwide.
- **Interpretation bias:** some "admin2" data is really admin1 or admin3, and some units aren't geographic at all (e.g., migrant populations or army camps).
- **Numerator errors** in tallying and reporting.
- **Inaccurate denominators** projected from old census data.
- **Numerator/denominator mismatch** caused by people moving between districts. As much as 26% of administrative units reported DTP3 coverage above 100%.
- District estimates usually **cannot be checked against surveys**.

---

## 8. Comparison with existing tools: what would Claude add?

| Tool | What it already does | Gap |
|---|---|---|
| **WHO Immunization Data Portal** | Charts and downloads of national data, WUENIC and district-band counts | Shows numbers; doesn't explain them or suggest next steps |
| **WUENIC process** | Expert review that reconciles admin data with surveys | Once a year, national level only, written for global audiences |
| **DHIS2 WHO Data Quality Tool** ([docs](https://docs.dhis2.org/en/use/optional-apps/who-data-quality-tool/usage-and-interpretation.html)) | Completeness, consistency over time, outliers, internal consistency (e.g., negative dropout) | Calculates flags but leaves interpretation to the officer; needs the country's own DHIS2 |
| **Immunization Data Quality Self-assessment (DQS)** | A structured field assessment method | Manual and periodic |

**What Claude would add (realistically):**
- Turning the calculated signals into a **plain-language explanation**, e.g. "coverage fell mainly because the target grew, not because doses fell".
- Combining **several sources at once** (admin vs WUENIC vs revisions vs district bands vs campaign records vs the country's own comments) into one investigation summary.
- Producing a **checklist of investigation steps** and questions to ask facilities and district staff.
- **Saying clearly what cannot be concluded**, and labelling every statement as either a computed fact or a hypothesis.

**What Claude must not do:** invent causes, create statistics, or present a hypothesis as a finding. All numbers will be computed in Python, and Claude will only explain the numbers it is given.

---

## 9. Go / no-go decision

**Conditional GO** for Milestone 3, with this scope:
1. **Build on Zambia, using sources C, D, E and F** (public, multi-year, official WHO data), plus the **2018 admin2 snapshot (B)** for named-district checks.
2. **Design the district module around the WHO admin2 format**
   (`Admin1, Admin2, Year, Vaccine, Denominator, Numerator, Coverage`), so that a real officer can later load their own DHIS2 export or the WHO dataset A without code changes.
3. **No synthetic or invented district data.** Any demo district data must come from a real, cited source.

**NO-GO** for claiming named-district trends from 2019 to 2025 from public WHO data, and for drawing any conclusion about missing facility reports.

---

## 10. Addendum (7 Nov 2026): data-gap review and a revised recommendation

### 10.1 Does the 2018-only district file support multi-year analysis?
**No.** Every row of the public WHO admin2 file is `Year = 2018` (verified), so it can't show a
change in any named district. The Zambia multi-year evidence in sections 4–5 is national,
plus counts of districts per coverage band; no individual district can be followed over time.

### 10.2 Other official, public, subnational sources checked

| Source | Level | Comparable years | Doses & denominator? | Verdict |
|---|---|---|---|---|
| **Brazil SI-PNI via DATASUS TabNet** (Ministry of Health) | State, health region (CIR), municipality | **1994–2022**, yearly | Coverage %, plus doses in a separate table (`dpnibr.def`); the coverage formula uses doses ÷ population | **Recommended.** Official, public, no login, verified live |
| **Zambia DHS** (DHS Program API, `CH_VACC_C_MSL`) | 10 provinces | 2013, 2018, 2024 | Survey %, with unweighted sample sizes of 128–311 children per province | Real, but small samples and no confidence intervals in the API. Use for triangulation only |
| WHO subnational 2017–2025 | admin1/admin2 | 2017–2025 | Yes | Access by request only |
| WHO AFRO data portal | National | — | — | Not subnational for MCV |
| India HMIS / NFHS | District | — | — | Not verified in this round |

### 10.3 Brazil, values verified live (TabNet, Tríplice Viral D1 coverage %)
TabNet notes: data source SI-PNI/CGPNI/DEIDT/SVS/MS; covers 1994–2022; data from 2023 on are in
separate "Cobertura Vacinal" dashboards; last updated May 2023; do **not** use the TOTAL
row/column when extracting.

**National vs WHO/UNICEF (independent check):**

| Year | TabNet | WHO JRF admin (doses / target) | WUENIC (rev 2025) |
|---|---:|---:|---:|
| 2015 | 96.07% | 96.07% (2,787,903 / 2,901,872) | 96% |
| 2018 | 92.61% | 92% (2,622,197 / 2,854,295) | 92% |
| 2019 | 93.12% | 91% (2,663,064 / 2,923,441) | 91% |
| 2020 | 80.88% | 79.46% (2,322,905 / 2,923,441) | 79% |
| 2021 | 74.94% | 73.46% (2,092,969 / 2,849,064) | 73% |
| 2022 | 80.70% | 80.66% (2,202,073 / 2,730,050) | 81% |

TabNet is about 1.5 points higher than the JRF submission for 2019–2021. That fits doses
being added after the JRF was submitted (TabNet was updated in May 2023), but this is **not yet confirmed**.

**Rio de Janeiro state by health region:**

| Health region (CIR) | 2019 | 2020 | 2021 |
|---|---:|---:|---:|
| RJ state | 96.58 | 61.61 | 59.48 |
| Baía da Ilha Grande | 98.06 | 57.52 | 60.03 |
| Baixada Litorânea | 80.89 | 60.16 | 48.65 |
| Centro-Sul | 91.12 | 80.06 | 75.20 |
| Médio Paraíba | 98.45 | 80.18 | 69.66 |
| Metropolitana I | 97.91 | 63.81 | 61.41 |
| **Metropolitana II** | 100.05 | **35.63** | 42.32 |
| Noroeste | 91.58 | 75.91 | 60.42 |
| Norte | 89.76 | 44.46 | 56.24 |
| Serrana | 98.51 | 82.58 | 71.24 |

**A data-quality example in the same source:** Federal District 67.58% (2015) → 131.75% (2016) → 78.50% (2017).

### 10.4 What the Brazil data can and cannot show
- **Can show:** multi-year coverage and doses for named health regions and municipalities; whether a change comes from doses or from the denominator; implausible values (>100%, one-year swings); how a unit compares with its state and neighbours.
- **Cannot show:** facility reporting completeness or missing facility reports; the cause of any change (COVID-19 disruption, registration-system changes, migration, stock-outs); 2023 onward in a comparable series. Subnational changes are **not** independently confirmed by WUENIC, which is national only. Possible independent checks (for example the 2020 national vaccination coverage survey of state capitals) still need to be verified.

### 10.5 Trade-offs of other options
- **Different geographic level (Zambia provinces, DHS):** real and comparable, but the sampling error is probably similar in size to the changes. Without confidence intervals, we would risk calling noise a decline.
- **Synthetic district scenario:** removes the data gap but breaks the "evidence-grounded" claim. Use only as labelled test fixtures (see `PROJECT_DECISIONS.md`, D-005).

## 11. Milestone 3 proof of concept: ingestion record (7 Nov 2026)

> The finished dataset documentation is in **`DATA_CARD.md`**. The loading code is `signalcheck.connectors.BrazilSIPNIConnector`.

### 11.1 Files retrieved (approved sample; raw files unchanged; git-ignored)
Folder: `data/raw/brazil_sipni/`. Fetch script: `scripts/fetch_tabnet.py`. Full query values are in `manifest.json`.

| File | What it measures | Period | TabNet filters | Bytes | SHA-256 (first 16) | Retrieved (UTC) |
|---|---|---|---|---:|---|---|
| `rj_mun_coverage_triplice_viral_d1_2015_2022.csv` | **Coverage %**, Tríplice Viral D1 (TabNet indicator code `021`) | 2015–2022 | Row = Município; Column = Ano; UF = Rio de Janeiro | 9,179 | `1877caa0c0b41a5f` | 2026-11-07 23:16:49 |
| `rj_mun_doses_triplice_viral_scr_d1_age1_2015_2022.csv` | **Doses administered** (count): Tríplice Viral (SCR) [codes 21,70,57], 1ª dose, age 1 year | 2015–2022 | Row = Município; Column = Ano; UF = RJ; vaccine, dose and age as listed | 7,532 | `c5fe40445a786340` | 2026-11-07 23:16:54 |
| `rj_mun_sinasc_live_births_residence_2014_2021.csv` | **Live births** (count) by mother's municipality of residence (SINASC) | 2014–2021 | Row = Município; Column = Ano do nascimento; files nvrj14–nvrj21 | 6,450 | `1364693f32e7608c` | 2026-11-07 23:16:59 |

Query pages:
- Coverage form `http://tabnet.datasus.gov.br/cgi/dhdat.exe?bd_pni/cpnibr.def`, submitted to `…/cgi/webtabx.exe?bd_pni/cpnibr.def`
- Doses form `…/cgi/dhdat.exe?bd_pni/dpnibr.def`, submitted to `…/cgi/webtabx.exe?bd_pni/dpnibr.def`
- SINASC form `…/cgi/deftohtm.exe?sinasc/cnv/nvrj.def`, submitted to `…/cgi/tabcgi.exe?sinasc/cnv/nvrj.def`

The CSV URLs that TabNet generates are temporary; the manifest records the ones used.

### 11.2 Public aggregate data only
Each file holds one row per municipality, one column per year and a Total, plus title and footnote lines for SINASC. There are **no person-level fields** (no names, IDs, dates of birth or addresses). The smallest cell is a municipality-year count; the smallest dose count is 6 (IBGE 330093, 2021). A test checks the header structure.

### 11.3 Validation results (`pytest`, 11 of 11 passed)
- **Municipality codes:** 92 six-digit IBGE codes, all starting with `33` (Rio de Janeiro), and the same set in all three files.
- **Years:** coverage and doses 2015–2022; births 2014–2021.
- **Missing or unparseable values:** none. There are no zero dose counts.
- **Types:** doses and births are non-negative integers; coverage is a non-negative percentage.
- **Births with unknown municipality:** SINASC has a row "MUNICIPIO IGNORADO – RJ" (5–23 births a year). It is **excluded and reported**; municipal births plus this row equal TabNet's total.
- **Totals:** the sum of municipal doses equals TabNet's Total row in every year.
- **Agreement with values read earlier:** state coverage matches the figures from the health-region query (96.58% / 61.61% / 59.48% for 2019 / 2020 / 2021).
- **Hashes:** each file's SHA-256 matches the manifest.
- **Coverage above 100% (observed):** 59, 68, 42, 56, 31, 14, 6 and 6 municipalities in 2015–2022 respectively.

### 11.4 Doses vs coverage: what each number means
- **Doses** are a count of recorded MMR first doses given to 1-year-olds, attributed to the municipality where they were *recorded*. They need no denominator.
- **Coverage %** is the Ministry's published indicator, calculated as doses ÷ the target population (`NU_POPULACAO`) × 100. **The target population isn't published as its own figure.**
- **Is the dose filter the right numerator?** At national level, TabNet doses ÷ TabNet coverage gives target populations within 0.1% of what Brazil reported to WHO: 2,921,800 vs 2,923,441 (2019); 2,923,358 vs 2,923,441 (2020); 2,848,999 vs 2,849,064 (2021). So the filter matches the official numerator.
- **Where the denominator comes from:** at state level it is roughly **live births two years earlier, from an earlier extract**. For example, the 2021 implied denominator is 208,028, against 207,989 births in 2019 in today's SINASC. 2019 and 2020 share the same national denominator. This explains coverage above 100% and means published municipal coverage **can't be reproduced exactly** from current SINASC.
- **Rule:** we report **doses** as the primary observed change. Published coverage is quoted as published. Any coverage we recalculate with SINASC is labelled as a *sensitivity check*, never as official coverage.

### 11.5 The one municipality comparison: São Gonçalo (IBGE 330490), 2019 vs 2020
**Why the two years are comparable:** same system (the old SI-PNI, before the 2023 change), same indicator definition, same dose filter, same denominator method, and both years are final.

| Observed | 2019 | 2020 | Change |
|---|---:|---:|---:|
| MMR1 doses, age 1 (count) | 13,396 | 4,096 | **−69.4%** |
| Published coverage (%) | 121.66 | 35.77 | −85.9 points |
| SINASC live births, previous year (independent denominator) | 10,969 (2018) | 10,432 (2019) | −4.9% |
| *Sensitivity check:* doses ÷ previous-year births | 122.1% | 39.3% | — |
| *Sensitivity check:* doses ÷ births two years earlier | 118.6% | 37.3% | — |

**What it shows:** the fall in published coverage comes mainly from **recorded doses**, not from a change in the denominator. Births fell 4.9%; doses fell 69.4%. Whichever official denominator is used, coverage falls by more than 80 points.
**What it does not show:** whether fewer children were vaccinated or fewer doses were *recorded or transmitted*. The 2019 coverage above 100% also suggests children from neighbouring municipalities may have been vaccinated in São Gonçalo. **This is not confirmed as a change in vaccination uptake.**

The same pattern appears elsewhere: 16 of the 92 municipalities recorded >50% fewer doses in 2020 than in 2019. These include Belford Roxo (−87.4%), Macaé (−86.7%), Niterói (−80.5%), Nova Iguaçu (−72.0%) and Duque de Caxias (−71.9%). Statewide, doses fell 36.4%.

### 11.6 The 2023 SI-PNI / RNDS transition and comparability
| Change | Status of evidence | Effect on comparisons |
|---|---|---|
| Data entry into the old SI-PNI web and desktop systems ended 31 May 2023; a new SI-PNI routine module started 1 Jun 2023, connected to RNDS | **Confirmed** (Ministry of Health news, 1 Jun 2023) | 2023 mixes two systems within one year |
| TabNet immunization series covers 1994–2022; data from 2023 on is on separate coverage dashboards; last updated May 2023 | **Confirmed** (TabNet notes) | **Don't join TabNet 2022 with dashboard data from 2023 on** |
| New coverage method from 2024: numerator from RNDS dose records, people counted once by CPF/CNS, results by residence or place of vaccination | **Not verified directly** (from document titles and secondary summaries; PDFs couldn't be decoded) | Numerator and place attribution may differ from TabNet |
| TabNet doses are attributed to the place where the dose was recorded; SINASC births to the mother's residence | **Observed** in the export definitions | Contributes to coverage above 100% and to swings between neighbouring municipalities |

**Supported comparison window:** 2015–2022, all 92 Rio de Janeiro municipalities, for doses and published coverage. Within that window, 2020–2021 may still reflect COVID-19 disruption and/or registration problems. The data can't tell them apart.

### 11.7 Missing fields, limitations and discrepancies
- **Missing:** the published denominator; facility-level reporting or completeness; monthly data (available, but not fetched); place of residence of vaccinated children; campaign-dose separation in coverage (excluded by the dose filter, but not verified for every municipality).
- **Discrepancy 1:** national TabNet doses are higher than the doses in Brazil's WHO submission (2019: 2,720,782 vs 2,663,064, +2.2%). This fits records added after the JRF, since TabNet was last updated in May 2023, but it's not confirmed.
- **Discrepancy 2:** published municipal denominators don't equal current SINASC births for either the previous year or two years earlier. The implied ÷ SINASC ratio has a median of about 0.99–1.04, with wider spread in small municipalities.
- **Discrepancy 3:** SINASC itself was revised after PNI froze its denominators. The SINASC footnote says final data runs to 2024, extracted 2 Dec 2025.

## 12. Source list
- WHO subnational coverage page: https://www.who.int/teams/immunization-vaccines-and-biologicals/immunization-analysis-and-insights/global-monitoring/immunization-coverage/subnational-immunization-coverage-data
- WHO limitations note (PDF): https://cdn.who.int/media/docs/default-source/immunization/data_statistics/limitations.pdf?sfvrsn=3597a47c_24
- WHO descriptive analysis (PDF): https://cdn.who.int/media/docs/default-source/immunization/data_statistics/web-subnational.pdf?sfvrsn=d3b7e376_30
- WHO Immunization Data Portal: https://immunizationdata.who.int/global
- WHO public data API (WIISE): https://xmart-api-public.who.int/WIISE
- GHDx record (2024 subnational data, access on request): https://ghdx.healthdata.org/record/subnational-immunization-coverage-data-reported-member-states-who-and-unicef-through-joint-7
- HDX archived WHO subnational file: https://data.humdata.org/dataset/world-sub-national-immunization-coverage
- DHIS2 WHO Data Quality Tool docs: https://docs.dhis2.org/en/use/optional-apps/who-data-quality-tool/usage-and-interpretation.html
- DATASUS TabNet, immunization coverage (Brazil): http://tabnet.datasus.gov.br/cgi/dhdat.exe?bd_pni/cpnibr.def
- DATASUS TabNet, doses applied (Brazil): http://tabnet.datasus.gov.br/cgi/dhdat.exe?bd_pni/dpnibr.def
- DHS Program API: https://api.dhsprogram.com/rest/dhs/data?countryIds=ZM&indicatorIds=CH_VACC_C_MSL&breakdown=subnational
