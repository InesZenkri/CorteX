"""End-to-end orchestration: ingest -> ledger -> detectors -> gate -> JSON."""

from __future__ import annotations
import datetime as dt
import json
from decimal import Decimal as D

from . import config, llm, ledger, detectors, gate
from .provenance import json_default


def run(cfg: config.Config, use_llm: bool = True) -> dict:
    client = None
    if use_llm and llm.available():
        try:
            client = llm.LLM(cfg.model)
        except llm.LLMUnavailable:
            client = None

    led = ledger.build(cfg, use_llm=use_llm)

    candidates = []
    for det in detectors.ALL_DETECTORS:
        candidates += det(led)

    findings = [gate.promote(c, cfg, client) for c in candidates]

    confirmed = [f for f in findings if f.status == "confirmed"]
    leads = [f for f in findings if f.status == "lead"]
    cleared = [f for f in findings if f.status == "cleared"]

    # profit-overstatement bridge: schemes that inflate reported profit
    overstate_schemes = {"capex_repair", "cutoff"}
    overstatement = sum((f.amount_eur for f in confirmed
                         if f.scheme in overstate_schemes), D("0"))

    report = {
        "dossier": cfg.data_dir,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "model": cfg.model,
        "llm_used": client is not None,
        "materiality": {
            "overall": float(cfg.materiality.overall),
            "tolerance": float(cfg.materiality.tolerance),
            "trivial": float(cfg.materiality.trivial),
            "payment_four_eyes": float(cfg.materiality.payment_four_eyes),
        },
        "summary": {
            "confirmed": len(confirmed),
            "leads": len(leads),
            "cleared": len(cleared),
            "profit_overstatement_eur": float(overstatement),
            "profit_overstatement_vs_tolerance": (
                "exceeds" if overstatement > cfg.materiality.tolerance else "within"),
        },
        "findings": [f.to_json() for f in
                     sorted(confirmed + leads, key=lambda x: -x.amount_eur)],
        "cleared_decoys": [f.to_json() for f in
                           sorted(cleared, key=lambda x: -x.amount_eur)],
    }

    import os
    os.makedirs(os.path.dirname(cfg.out_path) or ".", exist_ok=True)
    with open(cfg.out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False, default=json_default)
    led.close()
    return report
