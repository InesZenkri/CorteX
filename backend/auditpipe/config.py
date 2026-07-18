"""Runtime configuration for the strict GPT-5.6 audit pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PACKAGE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = PACKAGE_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent
load_dotenv(PROJECT_DIR / ".env", override=False)
load_dotenv(BACKEND_DIR / ".env", override=False)

REQUIRED_MODEL = "gpt-5.6"
EXPECTED_RESPONSE_MODEL = "gpt-5.6-sol"


def _positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


@dataclass(frozen=True)
class Config:
    data_dir: str = os.getenv("AUDIT_DATA_DIR", "data")
    out_path: str = os.getenv("AUDIT_OUTPUT_PATH", "output/findings.json")
    db_path: str = os.getenv("AUDIT_EVIDENCE_PATH", "output/evidence.json")
    model: str = REQUIRED_MODEL
    reasoning_effort: str = os.getenv("AUDIT_REASONING_EFFORT", "medium")
    batch_characters: int = _positive_int("AUDIT_BATCH_CHARACTERS", 600_000)
    max_output_tokens: int = _positive_int("AUDIT_MAX_OUTPUT_TOKENS", 20_000)
    parallel_batches: int = _positive_int("AUDIT_PARALLEL_BATCHES", 3)
    request_timeout_seconds: int = _positive_int("AUDIT_REQUEST_TIMEOUT_SECONDS", 600)
    prompts_dir: Path = Path(os.getenv("AUDIT_PROMPTS_DIR", str(BACKEND_DIR / "prompts")))

    def __post_init__(self) -> None:
        if self.model != REQUIRED_MODEL:
            raise ValueError(f"Only {REQUIRED_MODEL} is permitted for audit reports")
        if self.reasoning_effort not in {"low", "medium", "high", "xhigh", "max"}:
            raise ValueError("Unsupported AUDIT_REASONING_EFFORT")
