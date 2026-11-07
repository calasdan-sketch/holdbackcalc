"""Portfolio mode: many jobs in one CSV -> one merged, dated list (AR / project-admin view)."""
from __future__ import annotations

import csv
import datetime as dt
import io
import os
from typing import List, Optional, Tuple

from . import calc
from .calc import Deadline
from .textsafe import clean

MAX_BYTES = 5_000_000
MAX_ROWS = 10_000
MIN_YEAR, MAX_YEAR = 2000, 2100

COLUMNS = ("project", "command", "date", "certificate", "registered", "sector")


class BatchError(ValueError):
    pass


def parse_date(text: str, what: str = "date") -> dt.date:
    text = (text or "").strip()
    if len(text) != 10 or not text.isascii():
        raise ValueError(f"{what}: expected YYYY-MM-DD, got {clean(text, 40)!r}")
    try:
        d = dt.date.fromisoformat(text)
    except ValueError:
        raise ValueError(f"{what}: expected YYYY-MM-DD, got {clean(text, 40)!r}")
    if not MIN_YEAR <= d.year <= MAX_YEAR:
        raise ValueError(f"{what}: year must be {MIN_YEAR}-{MAX_YEAR}, got {d.year}")
    return d


def run(command: str, date: dt.date, *, certificate: Optional[dt.date] = None,
        registered: Optional[dt.date] = None, sector: str = "standard",
        also: Optional[List[dt.date]] = None) -> List[Deadline]:
    """Dispatch one command by name. Unknown names raise (fail closed)."""
    if command == "ab-invoice":
        return calc.ab_invoice(date)
    if command == "ab-sub-payment":
        return calc.ab_sub_payment(date)
    if command == "ab-lien":
        return calc.ab_lien(date, sector, registered)
    if command == "ab-holdback":
        return calc.ab_holdback(date, certificate, sector)
    if command == "ab-adjudication":
        return calc.ab_adjudication(date)
    if command == "on-lien":
        return calc.on_lien(date)
    if command == "on-holdback":
        return calc.on_holdback_release(date)
    if command == "on-invoice":
        return calc.on_invoice_deficiency(date)
    if command == "on-prompt-payment":
        return calc.on_prompt_payment(date)
    if command == "on-sub-payment":
        return calc.on_sub_payment(date)
    if command == "on-annual":
        return calc.on_annual_holdback(date)
    if command == "on-adjudication":
        return calc.on_adjudication(date, also)
    raise ValueError(f"unknown command {clean(command, 40)!r}")


BATCH_COMMANDS = ("ab-invoice", "ab-sub-payment", "ab-lien", "ab-holdback", "ab-adjudication",
                  "on-lien", "on-holdback", "on-invoice", "on-prompt-payment", "on-sub-payment",
                  "on-annual", "on-adjudication")


def read_rows(path: str) -> List[Tuple[str, str, List[Deadline]]]:
    """Parse + compute a CSV. ANY bad row aborts the whole run (no partial schedule)."""
    if not os.path.isfile(path):
        raise BatchError(f"not a regular file: {clean(path, 80)}")
    try:
        with open(path, "rb") as fh:
            raw = fh.read(MAX_BYTES + 1)
    except OSError as exc:
        raise BatchError(f"cannot read {clean(path, 80)}: {exc.strerror or exc}")
    if len(raw) > MAX_BYTES:
        raise BatchError(f"file larger than {MAX_BYTES} bytes")
    if b"\x00" in raw:
        raise BatchError("file contains NUL bytes")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise BatchError("file is not valid UTF-8")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    names = [(n or "").strip().lower() for n in (reader.fieldnames or [])]
    missing = [c for c in ("project", "command", "date") if c not in names]
    if missing:
        raise BatchError(f"header must include columns: project, command, date (missing: {', '.join(missing)})")
    unknown = [n for n in names if n not in COLUMNS]
    if unknown:
        raise BatchError(f"unknown column(s): {', '.join(clean(u, 30) for u in unknown)}")
    reader.fieldnames = names
    out: List[Tuple[str, str, List[Deadline]]] = []
    for n, row in enumerate(reader, start=2):
        if n - 1 > MAX_ROWS:
            raise BatchError(f"more than {MAX_ROWS} rows")
        if None in row:
            raise BatchError(f"line {n}: too many fields")
        row = {k: (v or "").strip() for k, v in row.items()}
        if not any(row.values()):
            continue
        try:
            cmd = row["command"]
            if cmd not in BATCH_COMMANDS:
                raise ValueError(f"command must be one of: {', '.join(BATCH_COMMANDS)}")
            date = parse_date(row["date"])
            cert = parse_date(row["certificate"], "certificate") if row.get("certificate") else None
            reg = parse_date(row["registered"], "registered") if row.get("registered") else None
            sector = row.get("sector") or "standard"
            dl = run(cmd, date, certificate=cert, registered=reg, sector=sector)
        except ValueError as exc:
            raise BatchError(f"line {n}: {exc}")
        out.append((clean(row["project"]) or "(unnamed)", cmd, dl))
    if not out:
        raise BatchError("no data rows")
    return out
