"""Deadline arithmetic tests — hand-computed expected dates, no circularity."""
import datetime as dt

from holdbackcalc.calc import (
    ab_invoice,
    ab_sub_payment,
    on_annual_holdback,
    on_holdback_release,
    on_invoice_deficiency,
    on_lien,
)
from holdbackcalc.rules import UNVERIFIED

D = dt.date


def by_label(deadlines, label):
    return next(d for d in deadlines if d.label == label)


def test_ab_invoice_hand_computed():
    table = ab_invoice(D(2026, 1, 1))
    assert by_label(table, "dispute notice by (owner)").date == D(2026, 1, 15)   # +14
    assert by_label(table, "payment due (owner → contractor)").date == D(2026, 1, 29)  # +28
    holdback = by_label(table, "unverified: holdback release")
    assert holdback.date is None and holdback.hard is False  # never fabricate the rule


def test_ab_sub_payment():
    table = ab_sub_payment(D(2026, 3, 2))
    assert by_label(table, "payment due (contractor → sub)").date == D(2026, 3, 9)  # +7


def test_on_lien_hand_computed():
    table = on_lien(D(2026, 1, 1))
    preserve = by_label(table, "preserve lien by")
    assert preserve.date == D(2026, 3, 2)      # +60
    perfect = by_label(table, "perfect lien by (commence action)")
    assert perfect.date == D(2026, 5, 31)      # preserve +90


def test_on_holdback_74_day_owner_payment():
    table = on_holdback_release(D(2026, 1, 1))
    assert by_label(table, "lien period expires").date == D(2026, 3, 2)     # +60 (Jan 1 + 60 = Mar 2)
    owner_pay = by_label(table, "owner must pay contractor (holdback)")
    assert owner_pay.date == D(2026, 3, 16)     # +74
    pass_down = by_label(table, "contractor passes down (if paid on the due date)")
    assert pass_down.date == D(2026, 3, 30)     # +88, marked as reminder


def test_on_invoice_deficiency_window():
    table = on_invoice_deficiency(D(2026, 6, 1))
    d = by_label(table, "deficiency notice window closes")
    assert d.date == D(2026, 6, 8) and d.days == 7


def test_on_annual_holdback_2026_rules():
    table = on_annual_holdback(D(2026, 1, 1))
    notice = by_label(table, "publish annual-release notice by")
    assert notice.date == D(2026, 1, 15)                 # anniversary +14
    earliest = by_label(table, "earliest payment of accrued holdback")
    latest = by_label(table, "latest payment of accrued holdback")
    assert earliest.date == D(2026, 3, 16)               # notice +60
    assert latest.date == D(2026, 3, 30)                 # notice +74
    assert earliest.date < latest.date


def test_unverified_list_is_nonempty_and_specific():
    assert len(UNVERIFIED) >= 4
    assert any(u.startswith("AB:") and "holdback" in u for u in UNVERIFIED)
    assert any("ON:" in u for u in UNVERIFIED)


def test_as_dict_roundtrip():
    d = ab_invoice(D(2026, 1, 1))[0].as_dict()
    assert d["date"] == "2026-01-15" and d["days"] == 14 and d["hard"] is True
