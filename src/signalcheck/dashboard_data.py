"""Data access for the Streamlit dashboard (pure functions, unit-tested).

Everything here is computed from the verified connector output and the deterministic
signal rules. No values are invented; aggregates are ratios of sums (weighted).
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .connectors import BrazilSIPNIConnector
from .evidence import build_packet

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "brazil_sipni"
REF = ROOT / "data" / "raw" / "brazil_reference"


def raw_dir() -> Path:
    """Overridable (SIGNALCHECK_RAW_DIR) so tests can simulate missing or unavailable files."""
    return Path(os.getenv("SIGNALCHECK_RAW_DIR", RAW))


def ref_dir() -> Path:
    return Path(os.getenv("SIGNALCHECK_REF_DIR", REF))
YEARS = list(range(2015, 2023))
PERIODS = [(y, y + 1) for y in range(2015, 2022)]
# TabNet's own published state totals (read 7 Nov 2026; DATA_SOURCES.md §10.3, §11.3)
TABNET_STATE_COVERAGE = {2019: 96.58, 2020: 61.61, 2021: 59.48}


@dataclass
class Bundle:
    connector: BrazilSIPNIConnector
    obs: pd.DataFrame
    units: pd.DataFrame          # unit_code, unit_name, cir_code, cir_name
    regions_available: bool
    retrieved_at: str


def load_regions() -> pd.DataFrame | None:
    """Municipality -> health region mapping, verified against its manifest hash."""
    ref = ref_dir()
    m, f = ref / "manifest.json", ref / "rj_health_regions.csv"
    if not (m.exists() and f.exists()):
        return None
    manifest = json.loads(m.read_text(encoding="utf-8"))
    entry = next(e for e in manifest["files"] if e["file"] == "rj_health_regions.csv")
    if hashlib.sha256(f.read_bytes()).hexdigest() != entry["sha256"]:
        raise ValueError("health-region mapping does not match its manifest hash")
    with f.open(encoding="utf-8") as fh:
        return pd.DataFrame(list(csv.DictReader(fh)))


def load_bundle(raw: Path | None = None) -> Bundle:
    raw = Path(raw) if raw else raw_dir()
    c = BrazilSIPNIConnector(raw)
    obs = c.load().observations
    units = obs.drop_duplicates("unit_code")[["unit_code", "unit_name"]].astype(str)
    regions = load_regions()
    if regions is not None:
        units = units.merge(regions.rename(columns={"ibge_code": "unit_code"}), on="unit_code", how="left")
        ok = units["cir_code"].notna().all()
    else:
        ok = False
    if not ok:
        units["cir_code"], units["cir_name"] = "", "Health regions unavailable"
    manifest = json.loads((raw / "manifest.json").read_text(encoding="utf-8"))
    retrieved = min(e["retrieved_at_utc"] for e in manifest["files"])[:10]
    return Bundle(c, obs, units.sort_values("unit_name").reset_index(drop=True), ok, retrieved)


def _wide(obs: pd.DataFrame, measure: str) -> pd.DataFrame:
    return obs[obs.measure == measure].pivot(index="unit_code", columns="year", values="value")


def area_series(b: Bundle, unit_codes: list[str]) -> pd.DataFrame:
    """Recorded doses (sum) and weighted published coverage for a set of units, by year.

    Weighted coverage = sum(doses) / sum(doses / coverage) x 100 (ratio of sums over units
    with both values) - never an unweighted mean of municipal percentages.
    """
    d = _wide(b.obs, "doses_administered").loc[unit_codes]
    c = _wide(b.obs, "published_coverage_pct").loc[unit_codes]
    rows = []
    for y in YEARS:
        both = pd.concat({"d": d[y], "c": c[y]}, axis=1).dropna()
        both = both[both.c > 0]
        cov = float(both.d.sum() / (both.d / both.c * 100).sum() * 100) if len(both) else None
        rows.append({"year": y, "doses": float(d[y].sum(min_count=1)), "coverage_weighted": cov,
                     "units": int(d[y].notna().sum())})
    return pd.DataFrame(rows)


def unit_series(b: Bundle, code: str) -> pd.DataFrame:
    def col(measure, years):
        w = _wide(b.obs, measure)
        return [w.loc[code, y] if y in w.columns else None for y in years]
    return pd.DataFrame({
        "year": YEARS,
        "doses": col("doses_administered", YEARS),
        "coverage": col("published_coverage_pct", YEARS),
        "births_previous_year": col("live_births", [y - 1 for y in YEARS]),
    })


def indexed(series: pd.Series, base_year: int = 2015) -> pd.Series:
    base = series.loc[base_year] if base_year in series.index else None
    return series / base * 100 if base else series * float("nan")


def region_changes(b: Bundle, y1: int, y2: int) -> pd.DataFrame:
    if not b.regions_available:
        return pd.DataFrame(columns=["cir_name", "doses_from", "doses_to", "change_pct"])
    out = []
    for (code, name), g in b.units.groupby(["cir_code", "cir_name"]):
        s = area_series(b, list(g.unit_code)).set_index("year")
        a, z = s.loc[y1, "doses"], s.loc[y2, "doses"]
        out.append({"cir_code": code, "cir_name": name, "municipalities": len(g), "doses_from": a,
                    "doses_to": z, "change_pct": (z / a - 1) * 100 if a else None})
    return pd.DataFrame(out).sort_values("change_pct")


def packet(b: Bundle, code: str, y1: int) -> dict:
    return build_packet(b.obs, b.connector, code, y1, y1 + 1)


def signal_table(b: Bundle, y1: int) -> pd.DataFrame:
    rows = []
    for _, u in b.units.iterrows():
        p = packet(b, u.unit_code, y1)
        d = {x["name"]: x["value"] for x in p["derived"]}
        cls = [s["classification"] for s in p["signals"]]
        cov_to = next((f["value"] for f in p["facts"]
                       if f["measure"] == "published_coverage_pct" and f["year"] == y1 + 1), None)
        rows.append({
            "unit_code": u.unit_code, "municipality": u.unit_name.title(), "health_region": u.cir_name,
            "dose_change_pct": d.get("doses_relative_change_pct"),
            "coverage_change_pp": d.get("published_coverage_change_pp"),
            "coverage_to": cov_to,
            "recorded_dose_change": "recorded_dose_change" in cls,
            "reported_coverage_change": "reported_coverage_change" in cls,
            "implausible_coverage": "implausible_coverage" in cls,
            "state_benchmark_divergence": "state_benchmark_divergence" in cls,
            "small_denominator_caution": "small_denominator_caution" in cls,
            "insufficient_evidence": "insufficient_evidence" in cls,
            "n_signals": len(cls),
        })
    return pd.DataFrame(rows)
