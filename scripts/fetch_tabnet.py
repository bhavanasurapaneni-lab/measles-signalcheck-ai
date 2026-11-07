"""Fetch the Milestone 3 proof-of-concept sample from DATASUS TabNet.

Reproduces three public, aggregate TabNet queries for Rio de Janeiro state and saves
TabNet's own CSV export byte-for-byte in data/raw/brazil_sipni/, plus a manifest with
URLs, query selections, retrieval time and SHA-256 hashes.

Usage (from the project root):
    .venv\\Scripts\\python.exe scripts\\fetch_tabnet.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

BASE = "http://tabnet.datasus.gov.br"
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "brazil_sipni"
UA = {"User-Agent": "measles-signalcheck-ai/0.1 (portfolio research; aggregate public data)"}
YEARS_PNI = [str(y) for y in range(2015, 2023)]          # 2015-2022
YEARS_SINASC = [str(y) for y in range(2014, 2022)]       # 2014-2021 (births one year earlier)

QUERIES = [
    {
        "id": "A_coverage_tv_d1",
        "file": "rj_mun_coverage_triplice_viral_d1_2015_2022.csv",
        "description": "Vaccination coverage (%) - Triplice Viral D1 - RJ municipalities x year",
        "form_url": f"{BASE}/cgi/dhdat.exe?bd_pni/cpnibr.def",
        "post_url": f"{BASE}/cgi/webtabx.exe?bd_pni/cpnibr.def",
        "select": {
            "Linha": ["Município"],
            "Coluna": ["Ano"],
            "Incremento": ["Tríplice Viral D1"],
            "PAno": YEARS_PNI,
            "SUnidade da Federação": ["Rio de Janeiro"],
        },
    },
    {
        "id": "B_doses_scr_d1_age1",
        "file": "rj_mun_doses_triplice_viral_scr_d1_age1_2015_2022.csv",
        "description": "Doses applied - Triplice Viral (SCR), 1a dose, age 1 year - RJ municipalities x year",
        "form_url": f"{BASE}/cgi/dhdat.exe?bd_pni/dpnibr.def",
        "post_url": f"{BASE}/cgi/webtabx.exe?bd_pni/dpnibr.def",
        "select": {
            "Linha": ["Município"],
            "Coluna": ["Ano"],
            "Incremento": ["Doses_aplicadas"],
            "PAno": YEARS_PNI,
            "SUnidade da Federação": ["Rio de Janeiro"],
            "SImunobiológicos": ["Tríplice Viral (SCR)"],
            "SDose": ["1ª dose"],
            "SFaixa_Etária": ["1 ano"],
        },
    },
    {
        "id": "C_sinasc_births_residence",
        "file": "rj_mun_sinasc_live_births_residence_2014_2021.csv",
        "description": "SINASC live births by mother's municipality of residence - RJ municipalities x year",
        "form_url": f"{BASE}/cgi/deftohtm.exe?sinasc/cnv/nvrj.def",
        "post_url": f"{BASE}/cgi/tabcgi.exe?sinasc/cnv/nvrj.def",
        "select": {
            "Linha": ["Município"],
            "Coluna": ["Ano do nascimento"],
            "Incremento": ["Nascim p/resid.mãe"],
            "Arquivos": YEARS_SINASC,
        },
        "extra": {"formato": "table", "mostre": "Mostra"},
    },
]


class FormParser(HTMLParser):
    """Collect <select> options (text, value, default-selected) from a TabNet form."""

    def __init__(self) -> None:
        super().__init__()
        self.selects: dict[str, list[dict]] = {}
        self.hidden: list[tuple[str, str]] = []
        self._cur: str | None = None
        self._opt: dict | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "select":
            self._cur = a.get("name")
            self.selects.setdefault(self._cur, [])
        elif tag == "option" and self._cur is not None:
            self._opt = {"value": a.get("value", ""), "selected": "selected" in a, "text": ""}
            self.selects[self._cur].append(self._opt)
        elif tag == "input" and a.get("type", "text") in ("hidden",) and a.get("name"):
            self.hidden.append((a["name"], a.get("value", "")))

    def handle_endtag(self, tag):
        if tag == "select":
            self._cur = None
        if tag in ("option", "select"):
            self._opt = None

    def handle_data(self, data):
        if self._opt is not None:
            self._opt["text"] += data


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def http_get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def build_form(q: dict) -> tuple[list[tuple[str, str]], dict]:
    page = http_get(q["form_url"]).decode("latin-1")
    fp = FormParser()
    fp.feed(page)
    fields: list[tuple[str, str]] = []
    resolved: dict[str, list[str]] = {}
    for name, opts in fp.selects.items():
        if not name or not opts:
            continue
        if name in q["select"]:
            wanted = q["select"][name]
            chosen = [o for o in opts if norm(o["text"]) in wanted]
            missing = set(wanted) - {norm(o["text"]) for o in chosen}
            if missing:
                raise SystemExit(f"[{q['id']}] option(s) not found for {name!r}: {sorted(missing)}")
        else:
            chosen = [o for o in opts if o["selected"]] or [opts[0]]
        for o in chosen:
            fields.append((name, o["value"]))
        if name in q["select"]:
            resolved[name] = [f"{norm(o['text'])} => {o['value']}" for o in chosen]
    fields.extend(fp.hidden)
    for k, v in q.get("extra", {}).items():
        fields.append((k, v))
    return fields, resolved


def fetch(q: dict) -> dict:
    fields, resolved = build_form(q)
    body = urllib.parse.urlencode(fields, encoding="latin-1").encode("ascii")
    req = urllib.request.Request(
        q["post_url"], data=body,
        headers={**UA, "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        html = r.read().decode("latin-1")
    links = re.findall(r"""href\s*=\s*["']?([^"'\s>]+\.csv)""", html, flags=re.I)
    if not links:
        raise SystemExit(f"[{q['id']}] no CSV link in TabNet response; first 500 chars:\n{html[:500]}")
    csv_url = urllib.parse.urljoin(q["post_url"], links[0])
    raw = http_get(csv_url)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / q["file"]
    path.write_bytes(raw)  # saved exactly as served; never modified afterwards
    return {
        "id": q["id"],
        "file": q["file"],
        "description": q["description"],
        "form_url": q["form_url"],
        "query_post_url": q["post_url"],
        "csv_export_url": csv_url,
        "selections": resolved,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def main() -> int:
    entries = [fetch(q) for q in QUERIES]
    manifest = {
        "source": "Ministério da Saúde / DATASUS TabNet (SI-PNI and SINASC), public aggregate tables",
        "state": "Rio de Janeiro (UF 33)",
        "files": entries,
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    for e in entries:
        print(f"{e['file']}: {e['bytes']} bytes sha256={e['sha256'][:16]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
