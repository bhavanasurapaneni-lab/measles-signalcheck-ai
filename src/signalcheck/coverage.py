"""Coverage calculation with explicit guard rails.

Coverage is only calculated when the numerator and denominator are compatible and the
denominator is valid. The result is always labelled a *sensitivity estimate*: it is
not the Ministry's published coverage, which uses an unpublished target population.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .connectors.base import Connector


class CoverageNotComputable(ValueError):
    """Numerator/denominator are missing, invalid, or not definitionally compatible."""


# Pairs that are accepted as compatible: (numerator measure, denominator measure).
# MMR1 is given at 12 months, so the eligible cohort for doses in year Y was born in Y-1.
COMPATIBLE = {("doses_administered", "live_births"): 1}   # value = birth-year lag


@dataclass(frozen=True)
class CoverageEstimate:
    unit_code: str
    year: int
    numerator: float
    denominator: float
    denominator_year: int
    coverage_pct: float
    label: str = "sensitivity estimate (doses ÷ SINASC live births, previous year); not official coverage"


def sensitivity_coverage(obs: pd.DataFrame, connector: Connector, unit_code: str, year: int,
                         numerator: str = "doses_administered",
                         denominator: str = "live_births") -> CoverageEstimate:
    if (numerator, denominator) not in COMPATIBLE:
        raise CoverageNotComputable(f"{numerator} / {denominator} is not a compatible pair")
    lag = COMPATIBLE[(numerator, denominator)]
    den_year = year - lag
    connector.check_comparable(year, den_year)

    def get(measure: str, y: int) -> float:
        row = obs[(obs.unit_code == unit_code) & (obs.year == y) & (obs.measure == measure)]
        if row.empty or pd.isna(row["value"].iloc[0]):
            raise CoverageNotComputable(f"{measure} missing for {unit_code} in {y}")
        return float(row["value"].iloc[0])

    num, den = get(numerator, year), get(denominator, den_year)
    if den <= 0:
        raise CoverageNotComputable(f"denominator {denominator}={den} for {unit_code} in {den_year} is not valid")
    return CoverageEstimate(unit_code, year, num, den, den_year, round(100 * num / den, 2))


def change(obs: pd.DataFrame, connector: Connector, unit_code: str, measure: str,
           year_from: int, year_to: int) -> dict:
    """Observed change in one measure between two comparable years (no interpretation)."""
    connector.check_comparable(year_from, year_to)
    sel = obs[(obs.unit_code == unit_code) & (obs.measure == measure)].set_index("year")["value"]
    a, b = sel.get(year_from), sel.get(year_to)
    if a is None or b is None or pd.isna(a) or pd.isna(b):
        raise CoverageNotComputable(f"{measure} missing for {unit_code} in {year_from} or {year_to}")
    out = {"unit_code": unit_code, "measure": measure, "from": a, "to": b, "absolute_change": b - a}
    out["relative_change_pct"] = round(100 * (b / a - 1), 1) if a else None
    return out
