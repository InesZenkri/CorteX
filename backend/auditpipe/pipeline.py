"""Strict GPT-5.6 dossier analysis with deterministic source verification."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal, InvalidOperation
from pathlib import Path
from collections.abc import Callable
from typing import Any

from . import config, ingest, llm


class InvalidModelOutput(RuntimeError):
    pass


def _prompt(cfg: config.Config, name: str) -> str:
    path = cfg.prompts_dir / name
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Required audit prompt is unavailable: {path}") from exc


def _normalize(value: object) -> str:
    return " ".join(str(value or "").split()).casefold()


def _source_index(documents: list[ingest.SourceDocument]) -> dict[str, ingest.SourceDocument]:
    return {document.path: document for document in documents}


def _locate(content: str, quote: str) -> str | None:
    normalized_quote = _normalize(quote)
    if not normalized_quote:
        return None
    lines = content.splitlines()
    for line_number, line in enumerate(lines, 1):
        if normalized_quote in _normalize(line):
            return f"line {line_number}"
    if normalized_quote in _normalize(content):
        return "document"
    return None


def _verified_evidence(items: object, sources: dict[str, ingest.SourceDocument]) -> list[dict[str, Any]]:
    verified: list[dict[str, Any]] = []
    if not isinstance(items, list):
        return verified
    for item in items:
        if not isinstance(item, dict):
            continue
        source = item.get("source")
        if not isinstance(source, dict):
            continue
        file = str(source.get("file") or "")
        quote = str(source.get("quote") or "")
        document = sources.get(file)
        locus = _locate(document.content, quote) if document else None
        if not document or not locus:
            continue
        verified.append({
            "text": str(item.get("text") or quote),
            "source": {"file": file, "locus": locus, "quote": quote},
        })
    return verified


def _decimal(value: object) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value).replace(",", ""))
    except InvalidOperation as exc:
        raise InvalidModelOutput(f"Invalid monetary value returned by GPT-5.6: {value}") from exc


def _confidence(value: object) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, result))


def _identifier(raw: object, index: int) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", str(raw or "")).strip("-")
    return cleaned or f"finding-{index}"


def _finding(raw: dict[str, Any], index: int,
             sources: dict[str, ingest.SourceDocument]) -> dict[str, Any] | None:
    inculpatory = _verified_evidence(raw.get("inculpatory"), sources)
    exculpatory = _verified_evidence(raw.get("exculpatory"), sources)
    if not inculpatory:
        return None
    status = str(raw.get("status") or "lead").lower()
    if status not in {"confirmed", "lead", "cleared"}:
        status = "lead"
    severity = str(raw.get("severity") or "low").lower()
    if severity not in {"high", "medium", "low", "observation"}:
        severity = "low"
    amount = _decimal(raw.get("amount_eur"))
    profit_effect = _decimal(raw.get("profit_effect_eur"))
    return {
        "id": _identifier(raw.get("id"), index),
        "scheme": str(raw.get("scheme") or "other"),
        "criterion": str(raw.get("criterion") or "GPT-5.6 evidence assessment"),
        "title": str(raw.get("title") or f"Finding {index}"),
        "amount_eur": float(amount),
        "currency": str(raw.get("currency") or ""),
        "profit_effect_eur": float(profit_effect),
        "status": status,
        "severity": severity,
        "confidence": _confidence(raw.get("confidence")),
        "verified": True,
        "verification_notes": [],
        "triage": raw.get("triage") if isinstance(raw.get("triage"), dict) else {},
        "inculpatory": inculpatory,
        "exculpatory": exculpatory,
        "narrative": str(raw.get("narrative") or ""),
    }


def _validate_synthesis(raw: dict[str, Any],
                        documents: list[ingest.SourceDocument]) -> tuple[list[dict], list[dict]]:
    sources = _source_index(documents)
    accepted: list[dict] = []
    for index, item in enumerate(raw.get("findings") or [], 1):
        if isinstance(item, dict):
            finding = _finding(item, index, sources)
            if finding:
                accepted.append(finding)
    cleared: list[dict] = []
    offset = len(accepted)
    for index, item in enumerate(raw.get("cleared_items") or [], offset + 1):
        if isinstance(item, dict):
            item = {**item, "status": "cleared"}
            finding = _finding(item, index, sources)
            if finding:
                cleared.append(finding)
    return accepted, cleared


def _write_json(path: str, payload: object) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, destination)


def run(
    cfg: config.Config,
    use_llm: bool = True,
    progress: Callable[[int, str], None] | None = None,
) -> dict[str, Any]:
    if not use_llm:
        raise llm.LLMUnavailable("Audit reports require GPT-5.6; offline generation is disabled")

    client = llm.AuditLLM(cfg)
    if progress:
        progress(10, "Reading uploaded evidence")
    documents = ingest.collect(cfg.data_dir)
    document_prompt = _prompt(cfg, "document_analysis.txt")
    synthesis_prompt = _prompt(cfg, "dossier_synthesis.txt")

    observations: list[dict[str, Any]] = []
    evidence_batches = ingest.batches(documents, cfg.batch_characters)
    if progress:
        progress(15, f"Submitting {len(evidence_batches)} GPT-5.6 evidence batches")

    def analyze_batch(batch_number: int, batch: list[dict[str, str]]) -> tuple[int, list[dict[str, Any]]]:
        result = client.json_response(
            purpose=f"evidence_batch_{batch_number}",
            instructions=document_prompt,
            payload={"batch": batch, "batch_number": batch_number, "batch_count": len(evidence_batches)},
        )
        items = result.get("observations")
        return batch_number, [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []

    completed: dict[int, list[dict[str, Any]]] = {}
    with ThreadPoolExecutor(max_workers=min(cfg.parallel_batches, len(evidence_batches))) as executor:
        futures = {
            executor.submit(analyze_batch, batch_number, batch): batch_number
            for batch_number, batch in enumerate(evidence_batches, 1)
        }
        for count, future in enumerate(as_completed(futures), 1):
            batch_number, items = future.result()
            completed[batch_number] = items
            if progress:
                percent = 15 + round(65 * count / max(1, len(evidence_batches)))
                progress(percent, f"GPT-5.6 evidence batches completed: {count} of {len(evidence_batches)}")
    for batch_number in sorted(completed):
        observations.extend(completed[batch_number])

    if progress:
        progress(85, "GPT-5.6 dossier synthesis")
    synthesis = client.json_response(
        purpose="dossier_synthesis",
        instructions=synthesis_prompt,
        payload={
            "evidence_manifest": ingest.evidence_manifest(documents),
            "verified_batch_observations": observations,
        },
    )
    findings, cleared = _validate_synthesis(synthesis, documents)
    if progress:
        progress(95, "Verifying source quotations and model attestation")
    engagement = synthesis.get("engagement") if isinstance(synthesis.get("engagement"), dict) else {}
    engagement_currency = str(engagement.get("currency") or "")
    for finding in findings + cleared:
        if not finding["currency"]:
            finding["currency"] = engagement_currency
    confirmed = [finding for finding in findings if finding["status"] == "confirmed"]
    leads = [finding for finding in findings if finding["status"] == "lead"]
    cleared.extend(finding for finding in findings if finding["status"] == "cleared")
    report_findings = confirmed + leads
    overstatement = sum(Decimal(str(item["profit_effect_eur"])) for item in confirmed)
    tolerance = _decimal(engagement.get("tolerable_misstatement_eur"))

    attestation = client.attestation()
    if not attestation["verified"]:
        raise llm.LLMUnavailable("GPT-5.6 attestation did not verify")
    report = {
        "dossier": str(Path(cfg.data_dir).resolve()),
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "model": cfg.model,
        "llm_used": True,
        "model_attestation": attestation,
        "pipeline": [
            "generic_ingestion",
            "gpt_5_6_evidence_analysis",
            "gpt_5_6_dossier_synthesis",
            "deterministic_quote_verification",
            "attested_json",
        ],
        "engagement": engagement,
        "summary": {
            "confirmed": len(confirmed),
            "leads": len(leads),
            "cleared": len(cleared),
            "all_verified": all(item["verified"] for item in report_findings),
            "profit_overstatement_eur": float(overstatement),
            "profit_overstatement_vs_tolerance": (
                "not_assessed" if tolerance <= 0 else "exceeds" if overstatement > tolerance else "within"
            ),
        },
        "findings": report_findings,
        "cleared_decoys": cleared,
    }
    _write_json(cfg.out_path, report)
    _write_json(cfg.db_path, {
        "manifest": ingest.evidence_manifest(documents),
        "observations": observations,
        "model_attestation": attestation,
    })
    return report
