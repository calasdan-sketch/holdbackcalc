"""Deadline arithmetic — pure functions from an anchor date to dated reminders."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import List, Optional

from . import rules as R


@dataclass(frozen=True)
class Deadline:
    label: str
    date: Optional[dt.date]
    basis: str                 # the rule that produced it
    days: int                  # offset from the anchor (informational)
    hard: bool = True          # False = window/reminder rather than a hard date

    def as_dict(self):
        return {"label": self.label, "date": self.date.isoformat() if self.date else None,
                "basis": self.basis, "days": self.days, "hard": self.hard}


def _d(anchor: dt.date, days: int) -> dt.date:
    return anchor + dt.timedelta(days=days)


def ab_invoice(received: dt.date) -> List[Deadline]:
    """Alberta: proper invoice received by the payer."""
    return [
        Deadline("dispute notice by (owner)", _d(received, R.AB_DISPUTE_NOTICE_DAYS),
                 "owner must give notice of dispute within 14 calendar days of receipt", 14),
        Deadline("payment due (owner → contractor)", _d(received, R.AB_INVOICE_PAYMENT_DAYS),
                 "proper invoice payable within 28 calendar days", 28),
        Deadline("unverified: holdback release", None,
                 "NOT ENCODED — Alberta's statutory holdback %/release clock could not be "
                 "verified from official text; see README", 0, hard=False),
    ]


def ab_sub_payment(owner_paid: dt.date) -> List[Deadline]:
    """Alberta: contractor received the owner's payment — clock toward the sub runs."""
    return [
        Deadline("payment due (contractor → sub)", _d(owner_paid, R.AB_SUB_PAYMENT_DAYS),
                 "contractor pays the subcontractor within 7 calendar days after receiving "
                 "the owner's payment", 7),
    ]


def on_lien(last_supply: dt.date) -> List[Deadline]:
    """Ontario: lien clock from the trigger event (e.g. publication of substantial performance)."""
    preserve = _d(last_supply, R.ON_LIEN_PRESERVE_DAYS)
    return [
        Deadline("preserve lien by", preserve,
                 f"lien must be preserved within {R.ON_LIEN_PRESERVE_DAYS} days of the trigger event", 60),
        Deadline("perfect lien by (commence action)",
                 _d(preserve, R.ON_LIEN_PERFECT_DAYS),
                 f"{R.ON_LIEN_PERFECT_DAYS} days to commence the action, running from the last "
                 "day the lien could have been preserved", 150),
    ]


def on_holdback_release(event: dt.date) -> List[Deadline]:
    """Ontario: 10% holdback after the lien period around an event expires."""
    return [
        Deadline("lien period expires", _d(event, R.ON_LIEN_PRESERVE_DAYS),
                 f"{R.ON_LIEN_PRESERVE_DAYS}-day preservation period", 60),
        Deadline("owner must pay contractor (holdback)",
                 _d(event, R.ON_OWNER_PAYMENT_TOTAL_DAYS),
                 "lien period (60) + owner has 14 days to pay after expiry — up to 74 days "
                 "from the event with no preserved lien", 74),
        Deadline("contractor passes down (if paid on the due date)",
                 _d(_d(event, R.ON_OWNER_PAYMENT_TOTAL_DAYS), R.ON_PASS_DOWN_DAYS),
                 "14 days after receipt to pay downstream parties", 88, hard=False),
    ]


def on_invoice_deficiency(received: dt.date) -> List[Deadline]:
    """Ontario 2026: a proper invoice stays proper unless a deficiency notice lands in 7 days."""
    return [
        Deadline("deficiency notice window closes", _d(received, R.ON_INVOICE_DEFICIENCY_DAYS),
                 "invoice is deemed proper unless the owner gives written notice of deficiency "
                 "within 7 days", 7),
    ]


def on_annual_holdback(anniversary: dt.date) -> List[Deadline]:
    """Ontario 2026 (contracts entered on/after Jan 1, 2026): annual holdback release."""
    notice = _d(anniversary, R.ON_ANNUAL_NOTICE_DAYS)
    return [
        Deadline("publish annual-release notice by", notice,
                 "notice within 14 days of each contract anniversary", 14),
        Deadline("earliest payment of accrued holdback", _d(notice, R.ON_ANNUAL_PAYMENT_MIN_DAYS),
                 "no earlier than 60 days after publication", 74, hard=False),
        Deadline("latest payment of accrued holdback", _d(notice, R.ON_ANNUAL_PAYMENT_MAX_DAYS),
                 "no later than 74 days after publication, provided no lien is preserved", 88),
        Deadline("contractor passes down (from payment)", None,
                 "14 days after receipt — add to whichever payment date applies", 0, hard=False),
    ]
