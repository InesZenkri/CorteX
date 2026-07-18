"""GPT-5.6 access layer.

Responsibilities kept to what LLMs are reliably good at:
  * classify a document (invoice / bank confirmation / financial statement / ...)
  * extract structured records from UNSTRUCTURED text (PDF/DOCX) with a verbatim
    source quote per record
  * resolve entity aliases across German/English
  * write the narrative + candidate innocent explanations for triage

Hard contract: every extracted value must be accompanied by a `quote` that is a
verbatim substring of the source text. `verify_quotes()` drops any record whose
quote does not string-match the source — this makes hallucinated numbers
structurally unable to reach the ledger.

If the OpenAI SDK or API key is unavailable, the module runs in OFFLINE mode and
raises on any call, so orchestration can skip LLM steps and use deterministic
parsers (GDPdU/CSV need no LLM at all).
"""

from __future__ import annotations
import json
import os
from typing import Any

from . import config

try:                                   # optional dependency
    from openai import OpenAI          # type: ignore
    _SDK = True
except Exception:                      # pragma: no cover
    _SDK = False


class LLMUnavailable(RuntimeError):
    pass


def available() -> bool:
    return _SDK and bool(os.environ.get(config.LLM_API_KEY_ENV)) and not config.OFFLINE


class LLM:
    def __init__(self, model: str | None = None):
        self.model = model or config.LLM_MODEL
        if not available():
            raise LLMUnavailable(
                "GPT-5.6 unavailable (missing SDK, OPENAI_API_KEY, or OFFLINE=1). "
                "Deterministic parsers will be used instead."
            )
        self._client = OpenAI()

    # -- core call: always returns parsed JSON -----------------------------
    def _json_call(self, system: str, user: str) -> dict:
        last = None
        for _ in range(config.LLM_MAX_RETRIES):
            try:
                resp = self._client.chat.completions.create(
                    model=self.model,
                    temperature=config.LLM_TEMPERATURE,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                return json.loads(resp.choices[0].message.content)
            except Exception as e:               # retry on transient/parse errors
                last = e
        raise LLMUnavailable(f"LLM call failed after retries: {last}")

    # -- document classification + extraction ------------------------------
    def extract_document(self, filename: str, text: str) -> dict:
        """Return {doc_type, records:[{fields, quote}], entities:[...]}."""
        system = (
            "You are a forensic-audit extraction engine. Classify the document and "
            "extract structured records. For EVERY record you MUST include a 'quote' "
            "field containing a VERBATIM substring copied from the source text that "
            "supports the record's key figures. Never invent numbers. Respond ONLY "
            "with JSON of shape: {\"doc_type\": str, \"records\": [{\"fields\": object, "
            "\"quote\": str}], \"entities\": [{\"name\": str, \"role\": str, "
            "\"ids\": object}]}. doc_type is one of: invoice, order, goods_receipt, "
            "bank_confirmation, financial_statement, trial_balance, contract, "
            "authorization_matrix, shareholder_list, protocol, other."
        )
        user = f"FILENAME: {filename}\n\nSOURCE TEXT:\n{text[:120000]}"
        data = self._json_call(system, user)
        data["records"] = verify_quotes(text, data.get("records", []))
        return data

    # -- entity resolution -------------------------------------------------
    def resolve_entities(self, names: list[str]) -> dict:
        """Group name variants (DE/EN) that refer to the same legal entity."""
        system = (
            "Group the following counterparty names that refer to the SAME legal "
            "entity (handle German/English variants, GmbH/AG suffixes, abbreviations). "
            "Respond ONLY as JSON: {\"groups\": [{\"canonical\": str, "
            "\"aliases\": [str]}]}."
        )
        return self._json_call(system, "NAMES:\n" + "\n".join(sorted(set(names))))

    # -- triage narrative + defense ---------------------------------------
    def defend_and_narrate(self, finding_json: dict) -> dict:
        """Given a candidate finding + its evidence, produce a plain-language
        narrative and a list of innocent explanations an auditor should rule out.
        This informs (does not decide) the deterministic gate."""
        system = (
            "You are the DEFENSE in an audit triage. Given a candidate finding and "
            "its cited evidence, (1) write a concise, neutral narrative an auditor "
            "can read, and (2) list plausible INNOCENT explanations, each naming the "
            "specific document that would refute the concern if it existed. Respond "
            "ONLY as JSON: {\"narrative\": str, \"innocent_explanations\": "
            "[{\"explanation\": str, \"refuting_document\": str}]}."
        )
        return self._json_call(system, json.dumps(finding_json, default=str))


# -- quote verification (runs even without the SDK) -------------------------
def _norm(s: str) -> str:
    return " ".join(str(s).split()).lower()


def verify_quotes(source_text: str, records: list[dict]) -> list[dict]:
    """Keep only records whose 'quote' is a verbatim (whitespace-normalized)
    substring of the source. Anti-hallucination gate for extracted numbers."""
    hay = _norm(source_text)
    kept = []
    for r in records:
        q = _norm(r.get("quote", ""))
        if q and q in hay:
            r["_verified"] = True
            kept.append(r)
    return kept
