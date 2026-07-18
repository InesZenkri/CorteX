"""FastAPI service: upload dossier → run auditpipe → serve findings to the UI."""

from __future__ import annotations

import os
import logging
import shutil
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import api_adapt, config
from .pipeline import run as run_pipeline

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent.parent
RUNTIME_DIR = Path(os.getenv("CORTEX_RUNTIME_DIR", BACKEND_DIR / "runtime"))
DATA_DIR = RUNTIME_DIR / "data"
OUT_PATH = RUNTIME_DIR / "output" / "findings.json"
DB_PATH = RUNTIME_DIR / "output" / "evidence.json"

app = FastAPI(title="CorteX Evidence API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "CORTEX_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_lock = threading.Lock()
_state: dict[str, Any] = {
    "id": uuid.uuid4().hex,
    "name": "Active dossier",
    "company": "Uploaded engagement",
    "period": "",
    "status": "ready",
    "progress": 0,
    "error": None,
    "stage": "Ready",
    "file_count": 0,
}


class InvestigateRequest(BaseModel):
    use_llm: bool = Field(default=True)


def _count_files() -> int:
    if not DATA_DIR.exists():
        return 0
    return sum(1 for p in DATA_DIR.rglob("*") if p.is_file() and p.name != ".DS_Store")


def _report() -> dict[str, Any] | None:
    return api_adapt._load_report(OUT_PATH)


def _clear_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for child in DATA_DIR.iterdir():
        if child.name == ".gitkeep":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _safe_relpath(raw: str) -> Path:
    # Browser directory uploads include one selected-root segment.
    parts = Path(raw.replace("\\", "/")).parts
    if not parts:
        raise HTTPException(400, "Empty file path")
    rel_parts = parts[1:] if len(parts) > 1 else parts
    rel = Path(*rel_parts)
    if rel.is_absolute() or ".." in rel.parts:
        raise HTTPException(400, f"Invalid path: {raw}")
    return rel


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/dossiers")
def list_dossiers() -> list[dict[str, Any]]:
    return [{
        "id": _state["id"],
        "name": _state["name"],
        "company": _state["company"],
        "period": _state["period"],
        "status": _state["status"],
        "progress": _state["progress"],
    }]


@app.get("/api/investigation/summary")
def investigation_summary() -> dict[str, Any]:
    summary = api_adapt.investigation_summary(_report())
    summary["dossier_status"] = _state["status"]
    summary["progress"] = _state["progress"]
    summary["error"] = _state["error"]
    summary["stage"] = _state["stage"]
    summary["file_count"] = _state["file_count"] or _count_files()
    return summary


@app.post("/api/upload")
async def upload_dossier(files: list[UploadFile] = File(...)) -> dict[str, Any]:
    if _state["status"] == "processing":
        raise HTTPException(409, "Investigation already running")
    if not files:
        raise HTTPException(400, "No files uploaded")

    with _lock:
        _clear_data_dir()
        written = 0
        for upload in files:
            rel = _safe_relpath(upload.filename or "")
            dest = DATA_DIR / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            data = await upload.read()
            dest.write_bytes(data)
            written += 1

        # Drop previous results so UI doesn't show a stale run
        if OUT_PATH.exists():
            OUT_PATH.unlink()

        _state.update({
            "id": uuid.uuid4().hex,
            "name": (files[0].filename or "dossier").split("/")[0],
            "status": "ready",
            "progress": 0,
            "error": None,
            "stage": "Upload complete",
            "file_count": written,
            "period": "",
        })

    return {"ok": True, "files": written, "dossierId": _state["id"]}


def _run_job() -> None:
    try:
        _state["status"] = "processing"
        _state["progress"] = 15
        _state["error"] = None
        _state["stage"] = "Preparing GPT-5.6 investigation"
        cfg = config.Config(
            data_dir=str(DATA_DIR),
            out_path=str(OUT_PATH),
            db_path=str(DB_PATH),
        )
        def update_progress(percent: int, stage: str) -> None:
            _state["progress"] = percent
            _state["stage"] = stage

        report = run_pipeline(cfg, use_llm=True, progress=update_progress)
        _state["progress"] = 100
        _state["status"] = "ready"
        _state["stage"] = "Investigation complete"
        _state["period"] = report.get("generated_at", "")
    except Exception as exc:  # noqa: BLE001 — surface to UI
        logger.exception("GPT-5.6 investigation failed")
        _state["status"] = "failed"
        _state["progress"] = 0
        _state["error"] = str(exc)
        _state["stage"] = "Investigation failed"


@app.post("/api/investigate")
def investigate(body: InvestigateRequest | None = None) -> dict[str, Any]:
    if _count_files() == 0:
        raise HTTPException(400, "No dossier files in data/. Upload a folder first.")
    if _state["status"] == "processing":
        raise HTTPException(409, "Investigation already running")

    if body is not None and body.use_llm is not True:
        raise HTTPException(422, "GPT-5.6 processing is mandatory")
    with _lock:
        if _state["status"] == "processing":
            raise HTTPException(409, "Investigation already running")
        _state["status"] = "processing"
        _state["progress"] = 5
        _state["error"] = None
        _state["stage"] = "Starting background worker"
        if OUT_PATH.exists():
            OUT_PATH.unlink()
    thread = threading.Thread(target=_run_job, daemon=True)
    thread.start()
    return {"ok": True, "status": "processing", "dossierId": _state["id"]}


@app.get("/api/dossiers/{dossier_id}/summary")
def dossier_summary(dossier_id: str) -> dict[str, Any]:
    if dossier_id != _state["id"]:
        raise HTTPException(404, "Dossier not found")
    return api_adapt.dossier_summary(_report(), _count_files())


@app.get("/api/dossiers/{dossier_id}/findings")
def dossier_findings(dossier_id: str) -> list[dict[str, Any]]:
    if dossier_id != _state["id"]:
        raise HTTPException(404, "Dossier not found")
    report = _report()
    if not report:
        return []
    return api_adapt.list_findings(report)


@app.get("/api/dossiers/{dossier_id}/documents")
def dossier_documents(dossier_id: str) -> list[dict[str, Any]]:
    if dossier_id != _state["id"]:
        raise HTTPException(404, "Dossier not found")
    return api_adapt.list_documents(DATA_DIR)


@app.get("/api/dossiers/{dossier_id}/graph")
def dossier_graph(dossier_id: str) -> dict[str, Any]:
    if dossier_id != _state["id"]:
        raise HTTPException(404, "Dossier not found")
    return api_adapt.build_graph(_report())


@app.get("/api/findings/{finding_id}")
def finding_detail(finding_id: str) -> dict[str, Any]:
    report = _report()
    if not report:
        raise HTTPException(404, "No investigation results yet")
    detail = api_adapt.get_finding(report, finding_id)
    if not detail:
        raise HTTPException(404, "Finding not found")
    return detail


@app.patch("/api/findings/{finding_id}")
def review_finding(finding_id: str, body: dict[str, Any]) -> dict[str, Any]:
    report = _report()
    if not report:
        raise HTTPException(404, "No investigation results yet")
    detail = api_adapt.get_finding(report, finding_id)
    if not detail:
        raise HTTPException(404, "Finding not found")
    status = body.get("status")
    if status not in ("confirmed", "rejected", "needs_review"):
        raise HTTPException(422, "Invalid review status")
    detail["reviewStatus"] = status
    if "note" in body:
        detail["auditorNote"] = body["note"]
    return detail


@app.get("/api/documents/{document_id}")
def get_document(document_id: str) -> dict[str, Any]:
    for doc in api_adapt.list_documents(DATA_DIR):
        if doc["id"] == document_id:
            return doc
    raise HTTPException(404, "Document not found")


@app.get("/api/documents/{document_id}/file")
def get_document_file(document_id: str) -> FileResponse:
    for path in DATA_DIR.rglob("*"):
        if not path.is_file() or path.name == ".DS_Store":
            continue
        rel = path.relative_to(DATA_DIR).as_posix()
        if api_adapt._doc_id(rel) == document_id:
            return FileResponse(path, filename=path.name)
    raise HTTPException(404, "Document not found")


def main() -> None:
    import uvicorn
    uvicorn.run(
        "auditpipe.server:app",
        host=os.getenv("CORTEX_API_HOST", "127.0.0.1"),
        port=int(os.getenv("CORTEX_API_PORT", "8000")),
    )


if __name__ == "__main__":
    main()
