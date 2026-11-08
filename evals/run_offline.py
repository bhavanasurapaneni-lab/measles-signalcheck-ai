"""Offline evaluation: grounding validator on labelled drafts + simulated API outcomes.

No network, no key, no cost.  Usage (project root):
    .venv\\Scripts\\python.exe -m evals.run_offline
Writes evals/results/offline_<UTC date>.json and prints a summary.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["SIGNALCHECK_OFFLINE"] = "1"

from evals.cases import draft_cases, good_draft_sao_goncalo, load_real, synthetic_packets, tampered_packet  # noqa: E402
from evals.fake_client import FakeClient, api_error, response  # noqa: E402
from signalcheck.brief_client import DEFAULT_MODEL, generate_brief  # noqa: E402
from signalcheck.brief_validator import validate_draft  # noqa: E402
from signalcheck.briefing import observations_from_packet  # noqa: E402

CFG = {"model": DEFAULT_MODEL, "effort": "medium", "max_tokens": 8000}


def main() -> int:
    packets, names = load_real()
    rows = []
    for cid, pid, draft, expected, mode in draft_cases():
        r = validate_draft(draft, observations_from_packet(packets[pid]), names)
        rows.append({"case": cid, "failure_mode": mode, "expected": expected, "verdict": r.verdict,
                     "correct": r.verdict == expected, "citation_accuracy": r.citation_accuracy,
                     "grounding_accuracy": r.grounding_accuracy, "reasons": r.reasons or r.review_reasons})

    sg = packets["real_sao_goncalo_2019_2020"]
    sim = []
    for label, outcome in [("rate_limit", api_error("rate_limit")), ("server_error", api_error("server")),
                           ("connection", api_error("connection")), ("timeout", api_error("timeout")),
                           ("auth", api_error("auth")), ("model_not_found", api_error("not_found")),
                           ("refusal", response(stop_reason="refusal", category="bio")),
                           ("truncated", response(stop_reason="max_tokens")),
                           ("no_structured_output", response(parsed=None)),
                           ("good_response", response(parsed=good_draft_sao_goncalo()))]:
        res = generate_brief(sg, names, client=FakeClient(outcome), cfg=CFG)
        sim.append({"simulated": label, "status": res.status, "detail": res.detail})
    fake = FakeClient(response(parsed=good_draft_sao_goncalo()))
    res = generate_brief(tampered_packet(sg), names, client=fake, cfg=CFG)
    sim.append({"simulated": "contradictory_packet", "status": res.status, "detail": res.detail,
                "api_called": bool(fake.requests)})
    for k, p in synthetic_packets().items():
        sim.append({"simulated": f"preflight:{k}", "status": "would_send",
                    "observations": [o.classification for o in observations_from_packet(p)]})

    n = len(rows)
    summary = {
        "draft_cases": n,
        "verdict_matches_expected": sum(r["correct"] for r in rows),
        "known_bad_drafts_rejected_or_reviewed": sum(r["verdict"] != "accepted" for r in rows if r["expected"] != "accepted"),
        "known_bad_drafts": sum(r["expected"] != "accepted" for r in rows),
        "known_good_drafts_accepted": sum(r["verdict"] == "accepted" for r in rows if r["expected"] == "accepted"),
        "known_good_drafts": sum(r["expected"] == "accepted" for r in rows),
    }
    out = {"generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "note": "Offline evaluation of the validator and failure handling with SYNTHETIC drafts. "
                   "It measures the checks, not Claude, and proves no public-health conclusion.",
           "summary": summary, "draft_results": rows, "simulated_api_outcomes": sim}
    path = ROOT / "evals" / "results" / f"offline_{datetime.now(timezone.utc):%Y%m%d}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))
    for r in rows:
        print(f"{'OK ' if r['correct'] else 'XX '} {r['verdict']:18s} {r['case']}  [{r['failure_mode']}]")
    for s in sim:
        print(f"   {s['simulated']:40s} -> {s['status']}")
    print(f"written: {path.relative_to(ROOT)}")
    return 0 if summary["verdict_matches_expected"] == n else 1


if __name__ == "__main__":
    sys.exit(main())
