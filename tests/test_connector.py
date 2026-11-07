"""Connector, schema, coverage guard-rail and failure-condition tests.

Tests marked `needs_raw` use the real (git-ignored) TabNet sample, or copies of it in a
temporary folder that are then deliberately altered. Tests that build tiny TabNet-format
files by hand are clearly marked as TEST FIXTURES - they are not observations.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from signalcheck import schema
from signalcheck.connectors import BrazilSIPNIConnector, ComparabilityError, ManifestError
from signalcheck.connectors.brazil_sipni import FILES
from signalcheck.coverage import CoverageNotComputable, change, sensitivity_coverage
from signalcheck.tabnet import read_tabnet_csv

RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "brazil_sipni"
needs_raw = pytest.mark.skipif(not (RAW / "manifest.json").exists(),
                               reason="sample not fetched; run scripts/fetch_tabnet.py")
SG = "330490"  # São Gonçalo


@pytest.fixture(scope="module")
def loaded():
    c = BrazilSIPNIConnector(RAW)
    return c, c.load()


@pytest.fixture
def raw_copy(tmp_path):
    """Writable copy of the raw sample so failure tests never touch the originals."""
    for f in RAW.iterdir():
        shutil.copy2(f, tmp_path / f.name)
    return tmp_path


def _rehash(folder: Path, name: str) -> None:
    """Update the copied manifest after a deliberate edit (to test parsing, not provenance)."""
    m = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    for e in m["files"]:
        if e["file"] == name:
            e["sha256"] = hashlib.sha256((folder / name).read_bytes()).hexdigest()
    (folder / "manifest.json").write_text(json.dumps(m), encoding="utf-8")


# ---------------------------------------------------------------- connector works
@needs_raw
def test_connector_returns_valid_canonical_table(loaded):
    _, res = loaded
    obs = res.observations
    schema.validate(obs)
    assert list(obs.columns) == list(schema.COLUMNS)
    assert obs["unit_code"].nunique() == 92
    counts = obs.groupby("measure").size().to_dict()
    assert counts == {"doses_administered": 92 * 8, "live_births": 92 * 8, "published_coverage_pct": 92 * 8}


@needs_raw
def test_measures_are_kept_separate(loaded):
    _, res = loaded
    obs = res.observations
    assert set(obs[obs.measure == "doses_administered"].attribution) == {"place_of_recording"}
    assert set(obs[obs.measure == "live_births"].attribution) == {"mother_residence"}
    assert set(obs[obs.measure == "published_coverage_pct"].attribution) == {"as_published"}
    assert set(obs[obs.measure == "doses_administered"].year) == set(range(2015, 2023))
    assert set(obs[obs.measure == "live_births"].year) == set(range(2014, 2022))


@needs_raw
def test_quality_report_lists_exclusions_and_no_missing(loaded):
    _, res = loaded
    assert any("MUNICIPIO IGNORADO" in k for k in res.quality.excluded_rows)
    assert res.quality.missing_values == []
    assert len(res.quality.notes) >= 3


@needs_raw
def test_load_does_not_modify_raw_files():
    before = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in RAW.iterdir()}
    BrazilSIPNIConnector(RAW).load()
    after = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in RAW.iterdir()}
    assert before == after


# ------------------------------------------------ verified example (observed only)
@needs_raw
def test_sao_goncalo_2019_2020_reproducible(loaded):
    c, res = loaded
    obs = res.observations
    doses = change(obs, c, SG, "doses_administered", 2019, 2020)
    assert (doses["from"], doses["to"], doses["relative_change_pct"]) == (13396, 4096, -69.4)
    cov = change(obs, c, SG, "published_coverage_pct", 2019, 2020)
    assert (cov["from"], cov["to"]) == (pytest.approx(121.66), pytest.approx(35.77))
    births = change(obs, c, SG, "live_births", 2018, 2019)
    assert births["relative_change_pct"] == -4.9
    est19 = sensitivity_coverage(obs, c, SG, 2019)
    est20 = sensitivity_coverage(obs, c, SG, 2020)
    assert (est19.coverage_pct, est19.denominator_year) == (122.13, 2018)
    assert (est20.coverage_pct, est20.denominator_year) == (39.26, 2019)
    assert "not official" in est20.label


# ------------------------------------------------------- coverage guard rails
@needs_raw
def test_coverage_refused_for_unknown_unit_or_outside_window(loaded):
    c, res = loaded
    with pytest.raises(CoverageNotComputable, match="missing"):
        sensitivity_coverage(res.observations, c, "330000", 2020)   # no such municipality
    with pytest.raises(ComparabilityError):
        sensitivity_coverage(res.observations, c, SG, 2023)         # crosses the 2023 break


@needs_raw
def test_coverage_refused_for_incompatible_pair(loaded):
    c, res = loaded
    with pytest.raises(CoverageNotComputable):
        sensitivity_coverage(res.observations, c, SG, 2020, numerator="published_coverage_pct")


@needs_raw
def test_coverage_refused_when_denominator_missing_or_zero(loaded):
    c, res = loaded
    obs = res.observations.copy()
    mask = (obs.unit_code == SG) & (obs.measure == "live_births") & (obs.year == 2019)
    obs.loc[mask, "value"] = 0.0
    with pytest.raises(CoverageNotComputable, match="not valid"):
        sensitivity_coverage(obs, c, SG, 2020)
    obs.loc[mask, "value"] = float("nan")
    with pytest.raises(CoverageNotComputable, match="missing"):
        sensitivity_coverage(obs, c, SG, 2020)


def test_comparison_across_2023_break_is_refused():
    c = BrazilSIPNIConnector(RAW)
    c.check_comparable(2019, 2020)          # fine
    with pytest.raises(ComparabilityError, match="2023"):
        c.check_comparable(2022, 2023)
    with pytest.raises(ComparabilityError):
        c.check_comparable(2024, 2019)


# ------------------------------------------------------------ failure conditions
@needs_raw
def test_fails_when_raw_file_altered(raw_copy):
    p = raw_copy / FILES[1].file
    p.write_bytes(p.read_bytes().replace(b'"13396"', b'"13397"'))
    with pytest.raises(ManifestError, match="altered"):
        BrazilSIPNIConnector(raw_copy).load()


@needs_raw
def test_fails_when_raw_file_missing(raw_copy):
    (raw_copy / FILES[0].file).unlink()
    with pytest.raises(ManifestError, match="missing"):
        BrazilSIPNIConnector(raw_copy).load()


@needs_raw
def test_fails_when_manifest_missing(raw_copy):
    (raw_copy / "manifest.json").unlink()
    with pytest.raises(ManifestError, match="manifest not found"):
        BrazilSIPNIConnector(raw_copy).load()


@needs_raw
def test_fails_on_invalid_municipality_code(raw_copy):
    name = FILES[1].file
    p = raw_copy / name
    p.write_bytes(p.read_bytes().replace(b'"330490 SAO GONCALO"', b'"350490 SAO GONCALO"'))
    _rehash(raw_copy, name)
    with pytest.raises(schema.SchemaError, match="invalid municipality codes"):
        BrazilSIPNIConnector(raw_copy).load()


@needs_raw
def test_fails_on_unexpected_reporting_years(raw_copy):
    name = FILES[0].file
    p = raw_copy / name
    p.write_bytes(p.read_bytes().replace(b'"2015";', b'"2014";', 1))
    _rehash(raw_copy, name)
    with pytest.raises(schema.SchemaError, match="years"):
        BrazilSIPNIConnector(raw_copy).load()


@needs_raw
def test_missing_cell_is_reported_not_imputed(raw_copy):
    name = FILES[1].file
    p = raw_copy / name
    p.write_bytes(p.read_bytes().replace(b'"13396"', b'"-"'))
    _rehash(raw_copy, name)
    res = BrazilSIPNIConnector(raw_copy).load()
    assert ("330490 SAO GONCALO", 2019, "doses_administered") in res.quality.missing_values
    v = res.observations.query("unit_code == @SG and year == 2019 and measure == 'doses_administered'")["value"]
    assert v.isna().all()


def test_parser_rejects_non_tabnet_file(tmp_path):
    p = tmp_path / "not_tabnet.csv"            # TEST FIXTURE, not data
    p.write_text("a;b\n1;2\n", encoding="latin-1")
    with pytest.raises(StopIteration):
        read_tabnet_csv(p)


def test_schema_rejects_mixed_or_unknown_measures():
    df = schema.empty()
    df.loc[0] = ["s", "BRA", "33", "330000", "X", 2020, "coverage_guess", 1.0, "as_published", "p"]
    df = df.astype(schema.COLUMNS)
    with pytest.raises(schema.SchemaError, match="unknown measure"):
        schema.validate(df)


def test_schema_rejects_negative_or_fractional_counts():
    df = schema.empty()
    df.loc[0] = ["s", "BRA", "33", "330000", "X", 2020, "doses_administered", 1.5, "place_of_recording", "p"]
    df = df.astype(schema.COLUMNS)
    with pytest.raises(schema.SchemaError, match="non-negative integers"):
        schema.validate(df)
