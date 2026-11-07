"""Milestone 3 proof-of-concept: reproducibility and validation of the TabNet sample.

These tests read only the raw files in data/raw/brazil_sipni/ (git-ignored) and
skip cleanly if the sample has not been fetched (run scripts/fetch_tabnet.py).
All values asserted here are OBSERVED values from the official exports.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from signalcheck.tabnet import read_tabnet_csv

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "brazil_sipni"
COV = RAW / "rj_mun_coverage_triplice_viral_d1_2015_2022.csv"
DOS = RAW / "rj_mun_doses_triplice_viral_scr_d1_age1_2015_2022.csv"
NV = RAW / "rj_mun_sinasc_live_births_residence_2014_2021.csv"

pytestmark = pytest.mark.skipif(not (RAW / "manifest.json").exists(),
                                reason="sample not fetched; run scripts/fetch_tabnet.py")


@pytest.fixture(scope="module")
def tables():
    return read_tabnet_csv(COV), read_tabnet_csv(DOS), read_tabnet_csv(NV)


# --- Reproducibility -------------------------------------------------------------

def test_manifest_hashes_match_raw_files():
    manifest = json.loads((RAW / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["files"]) == 3
    for entry in manifest["files"]:
        data = (RAW / entry["file"]).read_bytes()
        assert len(data) == entry["bytes"], entry["file"]
        assert hashlib.sha256(data).hexdigest() == entry["sha256"], entry["file"]
        assert entry["csv_export_url"].startswith("http://tabnet.datasus.gov.br/")


def test_raw_data_is_git_ignored():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "data/raw/*" in gitignore


# --- Aggregate-only / no personal data ------------------------------------------

def test_exports_contain_only_aggregate_columns(tables):
    for t in tables:
        assert all(isinstance(c, int) and 2014 <= c <= 2022 for c in t.values.columns)
    header = COV.read_text(encoding="latin-1").splitlines()[0]
    assert re.fullmatch(r'"Munic.pio"(;"\d{4}")+;" ?Total"', header), header


# --- Structure, codes, years, types ---------------------------------------------

def test_municipality_codes_valid_and_consistent(tables):
    cov, dos, nv = tables
    codes = set(cov.values.index)
    assert len(codes) == 92
    assert all(re.fullmatch(r"33\d{4}", c) for c in codes)  # 33 = Rio de Janeiro (IBGE)
    assert codes == set(dos.values.index) == set(nv.values.index)


def test_reporting_years(tables):
    cov, dos, nv = tables
    assert list(cov.values.columns) == list(range(2015, 2023))
    assert list(dos.values.columns) == list(range(2015, 2023))
    assert list(nv.values.columns) == list(range(2014, 2022))


def test_no_missing_or_unparsed_values(tables):
    for t in tables:
        assert t.unparsed_cells == []
        assert not t.values.isna().any().any()


def test_types_and_ranges(tables):
    cov, dos, nv = tables
    assert (dos.values >= 0).all().all() and (dos.values % 1 == 0).all().all()   # counts
    assert (nv.values >= 0).all().all() and (nv.values % 1 == 0).all().all()     # counts
    assert (cov.values >= 0).all().all()                                         # percentages


def test_unassigned_births_are_excluded_not_dropped_silently(tables):
    _, _, nv = tables
    assert list(nv.excluded_rows) == ["MUNICIPIO IGNORADO - RJ"]
    for y in nv.values.columns:
        idx = list(nv.values.columns).index(y)
        assert nv.values[y].sum() + nv.excluded_rows["MUNICIPIO IGNORADO - RJ"][idx] == nv.total_row[y]


# --- Internal consistency and agreement with published indicators --------------

def test_dose_counts_sum_to_tabnet_total(tables):
    _, dos, _ = tables
    for y in dos.values.columns:
        assert dos.values[y].sum() == dos.total_row[y]


def test_state_coverage_matches_previously_published_values(tables):
    cov, _, _ = tables
    # Values read from TabNet's health-region query on 7 Nov 2026 (DATA_SOURCES.md §10.3)
    assert cov.total_row[2019] == pytest.approx(96.58, abs=0.005)
    assert cov.total_row[2020] == pytest.approx(61.61, abs=0.005)
    assert cov.total_row[2021] == pytest.approx(59.48, abs=0.005)


# --- The one municipality comparison (observed values only) ---------------------

def test_sao_goncalo_2019_2020_observed_values(tables):
    cov, dos, nv = tables
    sg = "330490"
    assert cov.names[sg] == "SAO GONCALO"
    assert dos.values.loc[sg, 2019] == 13396 and dos.values.loc[sg, 2020] == 4096
    assert cov.values.loc[sg, 2019] == pytest.approx(121.66) and cov.values.loc[sg, 2020] == pytest.approx(35.77)
    # Independent denominator (SINASC births, previous year): changes far less than doses
    births_change = nv.values.loc[sg, 2019] / nv.values.loc[sg, 2018] - 1
    doses_change = dos.values.loc[sg, 2020] / dos.values.loc[sg, 2019] - 1
    assert abs(births_change) < 0.10
    assert doses_change < -0.60
