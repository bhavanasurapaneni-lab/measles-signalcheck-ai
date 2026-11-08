"""Claim-level validation of Claude's BriefDraft (Milestone 5).

What this CAN verify deterministically
  * Numbers: Claude may not write any (digits or spelled-out numbers / multipliers), so
    every number a reader sees comes from Python-generated observations.
  * Citations: every observation ID exists; claims cite the observations they discuss;
    every observation is discussed or explicitly skipped.
  * Place: no municipality / state other than the packet's own unit is named.
  * Period: no years can be written (digits banned); periods come from observations.
  * Indicator: indicator words in a claim (doses / coverage / births / state) must match
    the indicators of the cited observations.
  * Direction & magnitude: increase/decrease words must match the cited observation's
    direction; minimising words ("slight") are rejected for threshold-crossing signals.
  * Wording: no causal or uptake claims in evidence-supported text; possible
    explanations must be hedged and never asserted; no instruction-like text.

What it CANNOT verify
  * Whether a sentence's overall meaning is faithful in every nuance. Interpretive
    verbs ("suggests", "indicates", ...) therefore route the brief to HUMAN REVIEW
    instead of acceptance. Passing validation does not prove any public-health conclusion.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from .briefing import BriefDraft, Observation
from .evidence import CAUSAL_PATTERNS

ACCEPTED, REJECTED, HUMAN_REVIEW = "accepted", "rejected", "needs_human_review"

BRAZIL_STATES = [
    "acre", "alagoas", "amapa", "amazonas", "bahia", "ceara", "distrito federal", "espirito santo",
    "goias", "maranhao", "mato grosso", "mato grosso do sul", "minas gerais", "para", "paraiba",
    "parana", "pernambuco", "piaui", "rio grande do norte", "rio grande do sul", "rondonia",
    "roraima", "santa catarina", "sao paulo", "sergipe", "tocantins",
]

NUMBER_WORDS = (r"\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
                r"fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|"
                r"ninety|hundred|thousand|million|half|halved|quarter|third|double|doubled|triple|tripled|"
                r"twice|thrice|\w+fold)\b")
DIGIT = re.compile(r"\d")
OBS_ID = re.compile(r"^O\d+$")

KEYWORDS = {
    "doses": r"\b(doses?|administered|vaccinations? recorded)\b",
    "coverage": r"\bcoverage\b",
    "births": r"\b(births?|sinasc|live-born)\b",
    "state": r"\b(state ?wide|state benchmark|the state|state-level|state total)\b",
}
INCREASE = r"\b(increase[sd]?|increasing|rose|risen|rise|grew|grown|higher|jump(ed)?|gain(ed)?|up from)\b"
DECREASE = r"\b(decrease[sd]?|decreasing|fell|fallen|fall|drop(ped)?|declin\w*|lower|down from|reduc\w*|shr[ua]nk)\b"
MINIMISING = r"\b(slight(ly)?|small|modest(ly)?|marginal(ly)?|minor|negligible|little)\b"
HEDGES = r"\b(may|might|could|possibly|possible|potential(ly)?|perhaps)\b"
CERTAINTY = (r"\b(confirm(s|ed)?|prove[sdn]?|proof|demonstrat\w*|establish\w*|clearly|certainly|definitely|"
             r"because|due to|caused|causes|led to|result(ed)? (of|from)|driven by|explains?)\b")
INTERPRETIVE = r"\b(suggests?|indicates?|implies|imply|likely|probably|reflects?|means|evidence of|points? to)\b"
INSTRUCTION_LIKE = r"(ignore (all|any|previous|the)|system prompt|instructions?|disregard|as an ai|override)"
UPTAKE = r"\b(fewer|more) children (were|got|received|have been)\b|\bchildren (were|went) (not )?vaccinated\b"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch)).lower()


@dataclass
class ClaimResult:
    index: int
    kind: str
    citation_ok: bool
    grounded: bool
    reasons: list[str] = field(default_factory=list)
    review: list[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    verdict: str
    reasons: list[str]
    review_reasons: list[str]
    claims: list[ClaimResult]

    @property
    def citation_accuracy(self) -> float | None:
        """Share of claims that must cite evidence whose citations are valid and consistent."""
        cited = [c for c in self.claims if c.kind != "verification_action"]
        return None if not cited else sum(c.citation_ok for c in cited) / len(cited)

    @property
    def grounding_accuracy(self) -> float | None:
        ev = [c for c in self.claims if c.kind == "evidence_supported"]
        return None if not ev else sum(c.grounded for c in ev) / len(ev)


def validate_draft(draft: BriefDraft, observations: list[Observation],
                   place_names: list[str]) -> ValidationReport:
    """place_names: all known unit names (e.g. the 92 RJ municipalities)."""
    obs = {o.id: o for o in observations}
    reasons, review = [], []
    unit = _norm(observations[0].unit_name) if observations else ""
    others = sorted({_norm(n) for n in place_names} - {unit}, key=len, reverse=True) + \
        [s for s in BRAZIL_STATES if s != unit]

    def text_checks(text: str, where: str, allow_place_state=True) -> list[str]:
        t = _norm(text)
        bad = []
        if DIGIT.search(text):
            bad.append(f"{where}: contains digits (numbers must come from verified observations)")
        if re.search(NUMBER_WORDS, t):
            bad.append(f"{where}: contains a spelled-out number or multiplier")
        scrubbed = re.sub(r"(state of rio de janeiro|rio de janeiro state)", " ", t)
        for name in others:
            if re.search(rf"\b{re.escape(name)}\b", scrubbed):
                bad.append(f"{where}: names another place ({name})")
                break
        if re.search(INSTRUCTION_LIKE, t):
            bad.append(f"{where}: instruction-like text")
        if re.search(UPTAKE, t) and where != "possible_explanation":
            bad.append(f"{where}: claims a change in children vaccinated")
        return bad

    reasons += text_checks(draft.headline, "headline")
    for p in CAUSAL_PATTERNS:
        if re.search(p, _norm(draft.headline)):
            reasons.append("headline: causal or uptake wording")
            break

    results = []
    for i, c in enumerate(draft.claims, 1):
        r = ClaimResult(i, c.kind, citation_ok=True, grounded=True)
        where = f"claim {i} ({c.kind})"
        t = _norm(c.text)
        # --- citations
        unknown = [x for x in c.observation_ids if x not in obs or not OBS_ID.match(x)]
        if unknown:
            r.reasons.append(f"{where}: unknown observation IDs {unknown}")
            r.citation_ok = False
        if c.kind in ("evidence_supported", "possible_explanation") and not c.observation_ids:
            r.reasons.append(f"{where}: must cite at least one observation")
            r.citation_ok = False
        cited = [obs[x] for x in c.observation_ids if x in obs]
        # --- text-level checks
        r.reasons += text_checks(c.text, where if c.kind != "possible_explanation" else "possible_explanation")
        if len(c.text) > 400:
            r.reasons.append(f"{where}: longer than 400 characters")

        if c.kind == "evidence_supported":
            families = set().union(*(o.keyword_families for o in cited)) if cited else set()
            for fam, pat in KEYWORDS.items():
                if re.search(pat, t) and fam not in families:
                    r.reasons.append(f"{where}: mentions {fam} but cites no {fam} observation")
                    r.citation_ok = False
            dirs = {o.direction for o in cited if o.direction != "none"}
            if re.search(INCREASE, t) and dirs and "increase" not in dirs:
                r.reasons.append(f"{where}: says increase but cited observations show a decrease")
            if re.search(DECREASE, t) and dirs and "decrease" not in dirs:
                r.reasons.append(f"{where}: says decrease but cited observations show an increase")
            small_ok = any(o.classification == "small_denominator_caution" for o in cited)
            if re.search(MINIMISING, t) and not small_ok:
                r.reasons.append(f"{where}: minimises a change that crossed a review threshold")
            for p in CAUSAL_PATTERNS:
                if re.search(p, t):
                    r.reasons.append(f"{where}: causal or uptake wording in an evidence-supported claim")
                    break
            if re.search(INTERPRETIVE, t):
                r.review.append(f"{where}: interpretive wording cannot be verified automatically")
        elif c.kind == "possible_explanation":
            if not re.search(HEDGES, t):
                r.reasons.append(f"{where}: possible explanation is not hedged (may/might/could)")
            if re.search(CERTAINTY, t):
                r.reasons.append(f"{where}: presents a possible explanation as established")
        else:  # verification_action
            if re.search(CERTAINTY, t):
                r.reasons.append(f"{where}: verification action asserts a cause")
        r.grounded = not r.reasons
        results.append(r)
        reasons += r.reasons
        review += r.review

    # --- coverage of observations
    discussed = {x for c in draft.claims if c.kind == "evidence_supported" for x in c.observation_ids}
    skipped = set()
    for s in draft.observations_not_discussed:
        if s.observation_id not in obs:
            reasons.append(f"skipped unknown observation {s.observation_id}")
        skipped.add(s.observation_id)
        reasons += text_checks(s.reason, f"skip reason {s.observation_id}")
    missing = set(obs) - discussed - skipped
    if missing:
        reasons.append(f"observations neither discussed nor skipped: {sorted(missing)}")
    if not any(c.kind == "verification_action" for c in draft.claims):
        reasons.append("no verification action proposed")
    if len(draft.claims) > 12:
        reasons.append("more than 12 claims")

    verdict = REJECTED if reasons else HUMAN_REVIEW if review else ACCEPTED
    return ValidationReport(verdict, reasons, review, results)
