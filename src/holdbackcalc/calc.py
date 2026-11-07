"""Deadline arithmetic — pure functions from anchor dates to dated reminders.

Day counting follows the statutes: the anchor day is excluded and the last day
is included (Ontario Legislation Act s.89(3); Alberta Interpretation Act s.22).
`Deadline.date` is the plain arithmetic date - plan to act on or before it.
`Deadline.rolled` is the later date the holiday rule *may* allow; never rely on it
without counsel (see holidays.py for exactly what is and is not modelled).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Dict, List, Optional

from . import rules as R
from .holidays import is_holiday, roll_forward

SECTORS = ("standard", "oil-gas", "concrete")
ROLES = ("contractor", "other", "trustee")


@dataclass(frozen=True)
class Deadline:
    label: str
    date: Optional[dt.date]
    basis: str                 # the rule that produced it
    days: int                  # offset from the anchor (informational)
    hard: bool = True          # False = window/reminder rather than a hard date
    cite: str = ""             # statute section the rule comes from
    rolled: Optional[dt.date] = None   # later date IF the holiday rule applies (else None)
    plan_by: Optional[dt.date] = None  # last business day on/before `date` when `date` is a weekend/holiday
    closed_office: bool = False        # filing deadline on a Saturday: office-closed extension MAY apply

    def as_dict(self):
        return {"label": self.label, "date": self.date.isoformat() if self.date else None,
                "basis": self.basis, "days": self.days, "hard": self.hard,
                "cite": self.cite,
                "rolled_forward_to": self.rolled.isoformat() if self.rolled else None,
                "weekday": self.date.strftime("%a") if self.date else None,
                "plan_by": self.plan_by.isoformat() if self.plan_by else None,
                "closed_office_note": self.closed_office}


def _d(anchor: dt.date, days: int) -> dt.date:
    return anchor + dt.timedelta(days=days)


def _mk(jur: str, label: str, date: Optional[dt.date], basis: str, days: int,
        hard: bool = True, cite: str = "", filing: bool = False) -> Deadline:
    """filing=True marks a registration/filing/notice-to-court style deadline, for which both
    provinces' time rules (ON Legislation Act s.89(2); AB Interpretation Act s.22(2)) may extend
    a deadline that falls on a day the office is closed."""
    rolled = plan_by = None
    closed = False
    if date is not None:
        wd = date.weekday()
        hol = wd == 6 or is_holiday(jur, date)
        if hol:
            rolled = roll_forward(jur, date)
        if wd >= 5 or hol:
            plan_by = date
            while plan_by.weekday() >= 5 or is_holiday(jur, plan_by):
                plan_by -= dt.timedelta(days=1)
        closed = filing and wd == 5 and not hol
    return Deadline(label, date, basis, days, hard, cite, rolled, plan_by, closed)


def _sector(sector: str) -> None:
    if sector not in SECTORS:
        raise ValueError(f"sector must be one of {SECTORS}, got {sector!r}")


def _ab_days(sector: str, standard: int, special: int) -> int:
    _sector(sector)
    return standard if sector == "standard" else special


# ----------------------------------------------------------------- Alberta

def ab_invoice(received: dt.date) -> List[Deadline]:
    """Alberta: proper invoice received by the payer."""
    return [
        _mk("AB", "dispute notice by (owner)", _d(received, R.AB_DISPUTE_NOTICE_DAYS),
            "owner must give notice of dispute within 14 calendar days of receipt", 14,
            cite="PPCLA s.32.2(2)"),
        _mk("AB", "payment due (owner → contractor)", _d(received, R.AB_INVOICE_PAYMENT_DAYS),
            "proper invoice payable within 28 calendar days", 28, cite="PPCLA s.32.2(1)"),
        _mk("AB", "contractor pays subs if owner has not paid", _d(received, R.AB_UNPAID_PASSTHROUGH_DAYS),
            "if the owner has not paid, the contractor must still pay subs within 35 days of giving "
            "the invoice, unless it sends the s.32.3(5)/(6) notices", 35, hard=False,
            cite="PPCLA s.32.3(4)"),
        Deadline("holdback release: use ab-holdback", None,
                 "holdback release runs from the certificate of substantial performance or "
                 "completion date, not the invoice date - run `ab-holdback`", 0, hard=False,
                 cite="PPCLA ss.18, 23, 27"),
    ]


def ab_sub_payment(owner_paid: dt.date) -> List[Deadline]:
    """Alberta: contractor received the owner's payment — clock toward the sub runs."""
    return [
        _mk("AB", "payment due (contractor → sub)", _d(owner_paid, R.AB_SUB_PAYMENT_DAYS),
            "contractor pays the subcontractor within 7 calendar days after receiving "
            "the owner's payment", 7, cite="PPCLA s.32.3(1)"),
    ]


def ab_lien(last_work: dt.date, sector: str = "standard",
            registered: Optional[dt.date] = None) -> List[Deadline]:
    """Alberta: register a lien (60 days; 90 for oil/gas wells and concrete), then sue (180 days)."""
    n = _ab_days(sector, R.AB_LIEN_REGISTER_DAYS, R.AB_LIEN_REGISTER_DAYS_SPECIAL)
    out = [_mk("AB", "register lien by", _d(last_work, n),
               f"register the lien within {n} days of the last materials/services supplied, or of "
               "completion or abandonment of the contract/subcontract", n, cite="PPCLA s.41", filing=True)]
    if registered is not None:
        out.append(_mk("AB", "commence action + register lis pendens by", _d(registered, R.AB_LIS_PENDENS_DAYS),
                       f"the registered lien ceases to exist unless an action is started and a "
                       f"certificate of lis pendens registered within {R.AB_LIS_PENDENS_DAYS} days of "
                       "registration", R.AB_LIS_PENDENS_DAYS, cite="PPCLA s.43(1)", filing=True))
    else:
        out.append(Deadline("commence action + register lis pendens by", None,
                            f"{R.AB_LIS_PENDENS_DAYS} days after the date the lien is REGISTERED - "
                            "pass --registered DATE to compute", 0, hard=False, cite="PPCLA s.43(1)"))
    return out


def ab_holdback(completed: dt.date, certificate: Optional[dt.date] = None,
                sector: str = "standard") -> List[Deadline]:
    """Alberta: 10% holdback retention and earliest safe payment (major / minor lien fund)."""
    n = _ab_days(sector, R.AB_HOLDBACK_DAYS, R.AB_HOLDBACK_DAYS_SPECIAL)
    out: List[Deadline] = []
    if certificate is not None:
        out.append(_mk("AB", "major lien fund: retention/safe-payment date", _d(certificate, n),
                       f"10% retained for {n} days from the certificate of substantial performance; "
                       "payment may validly be made after that if no lien is registered", n,
                       cite="PPCLA ss.18(1), 27(2)(a)"))
        out.append(_mk("AB", "minor lien fund: retention/safe-payment date", _d(completed, n),
                       f"10% of post-certificate work retained for {n} days from completion", n,
                       cite="PPCLA ss.23(1), 27(2)(b)"))
    else:
        out.append(_mk("AB", "major lien fund: retention/safe-payment date", _d(completed, n),
                       f"no certificate issued: 10% retained for {n} days from completion", n,
                       cite="PPCLA ss.18(1)(b), 27(1)"))
    out.append(Deadline("annual/phased holdback payment", None,
                        "an owner MUST pay holdback early only if the contract provides annual/phased "
                        "payment, the price exceeds $10,000,000, and no liens are filed - not computed",
                        0, hard=False, cite="PPCLA s.24.1; Alta Reg 23/2022 s.2"))
    return out


def ab_adjudication(final_payment: dt.date) -> List[Deadline]:
    """Alberta: last day to give a notice of adjudication."""
    return [_mk("AB", "notice of adjudication by", _d(final_payment, R.AB_ADJUDICATION_DAYS),
                "no adjudication if notice is given more than 30 days after the date of final payment "
                "(unless the parties agree otherwise)", R.AB_ADJUDICATION_DAYS, cite="PPCLA s.33.4(2)", filing=True)]


# ----------------------------------------------------------------- Ontario

def on_lien(last_supply: dt.date) -> List[Deadline]:
    """Ontario: lien clock from ONE trigger event (see on_lien_events for the real s.31 test)."""
    preserve = _d(last_supply, R.ON_LIEN_PRESERVE_DAYS)
    return [
        _mk("ON", "preserve lien by", preserve,
            f"lien must be preserved within {R.ON_LIEN_PRESERVE_DAYS} days of the trigger event", 60,
            cite="Construction Act s.31", filing=True),
        _mk("ON", "perfect lien by (commence action)",
            _d(preserve, R.ON_LIEN_PERFECT_DAYS),
            f"{R.ON_LIEN_PERFECT_DAYS} days to commence the action, running from the last "
            "day the lien could have been preserved; ONLY if the lien was actually preserved "
            "first (s.36(1)) - a missed preservation date cannot be cured by this one",
            150, cite="Construction Act s.36(2)", filing=True),
    ]


def on_lien_events(role: str, *, cert_published: Optional[dt.date] = None,
                   completed: Optional[dt.date] = None, last_supply: Optional[dt.date] = None,
                   subcontract_certified: Optional[dt.date] = None,
                   supply_before_sp: bool = False,
                   terminated: Optional[dt.date] = None) -> List[Deadline]:
    """Ontario s.31: lien expiry is 60 days after the EARLIEST of the events that apply to you.

    role "contractor": cert publication (only for supply on/before the SP date) and
        completion/abandonment/termination.
    role "other" (sub, supplier...): also last supply and subcontract certified complete.
    role "trustee" (workers' trust fund lien, s.31(2.1)): same events; pass the date the final
        worker who is a beneficiary of the fund last supplied services as `last_supply`.
    supply_before_sp: True when the supply was on/before the certified date of substantial
        performance (s.31(2)(a)/(3)(a)); False for no certificate or later supply ((b)).
    """
    if role not in ROLES:
        raise ValueError(f"role must be one of {ROLES}, got {role!r}")
    cands: Dict[str, Optional[dt.date]] = {}
    if supply_before_sp:
        cands["certificate of substantial performance published"] = cert_published
    cands["contract completed/abandoned/terminated"] = completed
    if role in ("other", "trustee"):
        cands["you last supplied services/materials"] = last_supply
        cands["subcontract certified complete"] = subcontract_certified
    present = {k: v for k, v in cands.items() if v is not None}
    if not present:
        raise ValueError("no applicable trigger event supplied for this role/phase")
    which = min(present, key=lambda k: (present[k], k))
    event = present[which]
    preserve = _d(event, R.ON_LIEN_PRESERVE_DAYS)
    cite = {"contractor": "Construction Act s.31(2)", "other": "Construction Act s.31(3)",
            "trustee": "Construction Act s.31(2.1)"}[role]
    out = [
        _mk("ON", "preserve lien by", preserve,
            f"60 days after the earliest applicable event: {which} ({event.isoformat()})", 60, cite=cite,
            filing=True),
        _mk("ON", "perfect lien by (commence action)", _d(preserve, R.ON_LIEN_PERFECT_DAYS),
            "90 days after the last day the lien could have been preserved; ONLY if the lien was "
            "actually preserved first (s.36(1)); a preserved lien may instead be perfected by "
            "sheltering under another claimant's action (s.36(4))", 150,
            cite="Construction Act s.36(2)", filing=True),
    ]
    if terminated is not None:
        out.append(_mk("ON", "publish notice of termination by", _d(terminated, R.ON_TERMINATION_NOTICE_DAYS),
                       "owner or contractor must publish a notice of termination within 7 days; "
                       "the termination date for s.31 is the date the first notice is published",
                       R.ON_TERMINATION_NOTICE_DAYS, cite="Construction Act s.31(6),(7)"))
    missing = [k for k in cands if cands[k] is None]
    if missing:
        out.append(Deadline("events not supplied (could make it EARLIER)", None,
                            "; ".join(missing), 0, hard=False, cite=cite))
    return out


def on_holdback_release(event: dt.date) -> List[Deadline]:
    """Ontario: 10% holdback after the lien period around an event expires."""
    return [
        _mk("ON", "lien period expires", _d(event, R.ON_LIEN_PRESERVE_DAYS),
            f"{R.ON_LIEN_PRESERVE_DAYS}-day preservation period", 60, cite="Construction Act s.31"),
        _mk("ON", "owner must pay contractor (holdback)",
            _d(event, R.ON_OWNER_PAYMENT_TOTAL_DAYS),
            "lien period (60) + owner has 14 days to pay after expiry — up to 74 days "
            "from the event with no preserved lien", 74, cite="Construction Act s.26(8)"),
        _mk("ON", "contractor passes down (if paid on the due date)",
            _d(_d(event, R.ON_OWNER_PAYMENT_TOTAL_DAYS), R.ON_PASS_DOWN_DAYS),
            "14 days after receipt to pay downstream parties", 88, hard=False,
            cite="Construction Act s.26(8)"),
    ]


def on_invoice_deficiency(received: dt.date) -> List[Deadline]:
    """Ontario 2026: a proper invoice stays proper unless a deficiency notice lands in 7 days."""
    return [
        _mk("ON", "deficiency notice window closes", _d(received, R.ON_INVOICE_DEFICIENCY_DAYS),
            "invoice is deemed proper unless the owner gives written notice of deficiency "
            "within 7 days", 7, cite="Construction Act s.6.1(2)"),
    ]


def on_prompt_payment(received: dt.date) -> List[Deadline]:
    """Ontario: the full proper-invoice clock (deficiency 7, non-payment notice 14, payment 28)."""
    return on_invoice_deficiency(received) + [
        _mk("ON", "owner's notice of non-payment by", _d(received, R.ON_NOTICE_NONPAYMENT_DAYS),
            "owner may withhold only if it gives the prescribed notice of non-payment within 14 days",
            14, cite="Construction Act s.6.4(2)"),
        _mk("ON", "payment due (owner → contractor)", _d(received, R.ON_INVOICE_PAYMENT_DAYS),
            "proper invoice payable within 28 days", 28, cite="Construction Act s.6.4(1)"),
        _mk("ON", "contractor pays subs if owner has not paid", _d(received, R.ON_UNPAID_PASSTHROUGH_DAYS),
            "if the owner has not paid, the contractor must still pay subs within 35 days of giving "
            "the invoice, unless it sends the s.6.5(5)/(6) notices", 35, hard=False,
            cite="Construction Act s.6.5(4)"),
    ]


def on_sub_payment(owner_paid: dt.date) -> List[Deadline]:
    """Ontario: contractor received the owner's payment — 7 days to pay subs."""
    return [_mk("ON", "payment due (contractor → sub)", _d(owner_paid, R.ON_SUB_PAYMENT_DAYS),
                "contractor pays each subcontractor within 7 days after receiving payment", 7,
                cite="Construction Act s.6.5(1)")]


def on_annual_holdback(anniversary: dt.date, published: Optional[dt.date] = None) -> List[Deadline]:
    """Ontario 2026: annual holdback release (s.26(2)-(5)).

    The payment window runs from the date the owner ACTUALLY publishes the notice (s.26(4)).
    Without `published` we can only show the outer bounds that follow if the notice goes out on
    the last permitted day (anniversary + 14); an earlier notice moves both dates earlier.
    """
    last_notice = _d(anniversary, R.ON_ANNUAL_NOTICE_DAYS)
    out = [_mk("ON", "publish annual-release notice by", last_notice,
               "notice within 14 days of each contract anniversary", 14, cite="Construction Act s.26(3)")]
    if published is None:
        out += [
            _mk("ON", "payment window opens (if notice is published on its last day)",
                _d(last_notice, R.ON_ANNUAL_PAYMENT_MIN_DAYS),
                "payment no earlier than 60 days after the notice is published; an earlier notice "
                "means an earlier date - pass --published DATE for the exact window", 74, hard=False,
                cite="Construction Act s.26(4)"),
            _mk("ON", "latest possible payment (if notice is published on its last day)",
                _d(last_notice, R.ON_ANNUAL_PAYMENT_MAX_DAYS),
                "payment no later than 74 days after the notice is published, unless a lien is "
                "preserved/perfected; an earlier notice means an earlier date", 88,
                cite="Construction Act s.26(4)"),
        ]
    else:
        late = published > last_notice
        out += [
            Deadline("notice actually published", published,
                     "you reported this date" + ("; it is AFTER the 14-day limit in s.26(3) - "
                                                  "ask counsel what follows" if late else ""),
                     (published - anniversary).days, hard=False, cite="Construction Act s.26(3)"),
            _mk("ON", "payment window opens", _d(published, R.ON_ANNUAL_PAYMENT_MIN_DAYS),
                "no earlier than 60 days after publication", 60, hard=False, cite="Construction Act s.26(4)"),
            _mk("ON", "latest payment of accrued holdback", _d(published, R.ON_ANNUAL_PAYMENT_MAX_DAYS),
                "no later than 74 days after publication, unless a lien is preserved/perfected", 74,
                cite="Construction Act s.26(4)"),
        ]
    out.append(Deadline("contractor passes down (from payment)", None,
                        "14 days after receipt — add to whichever payment date applies", 0, hard=False,
                        cite="Construction Act s.26(5)"))
    return out


def on_first_annual_anniversary(contract_date: dt.date) -> dt.date:
    """First contract anniversary to which s.26 applies (Construction Act s.87.4(4)).

    s.26 (as re-enacted) is in force 2026-01-01. A contract entered into on/after that day has an
    annual release after each anniversary. For a contract entered into BEFORE it, para 1 makes the
    first one "the second anniversary of the day the contract was entered into that follows" the
    in-force day. We read that as: the second occurrence of the anniversary date after
    2026-01-01. Counsel should confirm that reading. Improvements under s.87.3(1) are excluded.
    """
    if contract_date.month == 2 and contract_date.day == 29:
        raise ValueError("contract dated Feb 29: anniversary dates are not defined by the rules we "
                         "verified - pass the anniversary to `on-annual` yourself")
    in_force = R.ON_S26_IN_FORCE
    if contract_date >= in_force:
        return dt.date(contract_date.year + 1, contract_date.month, contract_date.day)
    y = in_force.year
    first = dt.date(y, contract_date.month, contract_date.day)
    if first <= in_force:
        first = dt.date(y + 1, contract_date.month, contract_date.day)
    return dt.date(first.year + 1, first.month, first.day)


def on_annual_from_contract(contract_date: dt.date, published: Optional[dt.date] = None) -> List[Deadline]:
    first = on_first_annual_anniversary(contract_date)
    pre = contract_date < R.ON_S26_IN_FORCE
    head = Deadline("first annual-release anniversary", first,
                    ("contract entered before 2026-01-01: first anniversary to which s.26 applies is "
                     "the second one after the in-force date (reading of s.87.4(4)1; confirm); that "
                     "release must include ALL holdback accrued before it (s.87.4(4)2)") if pre else
                    "first anniversary of a contract entered into on/after 2026-01-01",
                    0, hard=False, cite="Construction Act s.87.4(4)" if pre else "Construction Act s.26(2)")
    return [head] + on_annual_holdback(first, published)


def on_adjudication(completed: dt.date, subcontract_events: Optional[List[dt.date]] = None) -> List[Deadline]:
    """Ontario: last day to give a notice of adjudication after the contract ends.

    For a SUBCONTRACT pass the other candidate dates (subcontract certified complete, last supply)
    as subcontract_events: the 90 days run from the earliest of all of them (s.13.5(3.1)).
    """
    dates = [completed] + list(subcontract_events or [])
    anchor = min(dates)
    kind = "subcontract" if subcontract_events else "contract"
    return [_mk("ON", "notice of adjudication by", _d(anchor, R.ON_ADJUDICATION_DAYS),
                f"no adjudication of a {kind} if notice is given more than 90 days after the "
                f"{'earliest of the listed dates' if subcontract_events else 'date completed, abandoned or terminated'} "
                f"({anchor.isoformat()}), unless the parties agree otherwise", R.ON_ADJUDICATION_DAYS,
                cite="Construction Act s.13.5(3),(3.1)", filing=True)]
