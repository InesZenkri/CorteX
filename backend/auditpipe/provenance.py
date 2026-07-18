"""Provenance primitives. Every claim in the output is an Evidence with a
Citation that resolves to file + locus + verbatim quote. Serialization to JSON
is defined here so the whole pipeline speaks one citation format."""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from decimal import Decimal
from typing import Any


@dataclass
class Citation:
    file: str
    locus: str            # e.g. "line 2569" or "p.2" or "beleg ER901416"
    quote: str            # verbatim source substring (code-verified)

    def to_json(self) -> dict:
        return {"file": self.file, "locus": self.locus, "quote": self.quote}


@dataclass
class Evidence:
    text: str             # human-readable claim
    citation: Citation

    def to_json(self) -> dict:
        return {"text": self.text, "source": self.citation.to_json()}


@dataclass
class Finding:
    id: str
    scheme: str
    criterion: str
    title: str
    amount_eur: Decimal
    status: str                                   # confirmed | lead | cleared
    severity: str                                 # high | medium | low | observation
    confidence: Decimal
    inculpatory: list[Evidence] = field(default_factory=list)
    exculpatory: list[Evidence] = field(default_factory=list)
    narrative: str = ""

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "scheme": self.scheme,
            "criterion": self.criterion,
            "title": self.title,
            "amount_eur": _dec(self.amount_eur),
            "status": self.status,
            "severity": self.severity,
            "confidence": float(round(self.confidence, 3)),
            "inculpatory": [e.to_json() for e in self.inculpatory],
            "exculpatory": [e.to_json() for e in self.exculpatory],
            "narrative": self.narrative,
        }


def _dec(d: Decimal) -> float:
    return float(d)


def json_default(o: Any):
    if isinstance(o, Decimal):
        return float(o)
    raise TypeError(f"not serializable: {type(o)}")
