"""Holiday roll-forward for statutory time limits.

Ontario: Legislation Act, 2006 ss.88-89. Alberta: Interpretation Act ss.22, 28(1)(x).
We only roll for days we can name from the statute text: Sundays and the fixed or
formula holidays listed there. Proclamation-only days, Saturdays and closed
offices (s.89(2)/s.22(2)) are NOT modelled - see rules.UNVERIFIED.
"""
from __future__ import annotations

import datetime as dt
from typing import Set

_cache: dict = {}


def _easter(year: int) -> dt.date:
    """Gregorian Easter Sunday (anonymous Gregorian algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    ll = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ll) // 451
    month, day = divmod(h + ll - 7 * m + 114, 31)
    return dt.date(year, month, day + 1)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> dt.date:
    first = dt.date(year, month, 1)
    return first + dt.timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def _victoria_day(year: int) -> dt.date:
    """Monday preceding May 25."""
    d = dt.date(year, 5, 24)
    return d - dt.timedelta(days=d.weekday())


def _common(year: int) -> Set[dt.date]:
    easter = _easter(year)
    return {
        dt.date(year, 1, 1),
        _nth_weekday(year, 2, 0, 3),                 # Family Day: third Monday of February
        easter - dt.timedelta(days=2),               # Good Friday
        easter + dt.timedelta(days=1),               # Easter Monday
        _victoria_day(year),
        _nth_weekday(year, 9, 0, 1),                 # Labour Day
        dt.date(year, 11, 11),                       # Remembrance Day
        dt.date(year, 12, 25),
    }


def _ontario(year: int) -> Set[dt.date]:
    out = _common(year)
    out.add(_nth_weekday(year, 10, 0, 2))            # Thanksgiving: second Monday of October
    out.add(dt.date(year, 12, 26))                   # Boxing Day
    canada = dt.date(year, 7, 1)
    out.add(dt.date(year, 7, 2) if canada.weekday() == 6 else canada)   # s.88(4)
    if dt.date(year, 1, 1).weekday() == 6:
        out.add(dt.date(year, 1, 2))                 # s.88(3)
    xmas = dt.date(year, 12, 25).weekday()
    if xmas == 5:
        out.add(dt.date(year, 12, 27))               # s.88(5): Christmas on Saturday
    elif xmas == 6:
        out.add(dt.date(year, 12, 27))               # s.88(5): Christmas on Sunday -> Tuesday
    return out


def _alberta(year: int) -> Set[dt.date]:
    out = _common(year)
    out.add(dt.date(year, 7, 1))                     # Canada Day (Sunday case is already a Sunday)
    boxing = dt.date(year, 12, 26)
    out.add(dt.date(year, 12, 27) if boxing.weekday() in (6, 0) else boxing)  # s.28(1)(x)(iv)
    return out


def holidays(jurisdiction: str, year: int) -> Set[dt.date]:
    key = (jurisdiction, year)
    if key not in _cache:
        if jurisdiction == "ON":
            _cache[key] = _ontario(year)
        elif jurisdiction == "AB":
            _cache[key] = _alberta(year)
        else:
            raise ValueError(f"unknown jurisdiction {jurisdiction!r}")
    return _cache[key]


def is_holiday(jurisdiction: str, d: dt.date) -> bool:
    return d.weekday() == 6 or d in holidays(jurisdiction, d.year)


def roll_forward(jurisdiction: str, d: dt.date) -> dt.date:
    """Next day that is not a Sunday or listed holiday (d itself if it already is one)."""
    while is_holiday(jurisdiction, d):
        d += dt.timedelta(days=1)
    return d
