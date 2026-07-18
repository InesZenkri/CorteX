"""Adapt auditpipe findings.json into the CorteX frontend / OpenAPI shapes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DOSSIER_ID = "active"


def _load_report(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _doc_id(name: str) -> str:
    return "doc-" + "".join(ch if ch.isalnum() else "-" for ch in name.lower()).strip("-")


def _citation(file: str, locus: str, quote: str, idx: int) -> dict[str, Any]:
    return {
        "id": f"cit-{idx}",
        "documentId": _doc_id(file),
        "documentName": file,
        "page": 1,
        "quote": quote or locus or file,
    }


def _money(amount: float, citation: dict[str, Any]) -> dict[str, Any]:
    return {
        "amount": f"{amount:.2f}",
        "currency": "EUR",
        "originalText": f"EUR {amount:,.2f}",
        "citation": citation,
    }


def _severity(amount: float, severity: str) -> str:
    if severity == "high" or amount >= 100_000:
        return "critical" if amount >= 200_000 else "high"
    if severity == "observation" or amount < 25_000:
        return "medium" if amount >= 10_000 else "low"
    return "medium"


def _kind(status: str, severity: str) -> str:
    if status == "cleared":
        return "clean"
    if severity == "observation":
        return "observation"
    return "finding"


def _to_finding(raw: dict[str, Any], rank: int) -> dict[str, Any]:
    evidence = list(raw.get("inculpatory") or []) + list(raw.get("exculpatory") or [])
    citations = []
    for i, ev in enumerate(evidence, 1):
        src = ev.get("source") or {}
        citations.append(_citation(src.get("file", "unknown"), src.get("locus", ""), src.get("quote", ""), i))
    if not citations:
        citations.append(_citation("findings.json", raw.get("id", ""), raw.get("title", ""), 1))

    amount = float(raw.get("amount_eur") or 0)
    status = raw.get("status", "confirmed")
    conf = raw.get("confidence", 0)
    confidence = int(round(float(conf) * 100)) if float(conf) <= 1 else int(conf)

    summary_bits = [ev.get("text", "") for ev in (raw.get("inculpatory") or [])[:2]]
    summary = "; ".join(b for b in summary_bits if b) or raw.get("narrative") or raw.get("title", "")

    finding: dict[str, Any] = {
        "id": raw["id"],
        "rank": rank,
        "title": raw.get("title") or raw["id"],
        "summary": summary,
        "kind": _kind(status, raw.get("severity", "low")),
        "severity": _severity(amount, raw.get("severity", "low")),
        "confidence": max(0, min(100, confidence)),
        "reviewStatus": "confirmed" if status == "confirmed" else ("rejected" if status == "cleared" else "needs_review"),
        "sourceCount": len(evidence) or 1,
        "citations": citations,
    }
    if amount:
        finding["amount"] = _money(amount, citations[0])
    return finding


def _to_detail(raw: dict[str, Any], rank: int) -> dict[str, Any]:
    base = _to_finding(raw, rank)
    checks = []
    for ev in raw.get("inculpatory") or []:
        checks.append({"label": (ev.get("text") or "Signal")[:48], "result": "failed", "detail": ev.get("text", "")})
    for ev in raw.get("exculpatory") or []:
        checks.append({"label": (ev.get("text") or "Defense")[:48], "result": "passed", "detail": ev.get("text", "")})
    if not checks:
        checks.append({"label": "Pipeline gate", "result": "failed" if raw.get("status") == "confirmed" else "passed",
                       "detail": raw.get("title", "")})

    contradictions = []
    for i, ev in enumerate(raw.get("inculpatory") or [], 1):
        src = ev.get("source") or {}
        contradictions.append({
            "id": f"con-{raw['id']}-{i}",
            "label": src.get("file", "Evidence"),
            "statement": ev.get("text", ""),
            "citation": _citation(src.get("file", "unknown"), src.get("locus", ""), src.get("quote", ""), i),
        })

    defenses = []
    for ev in raw.get("exculpatory") or []:
        defenses.append({
            "explanation": ev.get("text", ""),
            "verdict": "plausible",
            "detail": (ev.get("source") or {}).get("quote", ""),
        })
    if not defenses and raw.get("status") == "confirmed":
        defenses.append({
            "explanation": "No exculpatory evidence found in the dossier.",
            "verdict": "refuted",
            "detail": "Deterministic gate promoted this candidate.",
        })

    return {
        **base,
        "claim": raw.get("narrative") or raw.get("title") or "",
        "checks": checks,
        "contradictions": contradictions,
        "defenses": defenses,
    }


def all_raw(report: dict[str, Any]) -> list[dict[str, Any]]:
    return list(report.get("findings") or []) + list(report.get("cleared_decoys") or [])


def list_findings(report: dict[str, Any]) -> list[dict[str, Any]]:
    items = all_raw(report)
    return [_to_finding(raw, i) for i, raw in enumerate(items, 1)]


def get_finding(report: dict[str, Any], finding_id: str) -> dict[str, Any] | None:
    for i, raw in enumerate(all_raw(report), 1):
        if raw.get("id") == finding_id:
            return _to_detail(raw, i)
    return None


def dossier_summary(report: dict[str, Any] | None, document_count: int) -> dict[str, Any]:
    if not report:
        return {
            "health": 100,
            "documents": document_count,
            "verifiedFindings": 0,
            "reviewQueue": 0,
            "unresolvedEntities": 0,
            "lastUpdated": "",
        }
    confirmed = int(report.get("summary", {}).get("confirmed") or 0)
    cleared = int(report.get("summary", {}).get("cleared") or 0)
    leads = int(report.get("summary", {}).get("leads") or 0)
    over = float(report.get("summary", {}).get("profit_overstatement_eur") or 0)
    health = max(0, min(100, int(100 - min(90, over / 5000))))
    return {
        "health": health,
        "documents": document_count,
        "verifiedFindings": confirmed,
        "reviewQueue": leads,
        "unresolvedEntities": cleared,
        "lastUpdated": report.get("generated_at", ""),
    }


def investigation_summary(report: dict[str, Any] | None) -> dict[str, Any]:
    if not report:
        return {
            "status": "idle",
            "confirmed": 0,
            "leads": 0,
            "cleared": 0,
            "profit_overstatement_eur": 0.0,
            "profit_overstatement_vs_tolerance": "within",
            "schemes": {},
            "findings": [],
        }
    schemes: dict[str, float] = {}
    for f in report.get("findings") or []:
        schemes[f.get("scheme", "other")] = schemes.get(f.get("scheme", "other"), 0) + float(f.get("amount_eur") or 0)
    return {
        "status": "ready",
        "confirmed": report["summary"]["confirmed"],
        "leads": report["summary"]["leads"],
        "cleared": report["summary"]["cleared"],
        "profit_overstatement_eur": report["summary"]["profit_overstatement_eur"],
        "profit_overstatement_vs_tolerance": report["summary"]["profit_overstatement_vs_tolerance"],
        "schemes": schemes,
        "findings": [
            {
                "id": f["id"],
                "scheme": f.get("scheme"),
                "title": f.get("title"),
                "amount_eur": f.get("amount_eur"),
                "status": f.get("status"),
            }
            for f in (report.get("findings") or [])
        ],
        "generated_at": report.get("generated_at"),
        "llm_used": report.get("llm_used", False),
    }


def build_graph(report: dict[str, Any] | None) -> dict[str, Any]:
    if not report:
        return {"nodes": [], "edges": []}

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    nodes.append({
        "id": "entity",
        "label": "Audited entity",
        "kind": "company",
        "subtitle": "Dossier subject",
        "risk": "watch",
        "sourceCount": 1,
        "findingIds": [f["id"] for f in report.get("findings") or []],
        "citations": [_citation("findings.json", "summary", "audit findings", 1)],
    })

    scheme_meta = {
        "fictitious_vendor": ("Fictitious vendor", "alert"),
        "capex_repair": ("Capitalized repairs", "alert"),
        "cutoff": ("Cut-off", "alert"),
        "structuring": ("Structuring", "alert"),
        "related_party": ("Related party", "watch"),
    }
    seen: set[str] = set()
    for f in all_raw(report):
        scheme = f.get("scheme", "other")
        if scheme not in seen:
            seen.add(scheme)
            label, risk = scheme_meta.get(scheme, (scheme, "watch"))
            ids = [x["id"] for x in all_raw(report) if x.get("scheme") == scheme]
            cit = _citation("findings.json", scheme, label, len(seen))
            nodes.append({
                "id": f"scheme-{scheme}",
                "label": label,
                "kind": "account",
                "subtitle": f"{len(ids)} item(s)",
                "risk": "clear" if f.get("status") == "cleared" and scheme not in {x.get("scheme") for x in report.get("findings") or []} else risk,
                "sourceCount": len(ids),
                "findingIds": ids,
                "citations": [cit],
            })
            edges.append({
                "id": f"e-{scheme}",
                "source": "entity",
                "target": f"scheme-{scheme}",
                "label": scheme,
                "risk": "alert" if any(x.get("status") == "confirmed" and x.get("scheme") == scheme for x in all_raw(report)) else "clear",
                "explanation": f"Detector {scheme} evaluated on this dossier.",
                "findingIds": ids,
                "citations": [cit],
            })
    return {"nodes": nodes, "edges": edges}


def list_documents(data_dir: Path) -> list[dict[str, Any]]:
    docs = []
    if not data_dir.exists():
        return docs
    for path in sorted(p for p in data_dir.rglob("*") if p.is_file() and p.name not in (".DS_Store",)):
        rel = path.relative_to(data_dir).as_posix()
        ext = path.suffix.lower().lstrip(".") or "file"
        docs.append({
            "id": _doc_id(rel),
            "name": rel,
            "type": ext.upper(),
            "language": "DE",
            "pages": 1,
            "status": "verified",
            "extractedFacts": 0,
            "previewLines": [rel, f"Type: {ext.upper()}", f"Size: {path.stat().st_size} bytes"],
        })
    return docs
