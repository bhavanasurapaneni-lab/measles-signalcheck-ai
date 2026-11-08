"""Extract the official municipality -> health region (Região de Saúde, CIR) mapping.

The mapping is read from DATASUS TabNet's own immunization query form (the same page
`fetch_tabnet.py` uses): each CIR option value is "<CIR code> <name>|<IBGE municipality>|6".
No health values are involved. Saves the raw form page unchanged, a mapping CSV derived
from it, and a manifest with hashes, in data/raw/brazil_reference/ (git-ignored).

Usage (project root):
    .venv\\Scripts\\python.exe scripts\\fetch_health_regions.py
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_tabnet as ft  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "brazil_reference"
FORM_URL = f"{ft.BASE}/cgi/dhdat.exe?bd_pni/cpnibr.def"


def main() -> int:
    raw = ft.http_get(FORM_URL)
    fp = ft.FormParser()
    fp.feed(raw.decode("latin-1"))
    rows = []
    for o in fp.selects["SRegião de Saúde (CIR)"]:
        parts = o["value"].split("|")
        if len(parts) >= 2 and len(parts[1]) == 6 and parts[1].isdigit() and parts[1].startswith("33"):
            cir_code, _, cir_name = ft.norm(parts[0]).partition(" ")
            rows.append({"ibge_code": parts[1], "cir_code": cir_code, "cir_name": cir_name})
    rows = sorted({r["ibge_code"]: r for r in rows}.values(), key=lambda r: r["ibge_code"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "tabnet_cpnibr_form.html").write_bytes(raw)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["ibge_code", "cir_code", "cir_name"], lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    mapping = buf.getvalue().encode("utf-8")
    (OUT / "rj_health_regions.csv").write_bytes(mapping)
    manifest = {
        "source": "Ministério da Saúde / DATASUS TabNet immunization coverage query form (CIR selector)",
        "form_url": FORM_URL,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": [
            {"file": "tabnet_cpnibr_form.html", "role": "raw source page (unchanged)",
             "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()},
            {"file": "rj_health_regions.csv", "role": "derived: option values split into code/name",
             "bytes": len(mapping), "sha256": hashlib.sha256(mapping).hexdigest()},
        ],
        "municipalities": len(rows),
        "health_regions": len({r["cir_code"] for r in rows}),
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{manifest['municipalities']} municipalities in {manifest['health_regions']} health regions; "
          f"form page {len(raw)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
