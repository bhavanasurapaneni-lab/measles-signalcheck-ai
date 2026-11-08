"""Deterministic signal rules (Milestone 4).

Signals are REVIEW TRIGGERS over observed aggregate values. They never state causes.

Methodological rules enforced here:
* Recorded doses and published coverage are analysed separately.
* The official denominator is unpublished. Any denominator derived from published
  values (doses / coverage) is labelled ``back_calculated_not_observed``.
* SINASC births are an INDEPENDENT REFERENCE series (by mother's residence; the official
  denominator uses an older extract and doses are attributed by place of recording),
  so they are reported as context only and are NOT used to classify a change as
  numerator- or denominator-driven.
* The coverage decomposition is a mathematical identity of published values and is
  labelled as such; it cannot establish cause.
* Missing values stay missing (null) and lead to ``insufficient_evidence``; they are
  never replaced with zero.
"""
from __future__ import annotations

import hashlib
import math
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

RULES_VERSION = "1.0"
DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "signal_thresholds.toml"

CLASSIFICATIONS = (
    "recorded_dose_change",
    "reported_coverage_change",
    "implausible_coverage",
    "state_benchmark_divergence",
    "small_denominator_caution",
    "insufficient_evidence",
)

CANNOT_CONCLUDE = {
    "recorded_dose_change": [
        "Whether the number of children actually vaccinated changed.",
        "Whether the change reflects vaccination activity, recording, or transmission of records.",
        "Any cause of the change.",
    ],
    "reported_coverage_change": [
        "Whether true coverage changed: the official denominator is unpublished.",
        "Whether the change is driven by the numerator or the denominator in reality; the decomposition is arithmetic only.",
        "Any cause of the change.",
    ],
    "implausible_coverage": [
        "Which input is inaccurate: numerator and denominator are attributed differently (place of recording vs residence).",
        "The true coverage level.",
    ],
    "state_benchmark_divergence": [
        "Why this municipality differs from the state.",
        "Whether the difference reflects vaccination activity or recording.",
    ],
    "small_denominator_caution": [
        "Whether percentage changes are meaningful: small counts make percentages volatile.",
    ],
    "insufficient_evidence": [
        "Anything about this comparison: required inputs are missing, zero, or invalid.",
    ],
}


class UnsupportedComparison(ValueError):
    """The requested comparison is not like-for-like (e.g. non-consecutive years)."""


@dataclass(frozen=True)
class Thresholds:
    version: str
    sha256: str
    consecutive_years_only: bool
    dose_change_pct: float
    coverage_change_pp: float
    implausible_upper_pct: float
    state_divergence_pp: float
    min_reference_births: int
    min_base_doses: int


def load_thresholds(path: str | Path = DEFAULT_CONFIG) -> Thresholds:
    raw = Path(path).read_bytes()
    c = tomllib.loads(raw.decode("utf-8"))
    # Hash content with normalised line endings so Windows (CRLF) and Unix (LF) checkouts agree.
    normalised = raw.replace(b"\r\n", b"\n")
    return Thresholds(
        version=str(c["version"]),
        sha256=hashlib.sha256(normalised).hexdigest(),
        consecutive_years_only=bool(c["comparison"]["consecutive_years_only"]),
        dose_change_pct=float(c["recorded_dose_change"]["min_abs_relative_change_pct"]),
        coverage_change_pp=float(c["reported_coverage_change"]["min_abs_change_pp"]),
        implausible_upper_pct=float(c["implausible_coverage"]["upper_pct"]),
        state_divergence_pp=float(c["state_benchmark"]["min_abs_divergence_pp"]),
        min_reference_births=int(c["small_denominator"]["min_reference_births"]),
        min_base_doses=int(c["small_denominator"]["min_base_doses"]),
    )


# ------------------------------------------------------------------------------ ledger
@dataclass
class Ledger:
    """Accumulates facts (F#), derived values (D#) and signals (S#) with stable IDs."""
    facts: list[dict] = field(default_factory=list)
    derived: list[dict] = field(default_factory=list)
    signals: list[dict] = field(default_factory=list)

    def fact(self, measure, unit_code, year, value, unit, attribution, source_file, role="observed") -> str:
        fid = f"F{len(self.facts) + 1}"
        self.facts.append({
            "id": fid, "measure": measure, "unit_code": unit_code, "year": int(year),
            "value": None if value is None else float(value), "unit": unit,
            "attribution": attribution, "source_file": source_file, "role": role,
        })
        return fid

    def derive(self, name, method, inputs, value, unit, label) -> str:
        did = f"D{len(self.derived) + 1}"
        self.derived.append({
            "id": did, "name": name, "method": method, "inputs": list(inputs),
            "value": None if value is None else round(float(value), 4), "unit": unit, "label": label,
        })
        return did

    def signal(self, classification, rule_id, threshold, statement, evidence, cautions=()) -> str:
        assert classification in CLASSIFICATIONS, classification
        sid = f"S{len(self.signals) + 1}"
        self.signals.append({
            "id": sid, "classification": classification, "rule_id": rule_id,
            "threshold": threshold, "statement": statement, "evidence": list(evidence),
            "cautions": list(cautions), "cannot_conclude": list(CANNOT_CONCLUDE[classification]),
        })
        return sid

    def value(self, ref: str):
        for item in self.facts + self.derived:
            if item["id"] == ref:
                return item["value"]
        raise KeyError(ref)


# ----------------------------------------------------------------------------- helpers
def _get(obs: pd.DataFrame, unit_code: str, measure: str, year: int):
    """Return the observed value or None. Never substitutes zero for missing."""
    row = obs[(obs.unit_code == unit_code) & (obs.measure == measure) & (obs.year == year)]
    if row.empty or pd.isna(row["value"].iloc[0]):
        return None
    return float(row["value"].iloc[0])


def _valid_count(v) -> bool:
    return v is not None and v >= 0 and float(v).is_integer()


def _valid_pct(v) -> bool:
    return v is not None and math.isfinite(v) and v >= 0


def state_dose_totals(obs: pd.DataFrame, y1: int, y2: int) -> tuple[float, float, int]:
    """Weighted state benchmark: ratio of SUMMED doses over units observed in BOTH years."""
    d = obs[obs.measure == "doses_administered"].pivot(index="unit_code", columns="year", values="value")
    both = d[[y1, y2]].dropna()
    return float(both[y1].sum()), float(both[y2].sum()), len(both)


def state_reported_coverage(obs: pd.DataFrame, year: int) -> float | None:
    """Weighted state coverage = sum(doses) / sum(back-calculated denominators) x 100.

    This reproduces TabNet's own state total (it is the same ratio-of-sums). It is NOT
    the unweighted mean of municipal percentages.
    """
    d = obs[(obs.measure == "doses_administered") & (obs.year == year)].set_index("unit_code")["value"]
    c = obs[(obs.measure == "published_coverage_pct") & (obs.year == year)].set_index("unit_code")["value"]
    df = pd.concat({"d": d, "c": c}, axis=1).dropna()
    df = df[(df.c > 0)]
    if df.empty:
        return None
    return float(df.d.sum() / (df.d / df.c * 100).sum() * 100)


# ------------------------------------------------------------------------------ rules
def evaluate(obs: pd.DataFrame, unit_code: str, y1: int, y2: int, t: Thresholds,
             files: dict[str, str]) -> Ledger:
    """Evaluate every rule for one unit and one comparable year pair."""
    if y2 <= y1:
        raise UnsupportedComparison("year_to must be later than year_from")
    if t.consecutive_years_only and y2 - y1 != 1:
        raise UnsupportedComparison(f"only consecutive years are compared ({y1}->{y2} requested)")

    L = Ledger()
    f_dose, f_cov, f_nv = files["doses_administered"], files["published_coverage_pct"], files["live_births"]

    d1, d2 = _get(obs, unit_code, "doses_administered", y1), _get(obs, unit_code, "doses_administered", y2)
    c1, c2 = _get(obs, unit_code, "published_coverage_pct", y1), _get(obs, unit_code, "published_coverage_pct", y2)
    b1, b2 = _get(obs, unit_code, "live_births", y1 - 1), _get(obs, unit_code, "live_births", y2 - 1)

    F_d1 = L.fact("doses_administered", unit_code, y1, d1, "count", "place_of_recording", f_dose)
    F_d2 = L.fact("doses_administered", unit_code, y2, d2, "count", "place_of_recording", f_dose)
    F_c1 = L.fact("published_coverage_pct", unit_code, y1, c1, "percent", "as_published", f_cov)
    F_c2 = L.fact("published_coverage_pct", unit_code, y2, c2, "percent", "as_published", f_cov)
    F_b1 = L.fact("live_births", unit_code, y1 - 1, b1, "count", "mother_residence", f_nv, "independent_reference")
    F_b2 = L.fact("live_births", unit_code, y2 - 1, b2, "count", "mother_residence", f_nv, "independent_reference")

    # -- small-denominator caution (computed first so other signals can cite it) -------
    small_reasons, small_refs = [], []
    for ref, b, yr in ((F_b1, b1, y1 - 1), (F_b2, b2, y2 - 1)):
        if b is not None and b < t.min_reference_births:
            small_reasons.append(f"reference births in {yr} were {b:.0f} (below {t.min_reference_births})")
            small_refs.append(ref)
    if d1 is not None and d1 < t.min_base_doses:
        small_reasons.append(f"base-year recorded doses were {d1:.0f} (below {t.min_base_doses})")
        small_refs.append(F_d1)
    small_caution = "Small numbers: percentage changes for this unit are volatile." if small_reasons else None

    def cautions(*extra):
        return [c for c in (small_caution, *extra) if c]

    # -- independent reference births (context only; never used to classify) ---------
    D_bchg = None
    if _valid_count(b1) and _valid_count(b2) and b1 > 0:
        D_bchg = L.derive("reference_births_relative_change_pct",
                          "(births[y2-1] / births[y1-1] - 1) x 100; SINASC by mother's residence",
                          [F_b1, F_b2], (b2 / b1 - 1) * 100, "percent", "independent_reference_change")
    ref_note = None
    if D_bchg is not None:
        ref_note = (f"Context: the independent SINASC reference series ({D_bchg}) changed by "
                    f"{L.value(D_bchg):.1f}%. It is residence-based and is not the official denominator, "
                    "so it cannot classify this change as numerator- or denominator-driven.")

    # -- recorded dose change --------------------------------------------------------
    if not (_valid_count(d1) and _valid_count(d2)):
        L.signal("insufficient_evidence", "R1_recorded_dose_change", None,
                 f"Recorded doses for {y1} or {y2} are missing or invalid; no change is computed.",
                 [F_d1, F_d2])
    elif d1 == 0:
        L.signal("insufficient_evidence", "R1_recorded_dose_change", None,
                 f"Recorded doses in {y1} were 0; a relative change is undefined.", [F_d1, F_d2])
    else:
        rel = (d2 / d1 - 1) * 100
        D_rel = L.derive("doses_relative_change_pct", "(doses[y2] / doses[y1] - 1) x 100",
                         [F_d1, F_d2], rel, "percent", "observed_change")
        if abs(rel) >= t.dose_change_pct:
            L.signal("recorded_dose_change", "R1_recorded_dose_change",
                     {"min_abs_relative_change_pct": t.dose_change_pct},
                     f"Recorded MMR1 doses changed by {L.value(D_rel):.1f}% from {y1} ({d1:.0f}) to {y2} ({d2:.0f}).",
                     [F_d1, F_d2, D_rel], cautions(ref_note))

        # -- state benchmark (weighted: ratio of summed doses) -----------------------
        s1, s2, n_units = state_dose_totals(obs, y1, y2)
        if s1 > 0:
            D_s = L.derive("state_doses_relative_change_pct",
                           f"(sum doses[y2] / sum doses[y1] - 1) x 100 over {n_units} units observed in both years "
                           "(weighted by doses; not an average of municipal percentages)",
                           [], (s2 / s1 - 1) * 100, "percent", "state_benchmark_weighted")
            D_div = L.derive("divergence_from_state_pp", "unit relative dose change - state relative dose change",
                             [D_rel, D_s], rel - (s2 / s1 - 1) * 100, "percentage_points", "observed_change")
            if abs(L.value(D_div)) >= t.state_divergence_pp:
                L.signal("state_benchmark_divergence", "R4_state_benchmark",
                         {"min_abs_divergence_pp": t.state_divergence_pp},
                         f"The change in recorded doses ({L.value(D_rel):.1f}%) differs from the statewide change "
                         f"({L.value(D_s):.1f}%) by {L.value(D_div):.1f} percentage points.",
                         [D_rel, D_s, D_div], cautions())

    # -- implausible coverage values ---------------------------------------------------
    for ref, c, yr in ((F_c1, c1, y1), (F_c2, c2, y2)):
        if c is not None and not _valid_pct(c):
            L.signal("insufficient_evidence", "R3_implausible_coverage", None,
                     f"Published coverage for {yr} is invalid; it is not interpreted.", [ref])
        elif c is not None and c > t.implausible_upper_pct:
            L.signal("implausible_coverage", "R3_implausible_coverage",
                     {"upper_pct": t.implausible_upper_pct},
                     f"Published coverage in {yr} was {c:.2f}%, above {t.implausible_upper_pct:.0f}%.",
                     [ref], cautions("Values above 100% can arise when the numerator and denominator are "
                                     "attributed to different places; the value is neither corrected nor interpreted."))

    # -- reported coverage change + mathematical decomposition -------------------------
    if not (_valid_pct(c1) and _valid_pct(c2)):
        L.signal("insufficient_evidence", "R2_reported_coverage_change", None,
                 f"Published coverage for {y1} or {y2} is missing or invalid; no change is computed.",
                 [F_c1, F_c2])
    else:
        D_pp = L.derive("published_coverage_change_pp", "coverage[y2] - coverage[y1]",
                        [F_c1, F_c2], c2 - c1, "percentage_points", "observed_change")
        decomposition_note = None
        if _valid_count(d1) and _valid_count(d2) and min(d1, d2, c1, c2) > 0:
            D_den1 = L.derive("back_calculated_denominator_y1", "doses[y1] / coverage[y1] x 100 (from published, rounded values)",
                              [F_d1, F_c1], d1 / c1 * 100, "count", "back_calculated_not_observed")
            D_den2 = L.derive("back_calculated_denominator_y2", "doses[y2] / coverage[y2] x 100 (from published, rounded values)",
                              [F_d2, F_c2], d2 / c2 * 100, "count", "back_calculated_not_observed")
            total = math.log(c2 / c1)
            if abs(total) >= 0.01:
                share = math.log(d2 / d1) / total
                D_share = L.derive(
                    "share_of_log_coverage_change_from_recorded_doses",
                    "ln(doses[y2]/doses[y1]) / ln(coverage[y2]/coverage[y1]); identity: "
                    "ln(C2/C1) = ln(N2/N1) - ln(Den2/Den1) with back-calculated denominators",
                    [F_d1, F_d2, F_c1, F_c2, D_den1, D_den2], share, "share", "mathematical_decomposition")
                decomposition_note = (
                    f"Mathematical decomposition ({D_share}): the log change in recorded doses equals "
                    f"{L.value(D_share):.2f} times the log change in published coverage; the back-calculated "
                    "denominator accounts for the remainder, which can be negative. This is an identity of "
                    "published values and cannot establish cause.")
                if min(c1, c2) < 1.0:
                    decomposition_note += " Coverage below one percent makes the back-calculated denominator unstable."
        else:
            L.signal("insufficient_evidence", "R2_decomposition", None,
                     f"A decomposition for {y1} to {y2} is not computed: zero or missing inputs.",
                     [F_d1, F_d2, F_c1, F_c2])
        if abs(c2 - c1) >= t.coverage_change_pp:
            L.signal("reported_coverage_change", "R2_reported_coverage_change",
                     {"min_abs_change_pp": t.coverage_change_pp},
                     f"Published coverage changed by {L.value(D_pp):.2f} percentage points, from {c1:.2f}% in {y1} "
                     f"to {c2:.2f}% in {y2}.",
                     [F_c1, F_c2, D_pp], cautions(decomposition_note))

    if small_reasons:
        L.signal("small_denominator_caution", "R5_small_denominator",
                 {"min_reference_births": t.min_reference_births, "min_base_doses": t.min_base_doses},
                 "Small numbers: " + "; ".join(small_reasons) + ".", small_refs)
    return L
