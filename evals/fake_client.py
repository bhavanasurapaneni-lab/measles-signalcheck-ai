"""Offline stand-in for ``anthropic.Anthropic`` (no network, no key, no cost).

It records the request it receives and returns a scripted response or raises a real SDK
exception class, so the production code paths are exercised exactly.
"""
from __future__ import annotations

from types import SimpleNamespace

import anthropic
import httpx2

_REQ = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


def api_error(kind: str) -> Exception:
    status = {"rate_limit": (anthropic.RateLimitError, 429), "auth": (anthropic.AuthenticationError, 401),
              "permission": (anthropic.PermissionDeniedError, 403), "not_found": (anthropic.NotFoundError, 404),
              "bad_request": (anthropic.BadRequestError, 400), "server": (anthropic.InternalServerError, 500)}
    if kind == "connection":
        return anthropic.APIConnectionError(request=_REQ)
    if kind == "timeout":
        return anthropic.APITimeoutError(request=_REQ)
    cls, code = status[kind]
    return cls(f"simulated {kind}", response=httpx2.Response(code, request=_REQ), body=None)


def response(parsed=None, stop_reason="end_turn", category=None, usage=(1800, 900, 0, 1100)):
    i, o, cr, cw = usage
    return SimpleNamespace(
        stop_reason=stop_reason, parsed_output=parsed, _request_id="req_SIMULATED",
        stop_details=SimpleNamespace(category=category) if stop_reason == "refusal" else None,
        usage=SimpleNamespace(input_tokens=i, output_tokens=o, cache_read_input_tokens=cr,
                              cache_creation_input_tokens=cw))


class FakeClient:
    def __init__(self, outcome):
        """outcome: a response object, or an Exception instance to raise."""
        self.outcome = outcome
        self.requests: list[dict] = []
        self.messages = self

    def parse(self, **kwargs):
        self.requests.append(kwargs)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome
