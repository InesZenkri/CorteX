"""CLI:  python -m auditpipe.run --data data --out output/findings.json"""

from __future__ import annotations
import argparse

from . import config
from .pipeline import run


def main():
    ap = argparse.ArgumentParser(description="AuditPipe forensic-audit pipeline (GPT-5.6)")
    ap.add_argument("--data", default="data", help="folder containing the dossier")
    ap.add_argument("--out", default="output/findings.json", help="output JSON path")
    ap.add_argument("--db", default="output/evidence.db", help="working SQLite path")
    ap.add_argument("--model", default=config.LLM_MODEL, help="LLM model (default gpt-5.6)")
    ap.add_argument("--no-llm", action="store_true",
                    help="deterministic parsers only (skip GPT-5.6)")
    args = ap.parse_args()

    cfg = config.Config(data_dir=args.data, out_path=args.out, db_path=args.db,
                        model=args.model)
    report = run(cfg, use_llm=not args.no_llm)
    s = report["summary"]
    print(f"model={report['model']} llm_used={report['llm_used']}")
    print(f"confirmed={s['confirmed']} leads={s['leads']} cleared={s['cleared']} "
          f"profit_overstatement=EUR {s['profit_overstatement_eur']:,.0f} "
          f"({s['profit_overstatement_vs_tolerance']} tolerance)")
    print(f"written: {args.out}")


if __name__ == "__main__":
    main()
