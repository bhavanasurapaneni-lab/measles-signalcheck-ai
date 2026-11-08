"""Live evaluation (PAID). Disabled unless the owner approves a maximum spend.

Step 1 - estimate only (no network, no key needed):
    .venv\\Scripts\\python.exe -m evals.run_live --estimate
Step 2 - after explicit owner approval, run with a spending cap at or above the estimate:
    .venv\\Scripts\\python.exe -m evals.run_live --run --approve-max-usd 3.00

The key is read by the SDK from the git-ignored .env; it is never printed or logged.
Only validated aggregate packets are sent. Results go to evals/results/live_<timestamp>.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from evals.cases import load_real, synthetic_packets  # noqa: E402
from signalcheck.brief_client import PRICES, build_request, generate_brief, preflight, settings  # noqa: E402
from signalcheck.briefing import BriefDraft  # noqa: E402

CHARS_PER_TOKEN = 3.0       # conservative (real JSON/English is usually ~3.5-4 chars per token)
SCHEMA_OVERHEAD_TOKENS = 600
EXPECTED_OUTPUT_TOKENS = 2500   # assumption: medium-effort thinking + a ~600-token JSON brief


def cases():
    packets, names = load_real()
    allp = dict(packets)
    allp.update(synthetic_packets())
    return allp, names


def estimate(cfg: dict) -> dict:
    packets, _ = cases()
    price = PRICES[cfg["model"]]
    rows, max_total, exp_total = [], 0.0, 0.0
    for cid, p in packets.items():
        preflight(p)
        req = build_request(p, cfg)
        chars = len(req["system"][0]["text"]) + len(req["messages"][0]["content"])
        in_tok = int(chars / CHARS_PER_TOKEN) + SCHEMA_OVERHEAD_TOKENS
        worst = (in_tok * price["cache_write"] + cfg["max_tokens"] * price["output"]) / 1e6
        expected = (in_tok * price["input"] + EXPECTED_OUTPUT_TOKENS * price["output"]) / 1e6
        rows.append({"case": cid, "est_input_tokens": in_tok, "max_output_tokens": cfg["max_tokens"],
                     "max_cost_usd": round(worst, 4), "expected_cost_usd": round(expected, 4)})
        max_total += worst
        exp_total += expected
    return {"model": cfg["model"], "effort": cfg["effort"], "calls": len(rows),
            "max_total_usd": round(max_total, 2), "expected_total_usd": round(exp_total, 2),
            "assumptions": {"chars_per_token": CHARS_PER_TOKEN, "schema_overhead_tokens": SCHEMA_OVERHEAD_TOKENS,
                            "expected_output_tokens": EXPECTED_OUTPUT_TOKENS,
                            "max_case": "every call uses max_tokens and pays cache-write price on all input"},
            "per_case": rows}


LEDGER = ROOT / "evals" / "results" / "spend_ledger.json"


def ledger_total() -> float:
    if not LEDGER.exists():
        return 0.0
    return float(json.loads(LEDGER.read_text(encoding="utf-8")).get("total_usd", 0.0))


def ledger_add(case: str, usd: float) -> None:
    data = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else {"total_usd": 0.0, "calls": []}
    data["calls"].append({"case": case, "usd": usd, "at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    data["total_usd"] = round(data["total_usd"] + usd, 6)
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def run(cfg: dict, cap: float, only: list[str] | None, skip: list[str] | None) -> int:
    """cap = TOTAL approved budget for this evaluation, across runs (tracked in the ledger)."""
    if os.getenv("SIGNALCHECK_OFFLINE") == "1":
        print("Refusing: SIGNALCHECK_OFFLINE=1 is set.")
        return 2
    est = {r["case"]: r for r in estimate(cfg)["per_case"]}
    packets, names = cases()
    unknown = set(only or []) | set(skip or [])
    unknown -= set(packets)
    if unknown:
        print(f"Refusing: unknown case ids {sorted(unknown)}")
        return 2
    selected = [c for c in packets if (not only or c in only) and not (skip and c in skip)]
    spent_before = ledger_total()
    projected_max = spent_before + sum(est[c]["max_cost_usd"] for c in selected)
    print(f"already spent ${spent_before:.4f}; worst case after this run ${projected_max:.4f}; cap ${cap:.2f}")
    if projected_max > cap:
        print("Refusing: the worst-case total could exceed the approved cap.")
        return 2
    spent, results = 0.0, []
    for cid in selected:
        p = packets[cid]
        if spent_before + spent + est[cid]["max_cost_usd"] > cap:
            print("Stopping: the next call could exceed the approved cap.")
            break
        r = generate_brief(p, names, cfg=cfg)
        spent += r.cost_usd or 0.0
        ledger_add(cid, r.cost_usd or 0.0)
        v = r.validation
        results.append({"case": cid, "status": r.status, "detail": r.detail, "usage": r.usage,
                        "cost_usd": r.cost_usd, "latency_s": r.latency_s, "provenance": r.provenance,
                        "citation_accuracy": v.citation_accuracy if v else None,
                        "grounding_accuracy": v.grounding_accuracy if v else None,
                        "reasons": (v.reasons + v.review_reasons) if v else [],
                        "draft": r.draft.model_dump() if isinstance(r.draft, BriefDraft) else None,
                        "markdown": r.markdown})
        print(f"{cid:40s} {r.status:20s} ${r.cost_usd or 0:.4f} {r.latency_s or 0:.1f}s "
              f"in={r.usage.get('input_tokens')} out={r.usage.get('output_tokens')} "
              f"cache_r={r.usage.get('cache_read_input_tokens')} cache_w={r.usage.get('cache_creation_input_tokens')}")
        if r.status in ("auth_error", "config_error"):
            print("Stopping: configuration problem; fix it before further calls.")
            break
    path = ROOT / "evals" / "results" / f"live_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    path.write_text(json.dumps({"config": cfg, "estimate": est, "spent_usd": round(spent, 4),
                                "results": results}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"spent this run ${spent:.4f}; ledger total ${ledger_total():.4f}; written {path.relative_to(ROOT)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--estimate", action="store_true")
    g.add_argument("--run", action="store_true")
    ap.add_argument("--approve-max-usd", type=float, help="TOTAL approved budget across runs")
    ap.add_argument("--only", nargs="*", help="run only these case ids (e.g. a smoke test)")
    ap.add_argument("--skip", nargs="*", help="skip these case ids (e.g. already run)")
    a = ap.parse_args()
    cfg = settings()
    if a.estimate:
        print(json.dumps(estimate(cfg), indent=2))
        return 0
    if a.approve_max_usd is None:
        print("Refusing: --run requires --approve-max-usd (owner-approved spending cap).")
        return 2
    return run(cfg, a.approve_max_usd, a.only, a.skip)


if __name__ == "__main__":
    sys.exit(main())
