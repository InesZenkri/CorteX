"""Strict, attestable GPT-5.6 access through the OpenAI Responses API."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Any

from . import config

try:
    from openai import OpenAI
except ImportError as exc:  # pragma: no cover - deployment dependency failure
    OpenAI = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


class LLMUnavailable(RuntimeError):
    """Raised when a verified GPT-5.6 response cannot be obtained."""


@dataclass(frozen=True)
class CallReceipt:
    purpose: str
    response_id: str
    requested_model: str
    response_model: str
    input_tokens: int
    output_tokens: int


def available() -> bool:
    return OpenAI is not None and bool(os.getenv("OPENAI_API_KEY"))


def _is_required_model(returned_model: str) -> bool:
    normalized = (returned_model or "").lower()
    return (
        normalized == config.REQUIRED_MODEL
        or normalized == config.EXPECTED_RESPONSE_MODEL
        or normalized.startswith(f"{config.EXPECTED_RESPONSE_MODEL}-")
    )


class AuditLLM:
    def __init__(self, cfg: config.Config):
        if not available():
            detail = f": {_IMPORT_ERROR}" if _IMPORT_ERROR else ""
            raise LLMUnavailable(f"OPENAI_API_KEY and the OpenAI SDK are required{detail}")
        self.cfg = cfg
        self.client = OpenAI(timeout=cfg.request_timeout_seconds)
        self.receipts: list[CallReceipt] = []

    def json_response(self, purpose: str, instructions: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self.client.responses.create(
                model=self.cfg.model,
                reasoning={"effort": self.cfg.reasoning_effort},
                instructions=instructions,
                input=json.dumps({"response_format": "json", "payload": payload}, ensure_ascii=False, default=str),
                text={"format": {"type": "json_object"}, "verbosity": "medium"},
                max_output_tokens=self.cfg.max_output_tokens,
                store=False,
            )
        except Exception as exc:
            raise LLMUnavailable(f"GPT-5.6 request failed for {purpose}: {exc}") from exc

        returned_model = str(getattr(response, "model", ""))
        if getattr(response, "status", None) != "completed":
            raise LLMUnavailable(f"GPT-5.6 response for {purpose} was not completed")
        if not _is_required_model(returned_model):
            raise LLMUnavailable(
                f"Model attestation failed for {purpose}: requested {self.cfg.model}, "
                f"API returned {returned_model or 'no model'}"
            )

        usage = getattr(response, "usage", None)
        self.receipts.append(CallReceipt(
            purpose=purpose,
            response_id=str(response.id),
            requested_model=self.cfg.model,
            response_model=returned_model,
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
        ))
        try:
            parsed = json.loads(response.output_text)
        except (TypeError, json.JSONDecodeError) as exc:
            raise LLMUnavailable(f"GPT-5.6 returned invalid JSON for {purpose}") from exc
        if not isinstance(parsed, dict):
            raise LLMUnavailable(f"GPT-5.6 returned a non-object JSON value for {purpose}")
        return parsed

    def attestation(self) -> dict[str, Any]:
        if not self.receipts:
            raise LLMUnavailable("No GPT-5.6 calls were completed")
        return {
            "required": True,
            "verified": all(_is_required_model(receipt.response_model) for receipt in self.receipts),
            "requested_model": self.cfg.model,
            "response_models": sorted({receipt.response_model for receipt in self.receipts}),
            "calls": [asdict(receipt) for receipt in self.receipts],
        }


# Backwards-compatible name for callers that import LLM directly.
LLM = AuditLLM
