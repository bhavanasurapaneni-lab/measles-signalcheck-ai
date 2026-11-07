"""Canonical observation schema shared by all data connectors.

Every connector returns a long-format DataFrame with exactly these columns, one row per
(source, unit, year, measure). Doses, denominators and coverage are different
*measures*, never mixed in one column, so downstream code cannot confuse them.
"""
from __future__ import annotations

import pandas as pd

COLUMNS: dict[str, str] = {
    "source_id": "string",        # e.g. "brazil_sipni_tabnet"
    "country_iso3": "string",     # e.g. "BRA"
    "admin1_code": "string",      # e.g. "33" (Rio de Janeiro)
    "unit_code": "string",        # e.g. IBGE 6-digit municipality code
    "unit_name": "string",
    "year": "int64",
    "measure": "string",          # one of MEASURES
    "value": "float64",           # NaN = missing in source; never imputed
    "attribution": "string",      # how the value is assigned to the unit (see ATTRIBUTIONS)
    "system_period": "string",    # reporting-system era the value belongs to
}

# measure -> (unit of measure, kind)
MEASURES: dict[str, tuple[str, str]] = {
    "doses_administered": ("count", "numerator"),
    "live_births": ("count", "denominator"),
    "published_coverage_pct": ("percent", "published_indicator"),
}

ATTRIBUTIONS = {"place_of_recording", "mother_residence", "as_published"}


class SchemaError(ValueError):
    """Raised when a table does not conform to the canonical schema."""


def validate(df: pd.DataFrame) -> pd.DataFrame:
    """Check columns, dtypes, allowed values and key uniqueness. Returns df unchanged."""
    missing = set(COLUMNS) - set(df.columns)
    extra = set(df.columns) - set(COLUMNS)
    if missing or extra:
        raise SchemaError(f"columns mismatch: missing={sorted(missing)} extra={sorted(extra)}")
    bad_measures = set(df["measure"].unique()) - set(MEASURES)
    if bad_measures:
        raise SchemaError(f"unknown measure(s): {sorted(bad_measures)}")
    bad_attr = set(df["attribution"].unique()) - ATTRIBUTIONS
    if bad_attr:
        raise SchemaError(f"unknown attribution(s): {sorted(bad_attr)}")
    for col, dtype in COLUMNS.items():
        if str(df[col].dtype) != dtype:
            raise SchemaError(f"column {col!r} has dtype {df[col].dtype}, expected {dtype}")
    key = ["source_id", "unit_code", "year", "measure"]
    if df.duplicated(key).any():
        raise SchemaError("duplicate (source_id, unit_code, year, measure) rows")
    counts = df[df["measure"].map(lambda m: MEASURES[m][0]) == "count"]["value"].dropna()
    if (counts < 0).any() or (counts % 1 != 0).any():
        raise SchemaError("count measures must be non-negative integers")
    pct = df[df["measure"] == "published_coverage_pct"]["value"].dropna()
    if (pct < 0).any():
        raise SchemaError("coverage percentages must be non-negative")
    return df


def empty() -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype=t) for c, t in COLUMNS.items()})
