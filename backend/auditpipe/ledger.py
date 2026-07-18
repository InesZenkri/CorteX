"""Evidence ledger. Loads structured rows into per-table SQLite tables plus a
universal `cell` provenance table, and stores LLM document extracts in `doc` /
`doc_record`. Detectors query this single source of truth."""

from __future__ import annotations
import json
import sqlite3
from decimal import Decimal
from pathlib import Path

from . import config, ingest, llm


def _sqlval(v):
    if isinstance(v, Decimal):
        return str(v)
    if v is None or isinstance(v, (int, str)):
        return v
    return str(v)


class Ledger:
    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(db_path)
        self.con.execute("PRAGMA journal_mode=WAL")
        self._init()

    def _init(self):
        self.con.executescript("""
            DROP TABLE IF EXISTS cell;
            CREATE TABLE cell(table_name TEXT, source_file TEXT, line_no INT,
                              column_name TEXT, raw TEXT, value TEXT, role TEXT);
            CREATE INDEX ix_cell ON cell(table_name, line_no);
            DROP TABLE IF EXISTS doc;
            CREATE TABLE doc(file TEXT, doc_type TEXT);
            DROP TABLE IF EXISTS doc_record;
            CREATE TABLE doc_record(file TEXT, fields TEXT, quote TEXT);
        """)

    # -- structured -------------------------------------------------------
    def load_rows(self, rows: list[ingest.Row]):
        if not rows:
            return
        by_table: dict[str, list[ingest.Row]] = {}
        for r in rows:
            by_table.setdefault(r.table, []).append(r)
        cur = self.con.cursor()
        for table, rs in by_table.items():
            cols = list(rs[0].cells.keys())
            safe = table.replace('"', "")
            cur.execute(f'DROP TABLE IF EXISTS "{safe}"')
            coldef = ", ".join(f'"{c}"' for c in cols)
            cur.execute(f'CREATE TABLE "{safe}" (_line INT, {coldef})')
            ph = ", ".join("?" * (len(cols) + 1))
            data = [[r.line_no] + [_sqlval(r.val(c)) for c in cols] for r in rs]
            cur.executemany(f'INSERT INTO "{safe}" (_line, {coldef}) VALUES ({ph})', data)
            prov = [(r.table, r.source_file, r.line_no, cell.column, cell.raw,
                     _sqlval(cell.value), cell.role)
                    for r in rs for cell in r.cells.values()]
            cur.executemany("INSERT INTO cell VALUES (?,?,?,?,?,?,?)", prov)
        self.con.commit()

    # -- unstructured (LLM extracts) --------------------------------------
    def load_document(self, file: str, doc_type: str, records: list[dict]):
        cur = self.con.cursor()
        cur.execute("INSERT INTO doc VALUES (?,?)", (file, doc_type))
        cur.executemany("INSERT INTO doc_record VALUES (?,?,?)",
                        [(file, json.dumps(r.get("fields", {}), ensure_ascii=False),
                          r.get("quote", "")) for r in records])
        self.con.commit()

    def q(self, sql, *a):
        return self.con.cursor().execute(sql, a).fetchall()

    def tables(self) -> set[str]:
        return {r[0] for r in self.q("SELECT name FROM sqlite_master WHERE type='table'")}

    def close(self):
        self.con.close()


def build(cfg: config.Config, use_llm: bool) -> Ledger:
    led = Ledger(cfg.db_path)
    client = None
    if use_llm and llm.available():
        try:
            client = llm.LLM(cfg.model)
        except llm.LLMUnavailable:
            client = None

    for path in ingest.discover(cfg.data_dir):
        suf = path.suffix.lower()
        if path.name in ingest.GDPDU_SCHEMAS:
            led.load_rows(ingest.parse_gdpdu(path))
        elif suf == ".csv":
            led.load_rows(ingest.parse_csv(path))
        elif suf == ".xlsx":
            # load structurally (always) so detectors can query it without the LLM
            try:
                led.load_rows(ingest.parse_xlsx_structured(path))
            except Exception:
                pass
            text = ingest.read_xlsx_text(path)
            if client:
                try:
                    ex = client.extract_document(path.name, text)
                    led.load_document(path.name, ex.get("doc_type", "other"), ex.get("records", []))
                except llm.LLMUnavailable:
                    pass
        elif suf in (".pdf", ".docx"):
            text = ingest.read_pdf_text(path) if suf == ".pdf" else ingest.read_docx_text(path)
            if client and text.strip():
                try:
                    ex = client.extract_document(path.name, text)
                    led.load_document(path.name, ex.get("doc_type", "other"), ex.get("records", []))
                except llm.LLMUnavailable:
                    pass
    return led
