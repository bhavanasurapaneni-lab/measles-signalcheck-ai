"""Investigation-brief data model (Milestone 5).

Division of labour:
* Python turns each validated packet signal into an OBSERVATION (O#) whose text and
  numbers come only from the packet. These are the only numeric statements in a brief.
* Claude returns a BriefDraft: a headline and short claims that cite observation IDs,
  WITHOUT writing any numbers. Claims are typed as evidence-supported observations,
  possible explanations (unverified hypotheses) or verification actions.
* Python renders the final brief, inserting the verified observation text and the
  packet's own "cannot conclude" items and limitations.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Literal

from pydantic import BaseModel, Field

# classification -> (indicator, keyword families the claim may legitimately mention)
INDICATORS = {
    "recorded_dose_change": ("recorded_doses", {"doses"}),
    "reported_coverage_change": ("published_coverage", {"coverage"}),
    "implausible_coverage": ("published_coverage", {"coverage"}),
    "state_benchmark_divergence": ("recorded_doses_vs_state", {"doses", "state"}),
    "small_denominator_caution": ("population_size", {"births", "population"}),
    "insufficient_evidence": ("missing_evidence", {"doses", "coverage", "births", "missing"}),
}


@dataclass(frozen=True)
class Observation:
    id: str
    signal_id: str
    classification: str
    indicator: str
    direction: str            # "decrease" | "increase" | "none"
    unit_code: str
    unit_name: str
    years: tuple[int, ...]
    evidence_ids: tuple[str, ...]
    text: str                 # verified statement copied from the packet signal

    @property
    def keyword_families(self) -> set[str]:
        return INDICATORS[self.classification][1]


def _direction(packet: dict, signal: dict) -> str:
    if signal["classification"] not in ("recorded_dose_change", "reported_coverage_change",
                                        "state_benchmark_divergence"):
        return "none"
    values = {d["id"]: d["value"] for d in packet["derived"]}
    wanted = {"recorded_dose_change": "doses_relative_change_pct",
              "reported_coverage_change": "published_coverage_change_pp",
              "state_benchmark_divergence": "divergence_from_state_pp"}[signal["classification"]]
    names = {d["id"]: d["name"] for d in packet["derived"]}
    for ref in signal["evidence"]:
        if names.get(ref) == wanted and values.get(ref) is not None:
            v = values[ref]
            return "decrease" if v < 0 else "increase" if v > 0 else "none"
    return "none"


def observations_from_packet(packet: dict) -> list[Observation]:
    facts = {f["id"]: f for f in packet["facts"]}
    scope = packet["scope"]
    out = []
    for i, s in enumerate(packet["signals"], 1):
        years = sorted({facts[r]["year"] for r in s["evidence"] if r in facts}) or \
            [scope["year_from"], scope["year_to"]]
        out.append(Observation(
            id=f"O{i}", signal_id=s["id"], classification=s["classification"],
            indicator=INDICATORS[s["classification"]][0], direction=_direction(packet, s),
            unit_code=scope["unit_code"], unit_name=scope["unit_name"], years=tuple(years),
            evidence_ids=tuple(s["evidence"]), text=s["statement"]))
    return out


# ------------------------------------------------------------- Claude's output contract
class Claim(BaseModel):
    kind: Literal["evidence_supported", "possible_explanation", "verification_action"] = Field(
        description="evidence_supported: restates what cited observations show. possible_explanation: "
                    "an UNVERIFIED hypothesis to investigate, hedged (may/might/could). "
                    "verification_action: a neutral step a coordinator can take to check the data.")
    text: str = Field(description="One or two sentences. Must not contain any digits or spelled-out numbers.")
    observation_ids: list[str] = Field(description="IDs like O1 that this claim is about.")


class SkippedObservation(BaseModel):
    observation_id: str
    reason: str = Field(description="Short reason, no digits.")


class BriefDraft(BaseModel):
    headline: str = Field(description="One neutral sentence, no digits, no causes.")
    claims: list[Claim]
    observations_not_discussed: list[SkippedObservation]


# ----------------------------------------------------------------------- brief input
def brief_input(packet: dict) -> dict:
    """The compact, aggregate payload sent to Claude (derived from a validated packet)."""
    obs = observations_from_packet(packet)
    cannot = []
    for s in packet["signals"]:
        for c in s["cannot_conclude"]:
            if c not in cannot:
                cannot.append(c)
    return {
        "scope": {k: packet["scope"][k] for k in ("unit_code", "unit_name", "year_from", "year_to")},
        "observations": [{"id": o.id, "classification": o.classification, "indicator": o.indicator,
                          "direction": o.direction, "statement": o.text} for o in obs],
        "cannot_conclude": cannot,
        "limitations": [x["text"] for x in packet["limitations"]],
        "prohibited_interpretations": packet["prohibited_interpretations"],
    }


def packet_sha256(packet: dict) -> str:
    return hashlib.sha256(json.dumps(packet, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- rendering
def render_markdown(packet: dict, draft: BriefDraft, verdict: str, provenance: dict) -> str:
    obs = {o.id: o for o in observations_from_packet(packet)}
    sc = packet["scope"]
    lines = [f"# Investigation brief: {sc['unit_name']} ({sc['unit_code']}), {sc['year_from']}–{sc['year_to']}",
             "", f"> Validation verdict: **{verdict}**. Automated validation checks traceability and wording; "
             "it does not prove any public-health conclusion. A person must review this brief.", "",
             f"**{draft.headline}**", "", "## Verified observations (generated from the evidence packet)"]
    lines += [f"- **{o.id}** {o.text} _(evidence: {', '.join(o.evidence_ids)})_" for o in obs.values()]
    for kind, title in (("evidence_supported", "What the observations show"),
                        ("possible_explanation", "Unverified possibilities to investigate (not findings)"),
                        ("verification_action", "Recommended verification actions")):
        items = [c for c in draft.claims if c.kind == kind]
        if items:
            lines += ["", f"## {title}"]
            lines += [f"- {c.text}" + (f" _({', '.join(c.observation_ids)})_" if c.observation_ids else "")
                      for c in items]
    seen = []
    for s in packet["signals"]:
        seen += [c for c in s["cannot_conclude"] if c not in seen]
    lines += ["", "## What this data cannot show"] + [f"- {c}" for c in seen]
    lines += ["", "## Limitations"] + [f"- **{x['id']}** {x['text']}" for x in packet["limitations"]]
    lines += ["", "---", "Provenance: " + ", ".join(f"{k}={v}" for k, v in provenance.items())]
    return "\n".join(lines) + "\n"


def as_dict(o: Observation) -> dict:
    return asdict(o)
