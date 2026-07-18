"""Central configuration. Everything tunable lives here so no detector hard-codes
a dossier-specific value (account numbers, names, thresholds)."""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

# Load OPENAI_API_KEY (and other vars) from .env. Project root first, then
# backend/.env for local overrides. Existing process env wins (override=False).
_PACKAGE_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _PACKAGE_DIR.parent
_ROOT_DIR = _BACKEND_DIR.parent
load_dotenv(_ROOT_DIR / ".env")
load_dotenv(_BACKEND_DIR / ".env")


# ---- LLM ------------------------------------------------------------------
LLM_MODEL = os.environ.get("AUDIT_MODEL", "gpt-5.6")
LLM_API_KEY_ENV = "OPENAI_API_KEY"
LLM_MAX_RETRIES = 3
LLM_TEMPERATURE = 0.0          # deterministic extraction
# When True, run without any network/LLM calls (deterministic parsers only).
# Auto-enabled if the SDK or API key is missing.
OFFLINE = os.environ.get("AUDIT_OFFLINE", "0") == "1"


# ---- GDPdU / German locale format constants ------------------------------
GDPDU_ENCODING = "ISO-8859-1"
CSV_DELIMITER = ";"
TEXT_QUOTE = '"'
DATE_FMT = "%d.%m.%Y"


@dataclass(frozen=True)
class Materiality:
    overall: Decimal = Decimal("400000")     # planning materiality
    tolerance: Decimal = Decimal("300000")   # tolerable misstatement
    trivial: Decimal = Decimal("25000")      # JET clearly-trivial threshold
    payment_four_eyes: Decimal = Decimal("10000")  # second-signature limit


@dataclass(frozen=True)
class DetectorParams:
    # structuring: N same-day same-payee payments each within [floor*L, L), sum > L
    struct_min_count: int = 3
    struct_floor_ratio: Decimal = Decimal("0.80")
    # fictitious vendor: promote when weighted score >= this
    fict_promote_score: Decimal = Decimal("0.60")
    fict_fast_pay_days: int = 5          # invoice->payment lag considered "fast"
    # related-party "off-market" heuristics
    relparty_round_modulo: Decimal = Decimal("1000")
    # confidence needed to call something a FINDING vs a LEAD
    finding_min_confidence: Decimal = Decimal("0.66")


@dataclass(frozen=True)
class Config:
    data_dir: str = "data"
    out_path: str = "output/findings.json"
    db_path: str = "output/evidence.db"
    materiality: Materiality = field(default_factory=Materiality)
    params: DetectorParams = field(default_factory=DetectorParams)
    model: str = LLM_MODEL


# repair/maintenance lexicon (extensible, multilingual). Detector uses this AND
# an LLM classification; a hit on either makes a description "maintenance".
REPAIR_LEXICON = (
    "reparatur", "instandsetzung", "instandhaltung", "austausch",
    "überholung", "generalüberholung", "wartung", "ersatzteil",
    "repair", "maintenance", "overhaul", "replacement of", "servicing",
)

# words signalling a genuine capital project (exculpatory for capex detector)
CAPEX_OK_LEXICON = (
    "investition", "investitionsantrag", "neuanschaffung", "erweiterung",
    "investment", "capex", "capital expenditure", "new line", "new machine",
)
