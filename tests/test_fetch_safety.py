"""Safety of the public-data download scripts (offline: no network is used)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fetch_health_regions as fhr  # noqa: E402
import fetch_tabnet as ft  # noqa: E402


@pytest.mark.parametrize("url", [
    "http://tabnet.datasus.gov.br/cgi/csv/x.csv",
    "https://TABNET.DATASUS.GOV.BR/cgi/dhdat.exe?bd_pni/cpnibr.def",
])
def test_trusted_host_accepted(url):
    assert ft.require_trusted(url) == url


@pytest.mark.parametrize("url", [
    "http://evil.example.com/x.csv",
    "http://tabnet.datasus.gov.br.evil.example.com/x.csv",
    "http://datasus.gov.br/x.csv",
    "file:///etc/passwd",
])
def test_untrusted_host_refused(url):
    with pytest.raises(SystemExit, match="untrusted host"):
        ft.require_trusted(url)


def test_content_check_rejects_error_pages():
    assert ft.looks_like_tabnet_table(b'"Munic\xedpio";"2019"\n"330490 SAO GONCALO";"1"\n"Total";"1"\n')
    assert not ft.looks_like_tabnet_table(b"<html><body>Erro no acesso</body></html>")
    assert not ft.looks_like_tabnet_table(b"")


def test_existing_snapshots_are_not_overwritten(tmp_path, monkeypatch):
    for module, attr in ((ft, "OUT_DIR"), (fhr, "OUT")):
        monkeypatch.setattr(module, attr, tmp_path)
        (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
        monkeypatch.setattr(ft, "http_get", lambda url: pytest.fail("must not download"))
        assert module.main([]) == 0
        assert (tmp_path / "manifest.json").read_text(encoding="utf-8") == "{}"
