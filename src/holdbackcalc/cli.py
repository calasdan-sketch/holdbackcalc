"""holdbackcalc CLI: anchor date in, dated schedule out."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from typing import Optional

from . import __version__, batch as batchmod
from .calc import SECTORS, Deadline, on_lien_events
from .ics import DISCLAIMER, build_ics
from .rules import APPLICABILITY, READ_ON, REGISTRY, SOURCES, UNVERIFIED
from .textsafe import clean

NOTE = "administrative reminders, not legal advice"


def _date(text: str) -> dt.date:
    try:
        return batchmod.parse_date(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc))


def _sector(ap):
    ap.add_argument("--sector", choices=SECTORS, default="standard",
                    help="oil-gas (well/well-site improvements) and concrete work use 90-day periods")


def _status(d: Deadline, today: Optional[dt.date]) -> str:
    if today is None or d.date is None:
        return ""
    n = (d.date - today).days
    if n < 0:
        return f"OVERDUE {-n}d" if d.hard else f"past {-n}d"
    return "today" if n == 0 else f"in {n}d"


def _jur(cmd: str) -> Optional[str]:
    return "AB" if cmd.startswith("ab-") else "ON" if cmd.startswith("on-") else None


def _emit(items, args, cmd: str) -> int:
    """items: list of (project, command, Deadline)."""
    today = args.today
    if args.ics:
        sys.stdout.write(build_ics(items))
        return 0
    jurs = sorted({j for _p, c, _d in items if (j := _jur(c))})
    if args.json:
        rows = []
        for p, c, d in items:
            r = d.as_dict()
            if p:
                r["project"], r["command"] = p, c
            if today is not None:
                r["days_left"] = (d.date - today).days if d.date else None
            rows.append(r)
        print(json.dumps({"schedule": rows, "note": NOTE, "disclaimer": DISCLAIMER,
                          "applicability": [t for j in jurs for t in APPLICABILITY[j]],
                          "rules_read_on": READ_ON}, indent=2, ensure_ascii=False))
        return 0
    has_proj = any(p for p, _c, _d in items)
    lw = max(len(d.label) for _p, _c, d in items)
    pw = max((len(p) for p, _c, _d in items), default=0)
    for p, c, d in items:
        date_s = d.date.isoformat() if d.date else "—"
        st = _status(d, today)
        prefix = f"{p:<{pw}}  " if has_proj else ""
        st_s = f"{st:<12}  " if today is not None else ""
        cite = f"  [{d.cite}]" if d.cite else ""
        print(f"{prefix}{d.label:<{lw}}  {date_s:>10}  {st_s}{d.basis}{cite}")
        if d.rolled:
            print(f"{'':<{(pw + 2) if has_proj else 0}}    note: that day is a Sunday/holiday; the statute may allow "
                  f"{d.rolled.isoformat()} - plan to the earlier date")
    if jurs:
        print("\nCheck scope before relying on this:")
        for j in jurs:
            for t in APPLICABILITY[j]:
                print(f"  - {t}")
    print("\nAdministrative reminders, not legal advice — verify anything that matters.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="holdbackcalc",
        description="Prompt-payment/holdback/lien deadlines for AB & ON construction work "
                    "(verified rules only; NOT legal advice).",
    )
    ap.add_argument("--version", action="version", version=f"holdbackcalc {__version__}")
    ap.add_argument("--json", action="store_true", help="machine-readable schedule")
    ap.add_argument("--ics", action="store_true", help="print an iCalendar (.ics) file instead of a table")
    ap.add_argument("--today", type=_date, help="YYYY-MM-DD: show days left / OVERDUE against this date")
    sub = ap.add_subparsers(dest="cmd", required=True)

    abi = sub.add_parser("ab-invoice", help="Alberta: proper invoice received by the payer")
    abi.add_argument("received", type=_date)

    abp = sub.add_parser("ab-sub-payment", help="Alberta: owner's payment received by the contractor")
    abp.add_argument("owner_paid", type=_date)

    abl = sub.add_parser("ab-lien", help="Alberta: lien registration deadline (+ action deadline once registered)")
    abl.add_argument("last_work", type=_date, help="last materials/services, or completion/abandonment")
    abl.add_argument("--registered", type=_date, help="date the lien was registered (adds the 180-day deadline)")
    _sector(abl)

    abh = sub.add_parser("ab-holdback", help="Alberta: 10%% holdback retention / safe-payment dates")
    abh.add_argument("completed", type=_date, help="date the contract was completed")
    abh.add_argument("--certificate", type=_date, help="date the certificate of substantial performance was issued")
    _sector(abh)

    aba = sub.add_parser("ab-adjudication", help="Alberta: last day for a notice of adjudication")
    aba.add_argument("final_payment", type=_date, help="date of final payment (see PPCLA s.33.4(3))")

    onl = sub.add_parser("on-lien", help="Ontario: lien clock from ONE trigger event (simple)")
    onl.add_argument("trigger", type=_date, help="e.g. publication of substantial performance")

    one = sub.add_parser("on-lien-events", help="Ontario: s.31 lien expiry from the EARLIEST applicable event")
    one.add_argument("--role", choices=("contractor", "other"), required=True,
                     help="contractor, or other (subcontractor/supplier)")
    one.add_argument("--cert-published", type=_date, help="date the certificate of substantial performance was published")
    one.add_argument("--completed", type=_date, help="contract completed/abandoned/terminated")
    one.add_argument("--last-supply", type=_date, help="you last supplied services/materials (role other)")
    one.add_argument("--subcontract-certified", type=_date, help="subcontract certified complete (role other)")
    one.add_argument("--supply-before-sp", action="store_true",
                     help="your supply was on/before the certified substantial-performance date")
    one.add_argument("--terminated", type=_date, help="termination date (adds the 7-day notice reminder)")

    onh = sub.add_parser("on-holdback", help="Ontario: 10%% holdback release schedule from an event")
    onh.add_argument("trigger", type=_date)

    oni = sub.add_parser("on-invoice", help="Ontario: proper-invoice deficiency window (2026 rules)")
    oni.add_argument("received", type=_date)

    onp = sub.add_parser("on-prompt-payment", help="Ontario: full proper-invoice clock (7 / 14 / 28 / 35 days)")
    onp.add_argument("received", type=_date)

    ons = sub.add_parser("on-sub-payment", help="Ontario: owner's payment received by the contractor")
    ons.add_argument("owner_paid", type=_date)

    ona = sub.add_parser("on-annual", help="Ontario: annual holdback release for >1yr contracts (2026 rules)")
    ona.add_argument("anniversary", type=_date)

    onj = sub.add_parser("on-adjudication", help="Ontario: last day for a notice of adjudication")
    onj.add_argument("completed", type=_date, help="contract completed/abandoned/terminated")
    onj.add_argument("--also", type=_date, action="append",
                     help="subcontracts: subcontract-certified / last-supply dates (repeatable); earliest wins")

    bt = sub.add_parser("batch", help="many jobs from a CSV (columns: project,command,date[,certificate,registered,sector])")
    bt.add_argument("csv")

    sub.add_parser("rules", help="list every encoded rule with its citation and source")

    sub.add_parser("what-we-dont-encode", help="list the rules deliberately left out as unverified")

    args = ap.parse_args(argv)

    if args.cmd == "what-we-dont-encode":
        for line in UNVERIFIED:
            print(f"  - {line}")
        print("\nSources:")
        for name, url in SOURCES.items():
            print(f"  {name}: {url}")
        return 0

    if args.cmd == "rules":
        if args.json:
            print(json.dumps({"read_on": READ_ON, "rules": [r.as_dict() for r in REGISTRY],
                              "note": NOTE}, indent=2, ensure_ascii=False))
        else:
            for r in REGISTRY:
                print(f"{r.id:<42} {str(r.value):<30} {r.cite}")
            print(f"\n{len(REGISTRY)} rules, each checked against primary text on {READ_ON}; "
                  "`python tools/verify_sources.py` re-checks them.")
        return 0

    try:
        if args.cmd == "batch":
            rows = batchmod.read_rows(args.csv)
            items = [(p, c, d) for p, c, dl in rows for d in dl]
            items.sort(key=lambda t: (t[2].date is None, t[2].date or dt.date.max, t[0]))
            return _emit(items, args, "batch")
        if args.cmd == "on-lien-events":
            dl = on_lien_events(args.role, cert_published=args.cert_published, completed=args.completed,
                                last_supply=args.last_supply, subcontract_certified=args.subcontract_certified,
                                supply_before_sp=args.supply_before_sp, terminated=args.terminated)
        else:
            first = {"ab-invoice": "received", "ab-sub-payment": "owner_paid", "ab-lien": "last_work",
                     "ab-holdback": "completed", "ab-adjudication": "final_payment", "on-lien": "trigger",
                     "on-holdback": "trigger", "on-invoice": "received", "on-prompt-payment": "received",
                     "on-sub-payment": "owner_paid", "on-annual": "anniversary",
                     "on-adjudication": "completed"}[args.cmd]
            dl = batchmod.run(args.cmd, getattr(args, first),
                              certificate=getattr(args, "certificate", None),
                              registered=getattr(args, "registered", None),
                              sector=getattr(args, "sector", "standard"),
                              also=getattr(args, "also", None))
    except (ValueError, batchmod.BatchError) as exc:
        print(f"holdbackcalc: error: {clean(str(exc), 300)}", file=sys.stderr)
        return 2
    return _emit([("", args.cmd, d) for d in dl], args, args.cmd)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
