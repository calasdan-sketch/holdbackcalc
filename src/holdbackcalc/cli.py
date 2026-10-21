"""holdbackcalc CLI: anchor date in, dated schedule out."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from typing import List

from . import __version__
from .calc import (
    Deadline,
    ab_invoice,
    ab_sub_payment,
    on_annual_holdback,
    on_holdback_release,
    on_invoice_deficiency,
    on_lien,
)
from .rules import SOURCES, UNVERIFIED


def _date(text: str) -> dt.date:
    try:
        return dt.date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected YYYY-MM-DD, got {text!r}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="holdbackcalc",
        description="Prompt-payment/holdback deadlines for AB & ON construction work "
                    "(verified rules only; not legal advice).",
    )
    ap.add_argument("--version", action="version", version=f"holdbackcalc {__version__}")
    ap.add_argument("--json", action="store_true", help="machine-readable schedule")
    sub = ap.add_subparsers(dest="cmd", required=True)

    abi = sub.add_parser("ab-invoice", help="Alberta: proper invoice received by the payer")
    abi.add_argument("received", type=_date)

    abp = sub.add_parser("ab-sub-payment", help="Alberta: owner's payment received by the contractor")
    abp.add_argument("owner_paid", type=_date)

    onl = sub.add_parser("on-lien", help="Ontario: lien clock from the trigger event")
    onl.add_argument("trigger", type=_date, help="e.g. publication of substantial performance")

    onh = sub.add_parser("on-holdback", help="Ontario: 10% holdback release schedule from an event")
    onh.add_argument("trigger", type=_date)

    oni = sub.add_parser("on-invoice", help="Ontario: proper-invoice deficiency window (2026 rules)")
    oni.add_argument("received", type=_date)

    ona = sub.add_parser("on-annual", help="Ontario: annual holdback release for >1yr contracts (2026 rules)")
    ona.add_argument("anniversary", type=_date)

    sub.add_parser("what-we-dont-encode", help="list the rules deliberately left out as unverified")

    args = ap.parse_args(argv)

    if args.cmd == "what-we-dont-encode":
        for line in UNVERIFIED:
            print(f"  - {line}")
        print("\nSources:")
        for name, url in SOURCES.items():
            print(f"  {name}: {url}")
        return 0

    table = {
        "ab-invoice": lambda: ab_invoice(args.received),
        "ab-sub-payment": lambda: ab_sub_payment(args.owner_paid),
        "on-lien": lambda: on_lien(args.trigger),
        "on-holdback": lambda: on_holdback_release(args.trigger),
        "on-invoice": lambda: on_invoice_deficiency(args.received),
        "on-annual": lambda: on_annual_holdback(args.anniversary),
    }[args.cmd]()

    if args.json:
        print(json.dumps({"schedule": [d.as_dict() for d in table],
                          "note": "administrative reminders, not legal advice"}, indent=2))
        return 0

    width = max(len(d.label) for d in table)
    for d in table:
        date_s = d.date.isoformat() if d.date else "—"
        print(f"{d.label:<{width}}  {date_s:>10}  {d.basis}")
    print("\nAdministrative reminders, not legal advice — verify anything that matters.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
