"""Promotion gate. Deterministic, auditable rule that converts detector
Candidates into Findings with status + confidence. Optionally asks GPT-5.6 for a
narrative and a list of innocent explanations, but the DECISION is always code's.

Rule:
  * If a strong exculpatory item explains the candidate -> CLEARED.
    (strong = goods receipt, four-eyes creation, genuine-investment wording,
     or a disclosed related party that is NOT off-market.)
  * Else confidence = detector score; status = FINDING if confidence >= threshold
    else LEAD.
  * Severity from amount vs materiality.
"""

from __future__ import annotations
from decimal import Decimal as D

from . import config, llm
from .detectors import Candidate
from .provenance import Finding


STRONG_CLEAR_MARKERS = (
    "goods receipt exists", "four-eyes", "genuine capital investment",
)


def _severity(amount: D, mat: config.Materiality) -> str:
    if amount >= mat.overall:
        return "high"
    if amount >= mat.tolerance:
        return "medium"
    if amount >= mat.trivial:
        return "low"
    return "observation"


def _is_cleared(c: Candidate) -> bool:
    for e in c.exculpatory:
        low = e.text.lower()
        if any(m in low for m in STRONG_CLEAR_MARKERS):
            return True
        # disclosed related party clears only when not off-market
        if "related party disclosed" in low and not c.subject.get("off_market"):
            return True
    return False


def promote(c: Candidate, cfg: config.Config, client: "llm.LLM | None") -> Finding:
    mat = cfg.materiality
    if _is_cleared(c):
        status, confidence, severity = "cleared", D("0.9"), "observation"
    else:
        confidence = c.score
        status = "confirmed" if confidence >= cfg.params.finding_min_confidence else "lead"
        severity = _severity(c.amount, mat)

    f = Finding(
        id=c.fid, scheme=c.scheme, criterion=c.criterion, title=c.title,
        amount_eur=c.amount, status=status, severity=severity,
        confidence=confidence, inculpatory=c.inculpatory, exculpatory=c.exculpatory,
    )
    if client is not None and status != "cleared":
        try:
            payload = {"title": f.title, "amount_eur": float(f.amount_eur),
                       "inculpatory": [e.to_json() for e in f.inculpatory]}
            res = client.defend_and_narrate(payload)
            f.narrative = res.get("narrative", "")
        except llm.LLMUnavailable:
            f.narrative = ""
    return f
