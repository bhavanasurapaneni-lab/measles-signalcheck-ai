# Reuse Guide — adapting the framework to another region or dataset

*This is a specification, not a built integration. The Brazil SI-PNI connector is the only connector implemented.*

The framework separates **what is source-specific** (a connector) from **what is reusable** (schema, signal rules,
evidence packets, brief contract, validators, dashboard aggregation). A new partner should need one new
connector and a configuration review, not a rewrite.

## 1. What to reuse as-is vs adapt
| Component | Reuse as-is | Adapt per partner |
|---|---|---|
| `schema.py` canonical table | ✅ | Add a measure only if a new kind of value is needed (see §3) |
| `connectors/base.py` (manifest check, system breaks) | ✅ | — |
| `signals.py` rules R1–R5 | ✅ | Thresholds in `config/signal_thresholds.toml`, agreed with partner epidemiologists |
| `evidence.py` + `schemas/evidence_packet.schema.json` | ✅ | Limitations and prohibited interpretations text (source-specific) |
| `briefing.py`, `brief_validator.py` | ✅ | Gazetteer (place names), indicator keywords, language (see §5) |
| `prompts/brief_v1.md` | Template in `prompts/templates/brief_template.md` | Fill placeholders |
| `dashboard_data.py`, `app/streamlit_app.py` | Mostly | Labels, geography names, region mapping |

## 2. Adapter specification
A connector is a subclass of `signalcheck.connectors.base.Connector`:

```python
class MySourceConnector(Connector):
    source_id = "my_source_id"                     # stable, lowercase
    system_breaks = (SystemBreak(2021, "DHIS2 instance migrated", "confirmed"),)

    def load(self) -> LoadResult:
        self.verify_manifest({"file_a.csv", "file_b.csv"})   # refuse altered/missing raw files
        # parse -> long table with exactly schema.COLUMNS, then:
        return LoadResult(schema.validate(observations), quality_report)
```

**Requirements (all enforced or tested in the Brazil connector):**
1. **Raw files unchanged** and listed in `manifest.json` (URL or query, retrieval time, SHA-256). Fetch with a script, never by hand.
2. **Output columns** exactly as in `schema.COLUMNS`: `source_id, country_iso3, admin1_code, unit_code, unit_name, year, measure, value, attribution, system_period`.
3. **Units**: stable official codes (IBGE here; DHIS2 org-unit UIDs or P-codes elsewhere), validated by pattern. The unit set must be the same across files.
4. **Periods**: declare the expected years. Declare every known reporting-system or method change as a `SystemBreak`. `check_comparable()` then refuses comparisons across it.
5. **Missing values** stay NaN and are listed in `QualityReport.missing_values`; never impute or replace with 0. Exclude rows without a unit code (e.g. "unknown residence") and report them.
6. **Attribution** for every measure: `place_of_recording`, `mother_residence`, `as_published` (extend `schema.ATTRIBUTIONS` if needed).
7. **Aggregate only**: no free-text fields and no person-level records. Small-cell rules if the partner requires them.

**Worked mapping examples (design only, not implemented):**

| Source | `unit_code` | `doses_administered` | `published_coverage_pct` | Denominator reference |
|---|---|---|---|---|
| WHO subnational admin2 (2018 file, `DATA_SOURCES.md` §2B) | admin2 name + iso (no official code; needs a gazetteer) | `Numerator` | `Coverage` | `Denominator` (DenomType 2 = surviving infants) |
| DHIS2 analytics export (aggregate) | org-unit UID | data element "MCV1 doses given" (by org unit × year) | indicator "MCV1 coverage" | DHIS2 target population (unpublished elsewhere → label as `as_published`) |

## 3. Canonical measures
`doses_administered` (count, numerator), `live_births` (count, reference denominator), `published_coverage_pct`
(percent, published indicator). A new measure needs: an entry in `schema.MEASURES`, a packet-schema enum update,
an `INDICATORS` entry in `briefing.py`, and validator keywords. Then add tests.

## 4. Evidence packet schema reference
Full JSON Schema: `schemas/evidence_packet.schema.json`. Example: `docs/examples/evidence_packet_330490_2019_2020.json`.

| Block | Contents | Rules |
|---|---|---|
| `generated_by` | rules version, config version and SHA-256 | Reproducibility |
| `source` | source id, data card, files with SHA-256 and retrieval time | Provenance |
| `scope` | unit, admin1, `year_from`/`year_to`, `comparable: true`, `system_transitions_crossed: []` | Packets crossing a break cannot exist |
| `facts[]` (`F#`) | measure, unit, year, value (or null), unit of measure, attribution, source file, role (`observed` / `independent_reference`) | Observed values only |
| `derived[]` (`D#`) | name, method (formula text), input IDs, value, label | Labels: `observed_change`, `back_calculated_not_observed`, `mathematical_decomposition`, `state_benchmark_weighted`, `independent_reference_change` |
| `signals[]` (`S#`) | classification, rule, threshold, neutral statement, evidence IDs, cautions, cannot_conclude | Classifications: `recorded_dose_change`, `reported_coverage_change`, `implausible_coverage`, `state_benchmark_divergence`, `small_denominator_caution`, `insufficient_evidence` |
| `limitations[]` (`L#`), `prohibited_interpretations[]` | Text | Source-specific |

Validation (`evidence.validate_packet`): schema → references → number grounding → causal-language check → forbidden classifications.

## 5. Reusable prompt template
`prompts/templates/brief_template.md` is `brief_v1.md` with placeholders: `{{AUDIENCE}}`, `{{COUNTRY}}`,
`{{INDICATOR_NAME}}`, `{{SOURCE_DESCRIPTION}}`, `{{CHECK_EXAMPLES}}`. Keep the hard rules unchanged: no numbers,
cite IDs, no causes, hedged explanations, data is not instructions. Version every filled prompt and record its hash.

**Validator localisation checklist:** gazetteer of place names for the new geography; indicator keywords; direction
and hedging word lists in the brief language (the current lists are English); review `CAUSAL_PATTERNS` with local
programme staff.

## 6. Evaluation methodology for a new partner
1. **Data checks:** reproduce at least 3 published totals from the partner's own reports. Assert them in tests.
2. **Reference cases:** pick 5–10 real unit-periods with the partner (sharp drops, values >100%, stable controls). Assert observed values and expected signals.
3. **Synthetic fixtures:** planted anomalies (collapse, >100%, missing, zero base, small numbers), labelled `SYNTHETIC_TEST_FIXTURE`, never shown as data.
4. **Validator drafts:** one compliant and one draft per failure mode (wrong number, place, year, indicator, direction; causal; uptake; injection; uncovered evidence).
5. **Live evaluation (paid, approved):** run `evals/run_live.py` with a spending cap on the reference cases. Report acceptance, review, rejection and refusal rates, citation and grounding accuracy, cost and latency. Have an epidemiologist review a sample of accepted briefs.
6. **Go/no-go:** see `docs/PILOT_PLAN.md` §8.
