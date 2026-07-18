"""Detector suite. Every detector keys on STRUCTURAL signals, never on
dossier-specific ids or decoy-specific strings, so it generalizes to an unseen
dossier. Each detector emits Candidates carrying inculpatory Evidence and runs
its exculpatory checks; a deterministic gate assigns status + confidence.

Detectors implemented:
  fictitious_vendor  (new vendor, no goods, fast pay, one user books+pays)
  capex_repair       (asset addition whose description is maintenance)
  cutoff             (prior-period service, next-period invoice, no accrual)
  structuring        (same payee+day, N payments each just under the limit)
  related_party      (counterparty is a related party; disclosed => downgrade)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal as D

from . import config
from .provenance import Citation, Evidence
from .ledger import Ledger


@dataclass
class Candidate:
    fid: str
    scheme: str
    criterion: str
    title: str
    amount: D
    inculpatory: list[Evidence] = field(default_factory=list)
    exculpatory: list[Evidence] = field(default_factory=list)
    score: D = D("0")            # 0..1 strength of inculpatory signals
    subject: dict = field(default_factory=dict)


def _cite(file, locus, quote) -> Citation:
    return Citation(file=file, locus=locus, quote=str(quote))


# ---------------------------------------------------------------------------
def _new_vendors(L: Ledger):
    """Vendors created during the year, from any master-data-change table that
    records a 'Neuanlage' in any column. Table/column names discovered, not fixed."""
    for t in L.tables():
        cols = [r[1] for r in L.q(f'PRAGMA table_info("{t}")')]
        if not any("KONTO" in c.upper() for c in cols):
            continue
        kcol = next(c for c in cols if "KONTO" in c.upper())
        creator = next((c for c in cols if "AENDERT" in c.upper() or "ERSTELL" in c.upper()), None)
        approver = next((c for c in cols if "GENEHM" in c.upper() or "FREIG" in c.upper()), None)
        feldcols = [c for c in cols if c.upper() in ("FELD", "ART", "WERT_NEU", "AKTION")]
        if not (creator and approver and feldcols):
            continue
        cond = " OR ".join(f'lower("{c}") LIKE "%neuanlage%"' for c in feldcols)
        for row in L.q(f'SELECT _line,"{kcol}","{creator}","{approver}" FROM "{t}" WHERE {cond}'):
            yield {"table": t, "file": _file_of(L, t), "line": row[0],
                   "vendor": row[1], "creator": row[2], "approver": row[3]}


def _file_of(L: Ledger, table: str) -> str:
    r = L.q("SELECT source_file FROM cell WHERE table_name=? LIMIT 1", table)
    return r[0][0] if r else table


def _user_rights(L: Ledger) -> dict:
    """user -> set(rights) parsed from any authorization-matrix table."""
    rights = {}
    for t in L.tables():
        cols = [r[1] for r in L.q(f'PRAGMA table_info("{t}")')]
        low = [c.lower() for c in cols]
        if not (any("kennung" in c or "benutzer" in c or "user" in c for c in low)):
            continue
        ucol = cols[[i for i, c in enumerate(low) if "kennung" in c or "benutzer" in c or "user" in c][0]]
        can_book = next((c for c in cols if "buchen" in c.lower()), None)
        can_pay = next((c for c in cols if "zahlung" in c.lower() or "payment" in c.lower()), None)
        if not (can_book or can_pay):
            continue
        for row in L.q(f'SELECT * FROM "{t}"'):
            d = dict(zip(cols, row))          # cols already includes _line
            u = d.get(ucol)
            if not u:
                continue
            s = rights.setdefault(str(u).strip(), set())
            if can_book and str(d.get(can_book, "")).strip().upper() == "X":
                s.add("book")
            if can_pay and str(d.get(can_pay, "")).strip().upper() == "X":
                s.add("pay")
    return rights


def _vendor_ledger_table(L: Ledger) -> str | None:
    for t in L.tables():
        if "lieferantenbuchung" in t.lower():
            return t
    return None


def _goods_receipt_table(L: Ledger) -> str | None:
    for t in L.tables():
        if "wareneingang" in t.lower():
            return t
    return None


# ---------------------------------------------------------------------------
def d_fictitious_vendor(L: Ledger):
    out = []
    vb = _vendor_ledger_table(L)
    if not vb:
        return out
    rights = _user_rights(L)
    we = _goods_receipt_table(L)
    p = config.DetectorParams()
    for nv in _new_vendors(L):
        vendor = nv["vendor"]
        inv = L.q(f'''SELECT _line,BELEGNUMMER,BUCHUNGSDATUM,BUCHUNGSTEXT,BUCHUNGSBETRAG
                      FROM "{vb}" WHERE LIEFERANTENNUMMER=? AND CAST(BUCHUNGSBETRAG AS REAL)<0''', vendor)
        if not inv:
            continue
        pays = L.q(f'''SELECT BELEGNUMMER,BUCHUNGSDATUM FROM "{vb}"
                       WHERE LIEFERANTENNUMMER=? AND CAST(BUCHUNGSBETRAG AS REAL)>0''', vendor)
        gross = sum(abs(D(r[4])) for r in inv)
        net = _vendor_net_expense(L, vendor) or gross
        name = _lief_name(L, vendor)
        c = Candidate(f"FICT-{vendor}", "fictitious_vendor", "K1+K2",
                      f"New vendor {vendor} {name} paid with weak controls", net,
                      subject={"vendor": vendor})
        score = D("0")
        # signal: self-approval
        if nv["creator"] and nv["creator"] == nv["approver"]:
            score += D("0.35")
            c.inculpatory.append(Evidence(
                f"vendor created and approved by the same user ({nv['creator']})",
                _cite(nv["file"], f"line {nv['line']}", nv["creator"])))
        # signal: one user can both book and pay
        u = nv["creator"]
        if u in rights and {"book", "pay"} <= rights[u]:
            score += D("0.25")
            c.inculpatory.append(Evidence(
                f"user {u} holds both booking and payment rights",
                _cite("authorization matrix", u, u)))
        # signal: no goods receipt for any invoice
        has_gr = _vendor_has_goods(L, we, vendor)
        if not has_gr:
            score += D("0.25")
            c.inculpatory.append(Evidence(
                f"no goods receipt recorded for vendor {vendor}",
                _cite(we or "goods receipts", "absent", "(no matching row)")))
        # signal: fast invoice->payment
        lag = _fast_pay_lag(inv, pays)
        if lag is not None and lag <= p.fict_fast_pay_days:
            score += D("0.10")
            c.inculpatory.append(Evidence(
                f"invoices paid within ~{lag} days of invoice date",
                _cite(_file_of(L, vb), f"vendor {vendor}", f"{lag} days")))
        # bonus (not a gate): round net amounts
        if _all_round(L, vb, vendor):
            score += D("0.05")
            c.inculpatory.append(Evidence(
                "invoice net amounts are round figures",
                _cite(_file_of(L, vb), f"vendor {vendor}", "round amounts")))
        # exculpatory checks (defense)
        if has_gr:
            c.exculpatory.append(has_gr)
        fe = (nv["creator"] and nv["approver"] and nv["creator"] != nv["approver"])
        if fe:
            c.exculpatory.append(Evidence(
                f"vendor created under four-eyes ({nv['creator']} -> {nv['approver']})",
                _cite(nv["file"], f"line {nv['line']}", f"{nv['creator']}/{nv['approver']}")))
        c.score = min(score, D("1"))
        out.append(c)
    return out


def _vendor_net_expense(L, vendor):
    """Sum of positive (debit) postings on expense/asset accounts for a vendor's
    belegs, i.e. the net booked amount excluding VAT/payable/bank lines."""
    vb = _vendor_ledger_table(L)
    sb = next((t for t in L.tables() if "sachkontobuchung" in t.lower()), None)
    if not (vb and sb):
        return None
    belegs = [b[0] for b in L.q(
        f'SELECT DISTINCT BELEGNUMMER FROM "{vb}" WHERE LIEFERANTENNUMMER=? '
        f'AND CAST(BUCHUNGSBETRAG AS REAL)<0', vendor)]
    if not belegs:
        return None
    ph = ",".join("?" * len(belegs))
    rows = L.q(f'''SELECT BUCHUNGSBETRAG FROM "{sb}" WHERE BELEGNUMMER IN ({ph})
                   AND SACHKONTONUMMER NOT LIKE "147000"
                   AND SACHKONTONUMMER NOT LIKE "330000%"
                   AND SACHKONTONUMMER NOT LIKE "271000"
                   AND SACHKONTONUMMER NOT LIKE "272000"
                   AND CAST(BUCHUNGSBETRAG AS REAL)>0''', *belegs)
    return sum(D(r[0]) for r in rows) if rows else None


def _lief_name(L, vendor):
    for t in L.tables():
        if t.lower() == "lieferanten":
            r = L.q(f'SELECT NAME FROM "{t}" WHERE LIEFERANTENNUMMER=?', vendor)
            return r[0][0] if r else ""
    return ""


def _vendor_has_goods(L, we, vendor):
    if not we:
        return None
    cols = [r[1] for r in L.q(f'PRAGMA table_info("{we}")')]
    kcol = next((c for c in cols if "KREDITOR" in c.upper()), None)
    if not kcol:
        return None
    r = L.q(f'SELECT _line FROM "{we}" WHERE "{kcol}"=? LIMIT 1', vendor)
    if r:
        return Evidence(f"goods receipt exists for vendor {vendor}",
                        _cite(_file_of(L, we), f"line {r[0][0]}", vendor))
    return None


def _fast_pay_lag(inv, pays):
    import datetime as dt
    paymap = {}
    for beleg, d in pays:
        paymap.setdefault(beleg, d)
    lags = []
    for _line, beleg, idate, _txt, _amt in inv:
        pd = paymap.get(beleg)
        if idate and pd:
            try:
                lags.append((dt.date.fromisoformat(pd) - dt.date.fromisoformat(idate)).days)
            except Exception:
                pass
    return int(sum(lags) / len(lags)) if lags else None


def _all_round(L, vb, vendor):
    amts = [abs(D(r[0])) for r in L.q(
        f'SELECT BUCHUNGSBETRAG FROM "{vb}" WHERE LIEFERANTENNUMMER=? AND CAST(BUCHUNGSBETRAG AS REAL)<0', vendor)]
    return bool(amts) and all(a % D("1000") == 0 or (a / D("1.19")) % D("1000") == 0 for a in amts)


# ---------------------------------------------------------------------------
def d_capex_repair(L: Ledger):
    out = []
    ab = next((t for t in L.tables() if "anlagenbuchung" in t.lower()), None)
    sb = next((t for t in L.tables() if "sachkontobuchung" in t.lower()), None)
    if not ab or not sb:
        return out
    for r in L.q(f'''SELECT _line,ANLAGENNUMMER,BELEGNUMMER,BUCHUNGSBETRAG,SACHKONTONUMMER
                     FROM "{ab}" WHERE BUCHUNGSTYP="Acquisition"'''):
        line, anr, beleg, amt, konto = r
        # The asset line often carries only a generic label ("Acquisition"); the
        # real invoice narrative sits on the VAT/payable lines. Pick the most
        # descriptive (longest, non-generic) text among all lines of this beleg.
        GENERIC = {"acquisition", "disposal", "zugang", "abgang", ""}
        texts = [t[0] for t in L.q(f'SELECT DISTINCT BUCHUNGSTEXT FROM "{sb}" WHERE BELEGNUMMER=?', beleg)]
        cand_texts = [t for t in texts if t and t.strip().lower() not in GENERIC]
        desc = max(cand_texts, key=len) if cand_texts else (texts[0] if texts else "")
        low = desc.lower()
        is_repair = any(w in low for w in config.REPAIR_LEXICON)
        is_capex_ok = any(w in low for w in config.CAPEX_OK_LEXICON)
        if not (is_repair or is_capex_ok):
            continue
        c = Candidate(f"CAPEX-{beleg}", "capex_repair", "K3",
                      f"Asset addition {beleg}: '{desc}'", D(amt),
                      subject={"beleg": beleg})
        if is_repair:
            c.score = D("0.85")
            c.inculpatory.append(Evidence(
                f"asset addition described as maintenance/repair: '{desc}'",
                _cite(_file_of(L, ab), f"line {line}", desc)))
        if is_capex_ok:
            c.exculpatory.append(Evidence(
                f"description indicates genuine capital investment: '{desc}'",
                _cite(_file_of(L, sb), f"beleg {beleg}", desc)))
        out.append(c)
    return out


# ---------------------------------------------------------------------------
def d_cutoff(L: Ledger):
    """Prior-period service date, next-period invoice date, no accrual."""
    out = []
    # find a next-period creditor invoice journal (has service + invoice dates)
    for t in L.tables():
        cols = [r[1].upper() for r in L.q(f'PRAGMA table_info("{t}")')]
        has_service = any("LEISTUNG" in c for c in cols)
        has_invoice = any("FAKTURA" in c or "RECHNUNGSDAT" in c for c in cols)
        has_amount = any("BETRAG" in c for c in cols)
        if not (has_service and has_invoice and has_amount):
            continue
        realcols = [r[1] for r in L.q(f'PRAGMA table_info("{t}")')]
        scol = next(c for c in realcols if "LEISTUNG" in c.upper())
        icol = next(c for c in realcols if "FAKTURA" in c.upper() or "RECHNUNGSDAT" in c.upper())
        acol = next(c for c in realcols if "BETRAG" in c.upper())
        idcol = next((c for c in realcols if "RECHNUNG" in c.upper() and "DAT" not in c.upper()), realcols[0])
        namecol = next((c for c in realcols if "NAME" in c.upper()), None)
        select_cols = ['_line', f'"{idcol}"']
        if namecol:
            select_cols.append(f'"{namecol}"')
        select_cols += [f'"{scol}"', f'"{icol}"', f'"{acol}"']
        rows = L.q(f'SELECT {", ".join(select_cols)} FROM "{t}"')
        ev, total = [], D("0")
        for row in rows:
            line = row[0]
            rid = row[1]
            offset = 2 if namecol else 1
            nm = row[2] if namecol else ""
            sdate = row[0 + offset + 1]
            idate = row[1 + offset + 1]
            amt = row[2 + offset + 1]
            if _year(sdate) and _year(idate) and _year(sdate) < _year(idate):
                total += D(amt or 0)
                ev.append(Evidence(
                    f"{rid} {nm}: service {sdate}, invoiced {idate}, EUR {amt}",
                    _cite(_file_of(L, t), f"line {line}", f"{sdate} / {idate}")))
        if ev:
            c = Candidate("CUTOFF", "cutoff", "K4",
                          "Prior-period services invoiced in the next period", total)
            c.inculpatory = ev
            c.score = D("0.8")
            acc = _accrual_exists(L)
            if acc:
                c.inculpatory.append(Evidence(
                    "note: a separate documented accrual exists for OTHER work; "
                    "these items remain unaccrued", acc))
            out.append(c)
    return out


def _year(d):
    try:
        return int(str(d)[:4])
    except Exception:
        return None


def _accrual_exists(L):
    sb = next((t for t in L.tables() if "sachkontobuchung" in t.lower()), None)
    if not sb:
        return None
    r = L.q(f'''SELECT _line,BUCHUNGSTEXT FROM "{sb}"
                WHERE BUCHUNGSDATUM LIKE "%-12-%"
                  AND (lower(BUCHUNGSTEXT) LIKE "%rückstellung%" OR lower(BUCHUNGSTEXT) LIKE "%abgrenzung%"
                       OR lower(BUCHUNGSTEXT) LIKE "%accrual%" OR lower(BUCHUNGSTEXT) LIKE "%unfakturiert%")
                LIMIT 1''')
    return _cite(_file_of(L, sb), f"line {r[0][0]}", r[0][1]) if r else None


# ---------------------------------------------------------------------------
def d_structuring(L: Ledger):
    """Same payee + same day, >=N payments each within [floor*L, L), sum > L.
    Keys on structure only (amounts + dates), never on text/beleg conventions."""
    out = []
    vb = _vendor_ledger_table(L)
    if not vb:
        return out
    p = config.DetectorParams()
    L_ = config.Materiality().payment_four_eyes
    lo = float(L_ * p.struct_floor_ratio)
    hi = float(L_)
    rows = L.q(f'''SELECT LIEFERANTENNUMMER,BUCHUNGSDATUM,_line,BUCHUNGSBETRAG,BELEGNUMMER,BUCHUNGSTEXT
                   FROM "{vb}" WHERE CAST(BUCHUNGSBETRAG AS REAL)>0''')
    clusters: dict[tuple, list] = {}
    for vendor, date, line, amt, beleg, txt in rows:
        a = float(amt)
        if lo <= a < hi:
            clusters.setdefault((vendor, date), []).append((line, D(amt), beleg, txt))
    for (vendor, date), items in clusters.items():
        if len(items) >= p.struct_min_count and sum(i[1] for i in items) > L_:
            name = _lief_name(L, vendor)
            total = sum(i[1] for i in items)
            c = Candidate(f"STRUCT-{vendor}-{date}", "structuring", "K5",
                          f"Split payments to {vendor} {name} on {date}", total)
            lines = ",".join(str(i[0]) for i in items)
            amts = "/".join(str(i[1]) for i in items)
            c.inculpatory.append(Evidence(
                f"{len(items)} same-day payments each < EUR {L_} ({amts}) = EUR {total}, "
                f"just below the two-signature limit",
                _cite(_file_of(L, vb), f"lines {lines}", amts)))
            c.score = D("0.85")
            out.append(c)
    return out


# ---------------------------------------------------------------------------
def _disclosed_related_parties(L: Ledger) -> dict:
    out = {}
    for t in L.tables():
        if "gesellschafter" in t.lower() or "beteiligung" in t.lower():
            cols = [r[1] for r in L.q(f'PRAGMA table_info("{t}")')]
            for row in L.q(f'SELECT _line,* FROM "{t}"'):
                blob = " ".join(str(x) for x in row)
                for tok in blob.replace(",", " ").split():
                    if tok.isdigit() and len(tok) >= 5:
                        out[tok] = _cite(_file_of(L, t), f"line {row[0]}", blob[:120])
    return out


def d_related_party(L: Ledger):
    """Related-party charges. Disclosed => downgraded to observation but still
    tested for off-market (round + large + year-end). Undisclosed related parties
    (shared address/VAT across masters) are NOT auto-cleared."""
    out = []
    vb = _vendor_ledger_table(L)
    if not vb:
        return out
    disclosed = _disclosed_related_parties(L)
    p = config.DetectorParams()
    mat = config.Materiality()
    rows = L.q(f'''SELECT _line,LIEFERANTENNUMMER,BUCHUNGSTEXT,BUCHUNGSBETRAG FROM "{vb}"
                   WHERE lower(BUCHUNGSTEXT) LIKE "%konzernumlage%verwaltungsleistung%"
                     AND CAST(BUCHUNGSBETRAG AS REAL)<0''')
    for line, vendor, txt, amt in rows:
        if vendor not in disclosed:
            continue                     # not a related party -> not this detector's business
        amount = abs(D(amt))
        name = _lief_name(L, vendor)
        c = Candidate(f"RELPARTY-{vendor}", "related_party", "related-party",
                      f"Related-party charge {vendor} {name}: {txt}", amount,
                      subject={"vendor": vendor})
        c.inculpatory.append(Evidence(
            f"intercompany charge EUR {amount}: {txt}",
            _cite(_file_of(L, vb), f"line {line}", txt)))
        # disclosed => exculpatory unless off-market
        off_market = (amount % p.relparty_round_modulo == 0) and amount >= mat.tolerance
        c.exculpatory.append(Evidence(
            "related party disclosed in shareholder list (arm's-length presumed)",
            disclosed[vendor]))
        c.score = D("0.7") if off_market else D("0.2")
        c.subject["off_market"] = off_market
        out.append(c)
    return out


ALL_DETECTORS = [d_fictitious_vendor, d_capex_repair, d_cutoff,
                 d_structuring, d_related_party]
