"""Format-agnostic dossier ingestion with source-preserving text extraction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceDocument:
    path: str
    content: str
    media_type: str


def _decode(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "iso-8859-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _spreadsheet_text(path: Path) -> str:
    from openpyxl import load_workbook

    workbook = load_workbook(path, read_only=True, data_only=True)
    lines: list[str] = []
    for sheet in workbook.worksheets:
        lines.append(f"[sheet: {sheet.title}]")
        for row in sheet.iter_rows(values_only=True):
            lines.append("\t".join("" if cell is None else str(cell) for cell in row))
    return "\n".join(lines)


def _pdf_text(path: Path) -> str:
    from pypdf import PdfReader

    lines: list[str] = []
    for page_number, page in enumerate(PdfReader(str(path)).pages, 1):
        lines.append(f"[page: {page_number}]")
        lines.append(page.extract_text() or "")
    return "\n".join(lines)


def _docx_text(path: Path) -> str:
    import docx

    document = docx.Document(str(path))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def _read(path: Path) -> tuple[str, str] | None:
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        return _spreadsheet_text(path), "spreadsheet"
    if suffix == ".pdf":
        return _pdf_text(path), "pdf"
    if suffix == ".docx":
        return _docx_text(path), "word-processing"
    if suffix in {".txt", ".csv", ".tsv", ".xml", ".json", ".md", ".log", ".dtd", ".yaml", ".yml"}:
        return _decode(path), suffix.lstrip(".") or "text"
    return None


def discover(data_dir: str) -> list[Path]:
    root = Path(data_dir)
    if not root.exists():
        raise FileNotFoundError(f"Dossier directory does not exist: {root}")
    return sorted(path for path in root.rglob("*") if path.is_file() and path.name != ".DS_Store")


def collect(data_dir: str) -> list[SourceDocument]:
    root = Path(data_dir)
    documents: list[SourceDocument] = []
    for path in discover(data_dir):
        extracted = _read(path)
        if extracted is None:
            continue
        content, media_type = extracted
        if content.strip():
            documents.append(SourceDocument(
                path=path.relative_to(root).as_posix(),
                content=content,
                media_type=media_type,
            ))
    if not documents:
        raise ValueError("The dossier contains no readable evidence documents")
    return documents


def batches(documents: list[SourceDocument], character_limit: int) -> list[list[dict[str, str]]]:
    result: list[list[dict[str, str]]] = []
    current: list[dict[str, str]] = []
    current_size = 0
    for document in documents:
        chunks = [
            document.content[offset:offset + character_limit]
            for offset in range(0, len(document.content), character_limit)
        ] or [""]
        for index, chunk in enumerate(chunks, 1):
            item = {
                "file": document.path,
                "media_type": document.media_type,
                "part": f"{index}/{len(chunks)}",
                "content": chunk,
            }
            size = len(chunk) + len(document.path)
            if current and current_size + size > character_limit:
                result.append(current)
                current = []
                current_size = 0
            current.append(item)
            current_size += size
    if current:
        result.append(current)
    return result


def evidence_manifest(documents: list[SourceDocument]) -> list[dict[str, object]]:
    return [
        {"file": document.path, "media_type": document.media_type, "characters": len(document.content)}
        for document in documents
    ]
