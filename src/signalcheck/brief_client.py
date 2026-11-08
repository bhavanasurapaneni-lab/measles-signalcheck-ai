"""Generate an investigation brief from ONE validated evidence packet (single API call).

Safety and reproducibility choices (see PROJECT_DECISIONS.md D-020 to D-024):
* Only a validated, aggregate packet is used; it is re-validated here before sending.
* Model from CLAUDE_MODEL (default claude-opus-5-5); effort set explicitly (default medium).
* No cross-model refusal fallback: a refusal is recorded as an outcome.
* Structured output via ``client.messages.parse(output_format=BriefDraft)``; the system
  prompt carries a cache_control marker (prompt caching).
* The API key is read by the SDK from the environment / .env and is never printed or logged.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import pydantic

from .brief_validator import ValidationReport, validate_draft
from .briefing import BriefDraft, brief_input, observations_from_packet, packet_sha256, render_markdown
from .evidence import PacketError, validate_packet

ROOT = Path(__file__).resolve().parents[2]
PROMPT_PATH = ROOT / "prompts" / "brief_v1.md"
DEFAULT_MODEL = "claude-opus-5-5"
DEFAULT_EFFORT = "medium"
DEFAULT_MAX_TOKENS = 8000
# USD per million tokens (Claude API list prices for claude-opus-5-5, checked 2026-11-07).
PRICES = {"claude-opus-5-5": {"input": 4.00, "output": 20.00, "cache_read": 0.20, "cache_write": 5.00}}
UNIT_NAME_OK = re.compile(r"^[A-Z0-9 '\-À-Ü]{1,60}$")


@dataclass
class BriefResult:
    status: str              # accepted | needs_human_review | rejected | refused | truncated |
                             # api_error | auth_error | config_error | invalid_packet
    detail: str = ""
    validation: ValidationReport | None = None
    draft: BriefDraft | None = None
    markdown: str | None = None
    usage: dict = field(default_factory=dict)
    cost_usd: float | None = None
    latency_s: float | None = None
    provenance: dict = field(default_factory=dict)


def prompt_text() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def prompt_sha256() -> str:
    return hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest()


def settings() -> dict:
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env", override=False)
    except ImportError:  # pragma: no cover
        pass
    return {
        "model": os.getenv("CLAUDE_MODEL", DEFAULT_MODEL),
        "effort": os.getenv("CLAUDE_EFFORT", DEFAULT_EFFORT),
        "max_tokens": int(os.getenv("CLAUDE_MAX_TOKENS", DEFAULT_MAX_TOKENS)),
    }


def build_request(packet: dict, cfg: dict) -> dict:
    """Exact keyword arguments for ``client.messages.parse`` (also used for cost estimates)."""
    payload = json.dumps(brief_input(packet), ensure_ascii=False, sort_keys=True)
    return {
        "model": cfg["model"],
        "max_tokens": cfg["max_tokens"],
        "system": [{"type": "text", "text": prompt_text(), "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": f"<brief_input>\n{payload}\n</brief_input>\n\n"
                                                    "Write the investigation brief for this input."}],
        "output_config": {"effort": cfg["effort"]},
        "output_format": BriefDraft,
    }


def preflight(packet: dict) -> None:
    """Refuse anything that is not a validated, aggregate packet."""
    validate_packet(packet)
    if not UNIT_NAME_OK.match(packet["scope"]["unit_name"]):
        raise PacketError("unit_name contains unexpected characters")


def cost_usd(model: str, usage: dict) -> float | None:
    p = PRICES.get(model)
    if not p:
        return None
    return round((usage.get("input_tokens", 0) * p["input"] + usage.get("output_tokens", 0) * p["output"]
                  + usage.get("cache_read_input_tokens", 0) * p["cache_read"]
                  + usage.get("cache_creation_input_tokens", 0) * p["cache_write"]) / 1e6, 6)


def _usage(resp) -> dict:
    u = getattr(resp, "usage", None)
    return {k: int(getattr(u, k, 0) or 0) for k in
            ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")} if u else {}


def generate_brief(packet: dict, place_names: list[str], client=None, cfg: dict | None = None) -> BriefResult:
    cfg = cfg or settings()
    prov = {"model": cfg["model"], "effort": cfg["effort"], "prompt_sha256": prompt_sha256()[:12],
            "packet_sha256": packet_sha256(packet)[:12], "fallback": "disabled"}
    try:
        preflight(packet)
    except PacketError as e:
        return BriefResult("invalid_packet", str(e), provenance=prov)

    if client is None:
        import anthropic
        if os.getenv("SIGNALCHECK_OFFLINE") == "1":
            return BriefResult("config_error", "Offline mode (SIGNALCHECK_OFFLINE=1): no real API client is "
                               "created. Live calls run only through evals/run_live.py after approval.",
                               provenance=prov)
        if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")):
            return BriefResult("config_error", "No API credentials found. Add ANTHROPIC_API_KEY to the "
                               "git-ignored .env file yourself; never paste a key into chat.", provenance=prov)
        client = anthropic.Anthropic(max_retries=3)

    import anthropic  # for exception classes (fake clients raise the same types)
    req = build_request(packet, cfg)
    t0 = time.perf_counter()
    try:
        resp = client.messages.parse(**req)
    except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as e:
        return BriefResult("auth_error", f"{type(e).__name__}: check the API key and its permissions",
                           provenance=prov)
    except anthropic.NotFoundError:
        return BriefResult("config_error", f"Model or endpoint not found: {cfg['model']}", provenance=prov)
    except anthropic.BadRequestError as e:
        return BriefResult("api_error", f"BadRequestError: {getattr(e, 'message', '')[:200]}", provenance=prov)
    except anthropic.RateLimitError:
        return BriefResult("api_error", "RateLimitError after SDK retries; try again later", provenance=prov)
    except anthropic.APIStatusError as e:
        return BriefResult("api_error", f"APIStatusError {e.status_code} after SDK retries", provenance=prov)
    except anthropic.APIConnectionError as e:   # includes APITimeoutError
        return BriefResult("api_error", f"{type(e).__name__}: network problem", provenance=prov)
    except (pydantic.ValidationError, json.JSONDecodeError) as e:  # malformed structured output
        return BriefResult("rejected", f"output could not be parsed: {type(e).__name__}", provenance=prov)
    latency = round(time.perf_counter() - t0, 3)
    usage = _usage(resp)
    base = dict(usage=usage, cost_usd=cost_usd(cfg["model"], usage), latency_s=latency, provenance=prov)
    prov["request_id"] = getattr(resp, "_request_id", None) or ""

    if resp.stop_reason == "refusal":
        cat = getattr(getattr(resp, "stop_details", None), "category", None)
        return BriefResult("refused", f"model declined (category={cat}); no fallback by design", **base)
    if resp.stop_reason == "max_tokens":
        return BriefResult("truncated", "output hit max_tokens; brief discarded", **base)
    draft = getattr(resp, "parsed_output", None)
    if not isinstance(draft, BriefDraft):
        return BriefResult("rejected", "no valid structured output returned", **base)

    report = validate_draft(draft, observations_from_packet(packet), place_names)
    md = render_markdown(packet, draft, report.verdict, prov) if report.verdict != "rejected" else None
    return BriefResult(report.verdict, "; ".join(report.reasons or report.review_reasons),
                       validation=report, draft=draft, markdown=md, **base)
