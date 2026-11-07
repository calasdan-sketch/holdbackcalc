"""Minimal RFC 5545 calendar export - all-day events, one per dated deadline, no dependencies."""
from __future__ import annotations

import datetime as dt
import hashlib
from typing import Iterable, Optional, Tuple

from .calc import Deadline
from .textsafe import clean

DISCLAIMER = "Administrative reminder, not legal advice - verify with counsel."


def _esc(text: str) -> str:
    return (text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
                .replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n"))


def _fold(line: str) -> str:
    """Fold to <=75 octets per line (RFC 5545 3.1), never splitting a UTF-8 sequence."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    parts, cur = [], b""
    limit = 75
    for ch in line:
        b = ch.encode("utf-8")
        if len(cur) + len(b) > limit:
            parts.append(cur.decode("utf-8"))
            cur, limit = b"", 74          # continuation lines start with a space
        cur += b
    parts.append(cur.decode("utf-8"))
    return "\r\n ".join(parts)


def build_ics(items: Iterable[Tuple[str, str, Deadline]], stamp: Optional[dt.datetime] = None,
              alarm_days: Tuple[int, ...] = (7, 1)) -> str:
    """items: (project, command, deadline). Deadlines without a date are skipped."""
    stamp = stamp or dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//holdbackcalc//deadlines//EN",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH"]
    for project, command, d in items:
        if d.date is None:
            continue
        project = clean(project)
        uid = hashlib.sha256(f"{project}|{command}|{d.label}|{d.date}".encode()).hexdigest()[:24]
        title = f"{project}: {d.label}" if project else d.label
        if not d.hard:
            title = "Reminder - " + title
        desc = f"{d.basis} [{d.cite}]" if d.cite else d.basis
        if d.rolled:
            desc += f" May roll forward to {d.rolled.isoformat()} under the holiday rule - do not rely on it."
        desc += " " + DISCLAIMER
        lines += ["BEGIN:VEVENT", f"UID:{uid}@holdbackcalc", f"DTSTAMP:{stamp:%Y%m%dT%H%M%SZ}",
                  f"DTSTART;VALUE=DATE:{d.date:%Y%m%d}",
                  f"DTEND;VALUE=DATE:{d.date + dt.timedelta(days=1):%Y%m%d}",
                  f"SUMMARY:{_esc(title)}", f"DESCRIPTION:{_esc(desc)}", "TRANSP:TRANSPARENT"]
        if d.hard:
            for n in alarm_days:
                lines += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{_esc(title)}",
                          f"TRIGGER:-P{int(n)}D", "END:VALARM"]
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(ln) for ln in lines) + "\r\n"
