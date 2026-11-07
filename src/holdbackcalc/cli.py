"""holdbackcalc CLI: anchor date in, dated schedule out."""
from __future__ import annotations

import argparse
import contextlib
import csv
import datetime as dt
import json
import os
import sys
from typing import Optional

from . import __version__, batch as batchmod, calc
from .calc import SECTORS, Deadline, on_lien_events, weekday_name
from .ics import DISCLAIMER, build_ics
from .rules import APPLICABILITY, READ_ON, REGISTRY, SOURCES, UNVERIFIED
from .textsafe import clean

STALE_DAYS = 180
ISSUES_URL = "https://github.com/calasdan-sketch/holdbackcalc/issues"
NOTE = "administrative reminders, not legal advice"
JSON_SCHEMA_VERSION = 1      # bump only if an existing --json key is removed or changes meaning
EXIT_USAGE = 2              # bad input / user error (also argparse's own code)
EXIT_INTERNAL = 70          # a bug in holdbackcalc (EX_SOFTWARE)
EXIT_INTERRUPTED = 130


def _date(text: str) -> dt.date:
    try:
        return batchmod.parse_date(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc))


def _today_arg(text: str) -> dt.date:
    """--today accepts YYYY-MM-DD or the word `today` (the computer's local date)."""
    if text.strip().lower() == "today":
        return dt.date.today()
    return _date(text)


def _nonneg_int(text: str) -> int:
    try:
        n = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a whole number of days, got {clean(text, 30)!r}")
    if n < 0:
        raise argparse.ArgumentTypeError("must be 0 or more")
    return n


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


def _ascii_only() -> bool:
    enc = (getattr(sys.stdout, "encoding", None) or "utf-8").lower().replace("-", "")
    return enc not in ("utf8", "utf8sig")


def _csv_cell(text: str) -> str:
    """Neutralise spreadsheet formula injection (cells starting = + - @ tab CR)."""
    text = clean(str(text), 400)
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


def _stale_note(today: Optional[dt.date]) -> str:
    ref = today or dt.date.today()
    age = (ref - dt.date.fromisoformat(READ_ON)).days
    if age > STALE_DAYS:
        return (f"WARNING: the rules were last checked against the statutes on {READ_ON} ({age} days "
                "ago); amendments since then are not reflected. Run `holdbackcalc verify-sources`.")
    return ""


def _no_newline_translation() -> None:
    try:
        sys.stdout.reconfigure(newline="")  # type: ignore[union-attr]
    except (AttributeError, ValueError, OSError):
        pass


def _emit(items, args, cmd: str) -> int:
    """items: list of (project, command, Deadline)."""
    today = args.today
    if args.within is not None:
        if today is None:
            print("holdbackcalc: error: --within needs --today", file=sys.stderr)
            return EXIT_USAGE
        items = [t for t in items if t[2].date is not None and (t[2].date - today).days <= args.within
                 and (t[2].hard or t[2].date >= today)]
        if not items:
            print(f"Nothing due or overdue within {args.within} days of {today.isoformat()}.")
            return 0
    if args.csv:
        w = csv.writer(sys.stdout, lineterminator="\n")
        w.writerow(["project", "command", "label", "date", "weekday", "plan_by", "days_left", "hard", "cite", "basis"])
        for p, c, d in items:
            w.writerow([_csv_cell(p), c, _csv_cell(d.label), d.date.isoformat() if d.date else "",
                        weekday_name(d.date) if d.date else "", d.plan_by.isoformat() if d.plan_by else "",
                        (d.date - today).days if (d.date and today) else "", "yes" if d.hard else "no",
                        _csv_cell(d.cite), _csv_cell(d.basis)])
        return 0
    if args.ics:
        _no_newline_translation()      # the file already contains CRLF; Windows must not turn it into CR CR LF
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
        print(json.dumps({"schema_version": JSON_SCHEMA_VERSION, "tool_version": __version__,
                          "schedule": rows, "note": NOTE, "disclaimer": DISCLAIMER,
                          "applicability": [t for j in jurs for t in APPLICABILITY[j]],
                          "rules_read_on": READ_ON, "stale_warning": _stale_note(today) or None}, indent=2, ensure_ascii=_ascii_only()))
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
        wd = weekday_name(d.date) if d.date else "   "
        print(f"{prefix}{d.label:<{lw}}  {date_s:>10} {wd}  {st_s}{d.basis}{cite}")
        pad = f"{'':<{(pw + 2) if has_proj else 0}}    "
        if d.rolled:
            print(f"{pad}note: that day is a Sunday/holiday; the statute may allow "
                  f"{d.rolled.isoformat()} - plan to the earlier date")
        if d.plan_by:
            print(f"{pad}note: falls on a weekend/holiday - last business day to act is {d.plan_by.isoformat()} "
                  f"({weekday_name(d.plan_by)})")
        if d.closed_office:
            print(f"{pad}note: Saturday filing deadline - if the office where you file is closed, the time-limit "
                  "statute MAY extend it to the next open day (ON Legislation Act s.89(2); AB Interpretation "
                  "Act s.22(2)). Do not rely on that; file by the Friday.")
    if jurs:
        print("\nCheck scope before relying on this:")
        for j in jurs:
            for t in APPLICABILITY[j]:
                print(f"  - {t}")
    stale = _stale_note(today)
    if stale:
        print(f"\n{stale}")
    print("\nAdministrative reminders, not legal advice — verify anything that matters.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns 0 on success, 2 for bad input, 70 for an internal bug, 130 on Ctrl-C."""
    try:
        return _main(argv)
    except BrokenPipeError:
        # e.g. `holdbackcalc ... | head`: the reader went away. Not an error worth a traceback.
        try:
            if sys.__stdout__ is not None and sys.stdout is sys.__stdout__:
                os.dup2(os.open(os.devnull, os.O_WRONLY), sys.__stdout__.fileno())   # silence the exit-time flush
        except (OSError, ValueError, AttributeError):
            pass
        return 1
    except KeyboardInterrupt:
        print("holdbackcalc: interrupted", file=sys.stderr)
        return EXIT_INTERRUPTED
    except OSError as exc:
        print(f"holdbackcalc: error: cannot write the result: {clean(exc.strerror or str(exc), 120)}", file=sys.stderr)
        return EXIT_USAGE
    except Exception as exc:   # noqa: BLE001 - last resort: a plain message instead of a traceback
        if os.environ.get("HOLDBACKCALC_DEBUG"):
            raise
        print(f"holdbackcalc: internal error ({type(exc).__name__}). This is a bug; please report it at "
              f"{ISSUES_URL} (set HOLDBACKCALC_DEBUG=1 to see the details).", file=sys.stderr)
        return EXIT_INTERNAL


def _main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):      # legacy Windows consoles cannot print arrows/dashes
        try:
            stream.reconfigure(errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(
        prog="holdbackcalc",
        description="Prompt-payment/holdback/lien deadlines for AB & ON construction work "
                    "(verified rules only; NOT legal advice).",
    )
    ap.add_argument("--version", action="version", version=f"holdbackcalc {__version__}")
    fmt = ap.add_mutually_exclusive_group()
    fmt.add_argument("--json", action="store_true", help="machine-readable schedule")
    fmt.add_argument("--ics", action="store_true", help="print an iCalendar (.ics) file instead of a table")
    fmt.add_argument("--csv", action="store_true", help="spreadsheet-safe CSV (formula characters neutralised)")
    ap.add_argument("--out", metavar="FILE",
                    help="write the result to FILE as UTF-8 (use this instead of > on Windows PowerShell, "
                         "which would write UTF-16); refuses to overwrite an existing file")
    ap.add_argument("--within", type=_nonneg_int, metavar="N",
                    help="with --today: show only deadlines due in the next N days or already overdue")
    ap.add_argument("--today", type=_today_arg, metavar="DATE",
                    help="YYYY-MM-DD (or the word `today`): show days left / OVERDUE against this date")
    sub = ap.add_subparsers(dest="cmd", required=True, metavar="command")

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
    one.add_argument("--role", choices=("contractor", "other", "trustee"), required=True,
                     help="contractor; other (subcontractor/supplier); trustee (workers' trust fund lien)")
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
    ona.add_argument("--published", type=_date, help="date the owner actually published the annual-release notice")

    onf = sub.add_parser("on-annual-first", help="Ontario: first annual release for a contract date (s.87.4 transition)")
    onf.add_argument("contract_date", type=_date, help="date the contract was entered into")
    onf.add_argument("--published", type=_date, help="date the owner actually published the notice")

    onj = sub.add_parser("on-adjudication", help="Ontario: last day for a notice of adjudication")
    onj.add_argument("completed", type=_date, help="contract completed/abandoned/terminated")
    onj.add_argument("--also", type=_date, action="append",
                     help="subcontracts: subcontract-certified / last-supply dates (repeatable); earliest wins")

    bt = sub.add_parser("batch", help="many jobs from a CSV (columns: project,command,date[,certificate,registered,sector])")
    bt.add_argument("csv_path", metavar="csv", help="path to the CSV file, or - to read it from standard input")

    sub.add_parser("rules", help="list every encoded rule with its citation and source")

    vs = sub.add_parser("verify-sources", help="re-check every rule against the official statute text (needs network)")
    vs.add_argument("--from-dir", metavar="DIR", help="read pages you saved yourself (ON_ACT.html, AB_ACT.pdf ...) instead of downloading")

    sub.add_parser("what-we-dont-encode", help="list the rules deliberately left out as unverified")

    args = ap.parse_args(argv)
    if args.out:
        if os.path.exists(args.out):
            print(f"holdbackcalc: error: {clean(args.out, 80)} already exists; choose a new name", file=sys.stderr)
            return EXIT_USAGE
        try:
            fh = open(args.out, "x", encoding="utf-8", newline="")
        except OSError as exc:
            print(f"holdbackcalc: error: cannot write {clean(args.out, 80)}: {exc.strerror or exc}", file=sys.stderr)
            return EXIT_USAGE
        target, args.out = args.out, None
        rc = EXIT_INTERNAL
        try:
            with fh, contextlib.redirect_stdout(fh):
                rc = _dispatch(args)
        finally:
            if rc != 0:                 # never leave a half-written or empty result file behind
                try:
                    os.remove(target)
                except OSError:
                    pass
        return rc
    return _dispatch(args)


def _dispatch(args) -> int:
    if args.cmd == "verify-sources":
        from . import verify
        return verify.main(["--from-dir", args.from_dir] if args.from_dir else [])

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
                  "`holdbackcalc verify-sources` re-checks them.")
        return 0

    try:
        if args.cmd == "batch":
            rows = batchmod.read_rows(args.csv_path)
            items = [(p, c, d) for p, c, dl in rows for d in dl]
            items.sort(key=lambda t: (t[2].date is None, t[2].date or dt.date.max, t[0]))
            return _emit(items, args, "batch")
        if args.cmd == "on-lien-events":
            dl = on_lien_events(args.role, cert_published=args.cert_published, completed=args.completed,
                                last_supply=args.last_supply, subcontract_certified=args.subcontract_certified,
                                supply_before_sp=args.supply_before_sp, terminated=args.terminated)
        elif args.cmd == "on-annual":
            dl = calc.on_annual_holdback(args.anniversary, args.published)
        elif args.cmd == "on-annual-first":
            dl = calc.on_annual_from_contract(args.contract_date, args.published)
        else:
            first = {"ab-invoice": "received", "ab-sub-payment": "owner_paid", "ab-lien": "last_work",
                     "ab-holdback": "completed", "ab-adjudication": "final_payment", "on-lien": "trigger",
                     "on-holdback": "trigger", "on-invoice": "received", "on-prompt-payment": "received",
                     "on-sub-payment": "owner_paid",
                     "on-adjudication": "completed"}[args.cmd]
            dl = batchmod.run(args.cmd, getattr(args, first),
                              certificate=getattr(args, "certificate", None),
                              registered=getattr(args, "registered", None),
                              sector=getattr(args, "sector", "standard"),
                              also=getattr(args, "also", None))
    except (ValueError, batchmod.BatchError) as exc:
        print(f"holdbackcalc: error: {clean(str(exc), 300)}", file=sys.stderr)
        return EXIT_USAGE
    return _emit([("", args.cmd, d) for d in dl], args, args.cmd)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
