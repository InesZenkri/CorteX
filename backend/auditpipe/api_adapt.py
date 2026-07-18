"""Adapt an attested audit report to the frontend API shapes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .config import EXPECTED_RESPONSE_MODEL, REQUIRED_MODEL


def _attested(report: object) -> bool:
    if not isinstance(report, dict) or report.get("llm_used") is not True:
        return False
    attestation = report.get("model_attestation")
    if not isinstance(attestation, dict) or attestation.get("verified") is not True:
        return False
    if attestation.get("requested_model") != REQUIRED_MODEL:
        return False
    calls = attestation.get("calls")
    if not isinstance(calls, list) or not calls:
        return False
    for call in calls:
        if not isinstance(call, dict) or call.get("requested_model") != REQUIRED_MODEL:
            return False
        returned = str(call.get("response_model") or "").lower()
        if not (
            returned == REQUIRED_MODEL
            or returned == EXPECTED_RESPONSE_MODEL
            or returned.startswith(f"{EXPECTED_RESPONSE_MODEL}-")
        ):
            return False
        if not str(call.get("response_id") or "").startswith("resp_"):
            return False
    return True


def _load_report(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return report if _attested(report) else None


def _doc_id(name: str) -> str:
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:20]
    return f"doc-{digest}"


def _citation(source: dict[str, Any], index: int) -> dict[str, Any]:
    file = str(source.get("file") or "")
    locus = str(source.get("locus") or "")
    page = 1
    if locus.lower().startswith("page "):
        try:
            page = max(1, int(locus.split()[-1]))
        except ValueError:
            pass
    return {
        "id": f"cit-{hashlib.sha256(f'{file}:{locus}:{index}'.encode()).hexdigest()[:16]}",
        "documentId": _doc_id(file),
        "documentName": file,
        "page": page,
        "quote": str(source.get("quote") or ""),
    }


def _evidence(raw: dict[str, Any]) -> list[dict[str, Any]]:
    items = list(raw.get("inculpatory") or []) + list(raw.get("exculpatory") or [])
    return [item for item in items if isinstance(item, dict) and isinstance(item.get("source"), dict)]


def _frontend_severity(value: object) -> str:
    severity = str(value or "low").lower()
    return severity if severity in {"critical", "high", "medium", "low"} else "low"


def _to_finding(raw: dict[str, Any], rank: int) -> dict[str, Any]:
    evidence = _evidence(raw)
    citations = [_citation(item["source"], index) for index, item in enumerate(evidence, 1)]
    status = str(raw.get("status") or "lead")
    confidence = float(raw.get("confidence") or 0)
    if confidence <= 1:
        confidence *= 100
    summary = "; ".join(str(item.get("text") or "") for item in evidence[:2])
    amount = float(raw.get("amount_eur") or 0)
    item = {
        "id": str(raw.get("id") or f"finding-{rank}"),
        "rank": rank,
        "title": str(raw.get("title") or "Audit finding"),
        "summary": summary or str(raw.get("narrative") or ""),
        "kind": "clean" if status == "cleared" else "finding",
        "severity": _frontend_severity(raw.get("severity")),
        "confidence": max(0, min(100, round(confidence))),
        "reviewStatus": (
            "confirmed" if status == "confirmed" else "rejected" if status == "cleared" else "needs_review"
        ),
        "sourceCount": len({citation["documentId"] for citation in citations}),
        "citations": citations,
    }
    if amount and citations:
        currency = str(raw.get("currency") or "XXX").upper()[:3]
        item["amount"] = {
            "amount": f"{amount:.2f}",
            "currency": currency,
            "originalText": f"{currency} {amount:,.2f}",
            "citation": citations[0],
        }
    return item


def _to_detail(raw: dict[str, Any], rank: int) -> dict[str, Any]:
    finding = _to_finding(raw, rank)
    inculpatory = [item for item in raw.get("inculpatory") or [] if isinstance(item, dict)]
    exculpatory = [item for item in raw.get("exculpatory") or [] if isinstance(item, dict)]
    contradictions = [
        {
            "id": f"con-{finding['id']}-{index}",
            "label": str((item.get("source") or {}).get("file") or "Evidence"),
            "statement": str(item.get("text") or ""),
            "citation": _citation(item.get("source") or {}, index),
        }
        for index, item in enumerate(inculpatory, 1)
    ]
    defenses = [
        {
            "explanation": str(item.get("text") or ""),
            "verdict": "plausible",
            "detail": str((item.get("source") or {}).get("quote") or ""),
        }
        for item in exculpatory
    ]
    return {
        **finding,
        "claim": str(raw.get("narrative") or raw.get("title") or ""),
        "checks": [
            {"label": str(item.get("text") or "Evidence")[:48], "result": "failed", "detail": str(item.get("text") or "")}
            for item in inculpatory
        ] + [
            {"label": str(item.get("text") or "Defense")[:48], "result": "passed", "detail": str(item.get("text") or "")}
            for item in exculpatory
        ],
        "contradictions": contradictions,
        "defenses": defenses,
    }


def all_raw(report: dict[str, Any]) -> list[dict[str, Any]]:
    return list(report.get("findings") or []) + list(report.get("cleared_decoys") or [])


def list_findings(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [_to_finding(item, index) for index, item in enumerate(all_raw(report), 1)]


def get_finding(report: dict[str, Any], finding_id: str) -> dict[str, Any] | None:
    for index, item in enumerate(all_raw(report), 1):
        if item.get("id") == finding_id:
            return _to_detail(item, index)
    return None


def dossier_summary(report: dict[str, Any] | None, document_count: int) -> dict[str, Any]:
    summary = report.get("summary", {}) if report else {}
    return {
        "health": 100 if not report else max(0, 100 - int(summary.get("confirmed") or 0)),
        "documents": document_count,
        "verifiedFindings": int(summary.get("confirmed") or 0),
        "reviewQueue": int(summary.get("leads") or 0),
        "unresolvedEntities": 0,
        "lastUpdated": str(report.get("generated_at") or "") if report else "",
    }


def investigation_summary(report: dict[str, Any] | None) -> dict[str, Any]:
    if not report:
        return {
            "status": "idle", "confirmed": 0, "leads": 0, "cleared": 0,
            "profit_overstatement_eur": 0.0,
            "profit_overstatement_vs_tolerance": "not_assessed",
            "schemes": {}, "findings": [], "llm_used": False,
        }
    summary = report.get("summary") or {}
    schemes: dict[str, float] = {}
    for finding in report.get("findings") or []:
        scheme = str(finding.get("scheme") or "other")
        schemes[scheme] = schemes.get(scheme, 0) + float(finding.get("amount_eur") or 0)
    return {
        "status": "ready",
        "confirmed": int(summary.get("confirmed") or 0),
        "leads": int(summary.get("leads") or 0),
        "cleared": int(summary.get("cleared") or 0),
        "profit_overstatement_eur": float(summary.get("profit_overstatement_eur") or 0),
        "profit_overstatement_vs_tolerance": str(summary.get("profit_overstatement_vs_tolerance") or "not_assessed"),
        "schemes": schemes,
        "findings": [
            {key: finding.get(key) for key in ("id", "scheme", "title", "amount_eur", "status")}
            for finding in report.get("findings") or []
        ],
        "generated_at": report.get("generated_at"),
        "llm_used": True,
        "model_attestation": report.get("model_attestation"),
    }


def build_graph(report: dict[str, Any] | None) -> dict[str, Any]:
    if not report:
        return {"nodes": [], "edges": []}
    raw_items = all_raw(report)
    entity_name = str((report.get("engagement") or {}).get("entity_name") or "Audited entity")
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in raw_items:
        grouped.setdefault(str(item.get("scheme") or "other"), []).append(item)
    first_source = next((e for item in raw_items for e in _evidence(item)), None)
    if not first_source:
        return {"nodes": [], "edges": []}
    root_citation = _citation(first_source["source"], 1)
    nodes.append({
        "id": "entity", "label": entity_name, "kind": "company", "subtitle": "Dossier subject",
        "risk": "watch", "sourceCount": 1,
        "findingIds": [str(item.get("id")) for item in report.get("findings") or []],
        "citations": [root_citation],
    })
    for index, (scheme, items) in enumerate(grouped.items(), 1):
        source = _evidence(items[0])[0]["source"]
        citation = _citation(source, index + 1)
        node_id = f"scheme-{hashlib.sha256(scheme.encode()).hexdigest()[:12]}"
        ids = [str(item.get("id")) for item in items]
        confirmed = any(item.get("status") == "confirmed" for item in items)
        nodes.append({
            "id": node_id, "label": scheme.replace("_", " ").title(), "kind": "account",
            "subtitle": f"{len(items)} item(s)", "risk": "alert" if confirmed else "watch",
            "sourceCount": len({_doc_id(str(e["source"].get("file") or "")) for item in items for e in _evidence(item)}),
            "findingIds": ids, "citations": [citation],
        })
        edges.append({
            "id": f"edge-{index}", "source": "entity", "target": node_id, "label": scheme,
            "risk": "alert" if confirmed else "watch", "explanation": str(items[0].get("narrative") or ""),
            "findingIds": ids, "citations": [citation],
        })
    return {"nodes": nodes, "edges": edges}


def list_documents(data_dir: Path) -> list[dict[str, Any]]:
    documents = []
    if not data_dir.exists():
        return documents
    for path in sorted(item for item in data_dir.rglob("*") if item.is_file() and item.name != ".DS_Store"):
        relative = path.relative_to(data_dir).as_posix()
        extension = path.suffix.lower().lstrip(".") or "file"
        documents.append({
            "id": _doc_id(relative), "name": relative, "type": extension.upper(), "language": "DE",
            "pages": 1, "status": "verified", "extractedFacts": 0,
            "previewLines": [relative, f"Type: {extension.upper()}", f"Size: {path.stat().st_size} bytes"],
        })
    return documents
