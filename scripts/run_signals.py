"""Scan all units and consecutive year pairs; write a signal summary and an example packet.

Usage (project root):
    .venv\\Scripts\\python.exe scripts\\run_signals.py

Outputs
  data/processed/signals_rj_2015_2022.csv        (git-ignored; one row per unit x year pair)
  docs/examples/evidence_packet_330490_2019_2020.json  (reference example, regenerated)
Counts are REPORTED, not used to tune thresholds.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402

from signalcheck.connectors import BrazilSIPNIConnector  # noqa: E402
from signalcheck.evidence import build_packet  # noqa: E402


def main() -> int:
    connector = BrazilSIPNIConnector(ROOT / "data" / "raw" / "brazil_sipni")
    obs = connector.load().observations
    rows, totals = [], Counter()
    for unit in sorted(obs.unit_code.unique()):
        for y in range(2015, 2022):
            p = build_packet(obs, connector, unit, y, y + 1)
            cls = [s["classification"] for s in p["signals"]]
            totals.update(set(cls))
            rows.append({"unit_code": unit, "unit_name": p["scope"]["unit_name"], "year_from": y,
                         "year_to": y + 1, "classifications": ";".join(cls), "n_signals": len(cls)})
    out = ROOT / "data" / "processed" / "signals_rj_2015_2022.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False, encoding="utf-8")

    example = build_packet(obs, connector, "330490", 2019, 2020)
    ex_path = ROOT / "docs" / "examples" / "evidence_packet_330490_2019_2020.json"
    ex_path.parent.mkdir(parents=True, exist_ok=True)
    ex_path.write_text(json.dumps(example, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"{len(rows)} unit-year pairs scanned ({obs.unit_code.nunique()} units x 7 pairs)")
    for k, v in sorted(totals.items()):
        print(f"  pairs with {k}: {v}")
    print(f"summary: {out.relative_to(ROOT)}\nexample: {ex_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
