"""Evidence packets: the only material a language model will see (Milestone 5+).

A packet is aggregate, traceable and validated:
1. structure: ``schemas/evidence_packet.schema.json`` (via ``jsonschema_lite``);
2. references: every evidence/input ID points to an existing fact or derived value;
3. grounding: every number in a statement or caution is a fact/derived value, a year
   in the packet, or a configured threshold;
4. language: no causal or uptake claims; no forbidden classifications.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from . import jsonschema_lite
from .connectors.base import Connector
from .signals import RULES_VERSION, Thresholds, evaluate, load_thresholds

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "evidence_packet.schema.json"
PACKET_VERSION = "1.0"

LIMITATIONS = [
    "Values are recorded administrative activity, not confirmed vaccination uptake.",
    "The official coverage denominator is unpublished; denominators shown here are back-calculated from published values or come from an independent reference series.",
    "Doses are attributed to the municipality where they were recorded; SINASC births to the mother's residence.",
    "Comparisons are limited to 2015-2022 (legacy SI-PNI on TabNet); a reporting-system transition began in 2023.",
    "2020-2021 may combine service disruption with registration-system effects; the data cannot separate them.",
    "No facility-level reporting completeness is available in this source.",
]

PROHIBITED = [
    "Stating that fewer (or more) children were vaccinated.",
    "Attributing a change to a cause (e.g. vaccine hesitancy, supply shortages, staffing, missed vaccinations, reporting failures) without independent evidence.",
    "Describing a back-calculated denominator as observed or as verified SINASC births.",
    "Classifying a change as numerator-driven or denominator-driven.",
    "Presenting a recalculated percentage as official coverage.",
    "Comparing values across the 2023 reporting-system transition.",
]

FORBIDDEN_CLASSIFICATIONS = {"numerator_driven", "denominator_driven", "uptake_decline", "reporting_failure"}

CAUSAL_PATTERNS = [
    r"\bbecause\b", r"\bdue to\b", r"\bcaused?\b", r"\bresult(ed)? of\b", r"\bled to\b", r"\bdriven by\b",
    r"\bhesitan", r"\bshortage", r"\bstock-?outs?\b", r"\bstaffing\b", r"\bmissed vaccinations?\b",
    r"\breporting failure", r"\bfewer children\b", r"\bmore children\b", r"\bchildren were (not )?vaccinated\b",
    r"\bverified sinasc\b", r"\bnumerator-driven\b", r"\bdenominator-driven\b",
]
# The two phrases above that name forbidden interpretations are allowed only in the
# explicit "cannot classify" disclaimer, checked by _strip_disclaimers().
_DISCLAIMER = re.compile(
    r"cannot classify this change as numerator- or denominator-driven|cannot establish cause", re.I)

NUMBER = re.compile(r"(?<![A-Za-z0-9.])-?\d+(?:\.\d+)?(?![A-Za-z0-9])")


class PacketError(ValueError):
    """An evidence packet failed validation."""


def _source_block(connector: Connector) -> dict:
    manifest = json.loads((connector.raw_dir / "manifest.json").read_text(encoding="utf-8"))
    return {
        "source_id": connector.source_id,
        "data_card": "DATA_CARD.md",
        "files": [{"file": e["file"], "sha256": e["sha256"], "retrieved_at_utc": e["retrieved_at_utc"]}
                  for e in manifest["files"]],
    }


def build_packet(obs: pd.DataFrame, connector: Connector, unit_code: str, year_from: int, year_to: int,
                 thresholds: Thresholds | None = None) -> dict:
    """Build and validate one packet. Raises on non-comparable or unsupported requests."""
    t = thresholds or load_thresholds()
    connector.check_comparable(year_from, year_to)          # refuses the 2023 transition
    names = obs.drop_duplicates("unit_code").set_index("unit_code")["unit_name"]
    if unit_code not in names.index:
        raise PacketError(f"unknown unit {unit_code}")
    files = {f.measure: f.file for f in getattr(connector, "files", ())}
    ledger = evaluate(obs, unit_code, year_from, year_to, t, files)
    packet = {
        "packet_version": PACKET_VERSION,
        "generated_by": {"rules_version": RULES_VERSION, "config_version": t.version, "config_sha256": t.sha256},
        "source": _source_block(connector),
        "scope": {
            "unit_code": unit_code, "unit_name": str(names[unit_code]),
            "admin1_code": str(obs.loc[obs.unit_code == unit_code, "admin1_code"].iloc[0]),
            "year_from": year_from, "year_to": year_to,
            "comparable": True, "system_transitions_crossed": [],
        },
        "facts": ledger.facts,
        "derived": ledger.derived,
        "signals": ledger.signals,
        "limitations": [{"id": f"L{i}", "text": s} for i, s in enumerate(LIMITATIONS, 1)],
        "prohibited_interpretations": list(PROHIBITED),
    }
    validate_packet(packet, t)
    return packet


# --------------------------------------------------------------------------- validation
def _allowed_numbers(packet: dict, t: Thresholds) -> list[float]:
    vals = [x["value"] for x in packet["facts"] + packet["derived"] if x["value"] is not None]
    vals += [x["year"] for x in packet["facts"]]
    vals += [packet["scope"]["year_from"], packet["scope"]["year_to"]]
    vals += [t.dose_change_pct, t.coverage_change_pp, t.implausible_upper_pct, t.state_divergence_pp,
             t.min_reference_births, t.min_base_doses]
    return vals


def ungrounded_numbers(packet: dict, t: Thresholds) -> list[str]:
    allowed = _allowed_numbers(packet, t)
    bad = []
    for s in packet["signals"]:
        for text in [s["statement"], *s["cautions"]]:
            for tok in NUMBER.findall(text):
                decimals = len(tok.split(".")[1]) if "." in tok else 0
                x = float(tok)
                if not any(round(v, decimals) == x or (decimals == 0 and round(v) == x) for v in allowed):
                    bad.append(f"{s['id']}: {tok}")
    return bad


def causal_language(packet: dict) -> list[str]:
    hits = []
    for s in packet["signals"]:
        for text in [s["statement"], *s["cautions"]]:
            cleaned = _DISCLAIMER.sub("", text)
            for p in CAUSAL_PATTERNS:
                if re.search(p, cleaned, re.I):
                    hits.append(f"{s['id']}: /{p}/")
    return hits


def validate_packet(packet: dict, thresholds: Thresholds | None = None) -> None:
    t = thresholds or load_thresholds()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        jsonschema_lite.validate(packet, schema)
    except jsonschema_lite.SchemaViolation as e:
        raise PacketError(f"schema: {e}") from e
    ids = {x["id"] for x in packet["facts"] + packet["derived"]}
    for item in packet["derived"]:
        missing = set(item["inputs"]) - ids
        if missing:
            raise PacketError(f"{item['id']} cites unknown inputs {sorted(missing)}")
    for s in packet["signals"]:
        missing = set(s["evidence"]) - ids
        if missing:
            raise PacketError(f"{s['id']} cites unknown evidence {sorted(missing)}")
        if s["classification"] in FORBIDDEN_CLASSIFICATIONS:
            raise PacketError(f"{s['id']}: forbidden classification {s['classification']}")
    bad = ungrounded_numbers(packet, t)
    if bad:
        raise PacketError(f"ungrounded numbers: {bad}")
    causal = causal_language(packet)
    if causal:
        raise PacketError(f"causal or uptake language: {causal}")
