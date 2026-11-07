"""The rules — every constant here was verified against an official source.

Each rule has a REGISTRY entry (section citation, source, the phrase that
proves it). `tools/verify_sources.py` re-checks those phrases against the live
official texts. We deliberately encode NOTHING we could not verify: see
UNVERIFIED for the holes. A calculator that invents a legal deadline is worse
than no calculator.
"""
import datetime as _dt
from dataclasses import dataclass
from typing import Tuple

# --- Alberta (Prompt Payment and Construction Lien Act / Prompt Payment and
# Adjudication Regulation, Alta Reg 23/2022). Sources:
# https://www.alberta.ca/prompt-payment-rules-for-construction-industry
# https://open.alberta.ca/publications/2022_023
AB_INVOICE_PAYMENT_DAYS = 28          # payer pays a proper invoice within 28 calendar days
AB_DISPUTE_NOTICE_DAYS = 14           # owner must give notice of dispute within 14 calendar days
AB_SUB_PAYMENT_DAYS = 7               # contractor pays the sub within 7 days of receiving the owner's payment
AB_UNPAID_PASSTHROUGH_DAYS = 35       # s.32.3(4): owner did not pay -> contractor pays subs within 35 days of giving the invoice
AB_LIEN_REGISTER_DAYS = 60            # s.41: register a lien within 60 days (standard work)
AB_LIEN_REGISTER_DAYS_SPECIAL = 90    # s.41: 90 days for oil/gas well (site) improvements and concrete work
AB_LIS_PENDENS_DAYS = 180             # s.43(1): action + certificate of lis pendens within 180 days of registration
AB_HOLDBACK_RATE = 0.10               # s.18(1) major lien fund / s.23(1) minor lien fund: 10%
AB_HOLDBACK_DAYS = 60                 # s.18, s.23, s.27: 60-day retention / safe-payment period (standard work)
AB_HOLDBACK_DAYS_SPECIAL = 90         # same sections: 90 days for oil/gas well (site) improvements and concrete work
AB_ADJUDICATION_DAYS = 30             # s.33.4(2): notice of adjudication within 30 days of the date of final payment
AB_ANNUAL_HOLDBACK_MIN_PRICE = 10_000_000  # Alta Reg 23/2022 s.2(2): prescribed contract price for annual/phased payment

# --- Ontario (Construction Act, consolidated to Jan 1, 2026). Sources:
# https://www.ontario.ca/laws/statute/90c30
# https://cassels.com/insights/the-construction-act-whats-new-in-the-new-year/
ON_LIEN_PRESERVE_DAYS = 60            # preserve a lien within 60 days of the trigger event
ON_LIEN_PERFECT_DAYS = 90             # commence the action within 90 days after the preservation period
ON_HOLDBACK_RATE = 0.10               # statutory holdback is 10%
ON_OWNER_PAYMENT_AFTER_LIEN_DAYS = 14  # owner pays within 14 days of lien period expiry
ON_PASS_DOWN_DAYS = 14                # contractor/sub passes holdback down within 14 days of receipt
ON_OWNER_PAYMENT_TOTAL_DAYS = ON_LIEN_PRESERVE_DAYS + ON_OWNER_PAYMENT_AFTER_LIEN_DAYS  # 74
ON_INVOICE_DEFICIENCY_DAYS = 7        # 2026: invoice deemed proper unless deficiency notice in 7 days
ON_ANNUAL_NOTICE_DAYS = 14            # 2026: publish annual-release notice within 14 days of anniversary
ON_ANNUAL_PAYMENT_MIN_DAYS = 60       # payment no earlier than 60 days after publication
ON_ANNUAL_PAYMENT_MAX_DAYS = 74       # ... and no later than 74 days after publication
ON_ADJUDICATION_DAYS = 90             # s.13.5(3)/(3.1): adjudication notice within 90 days (completion/abandonment/termination)
ON_INVOICE_PAYMENT_DAYS = 28          # s.6.4(1): owner pays a proper invoice within 28 days
ON_NOTICE_NONPAYMENT_DAYS = 14        # s.6.4(2): owner's notice of non-payment within 14 days
ON_SUB_PAYMENT_DAYS = 7               # s.6.5(1): contractor pays subs within 7 days of receiving payment
ON_UNPAID_PASSTHROUGH_DAYS = 35       # s.6.5(4): owner did not pay -> contractor pays subs within 35 days of giving the invoice
ON_S26_IN_FORCE = _dt.date(2026, 1, 1)  # s.26 (re-enacted) in force date, from the Act's amendment table
ON_TERMINATION_NOTICE_DAYS = 7        # s.31(6): publish notice of termination within 7 days of termination

# --- What we could NOT verify from primary text and therefore do not compute.
# (Rules that WERE verified live in REGISTRY below with a citation.)
UNVERIFIED = [
    "AB: Act consolidation read is 'current as of April 1, 2025' and the Regulation 'as of November 26, 2025'; later amendments were not checked",
    "AB: whether Thanksgiving Day counts as a 'holiday' for time limits (not named in Interpretation Act s.28(1)(x); proclamation-based) - not rolled forward",
    "AB: base-building / partial-performance treatment and sub-subcontract holdback detail",
    "AB: detailed adjudication procedure deadlines (Alta Reg 23/2022 ss.20-30) - only the 30-day-after-final-payment filing limit is encoded",
    "ON: Saturday / closed-office extensions (Legislation Act s.89(2)) - only Sundays and statutory holidays are rolled forward",
    "ON: general-lien rules; the workers' trust fund lien (s.31(2.1)) is encoded only as `--role trustee` using the date the final beneficiary worker last supplied",
    "Both: where an office is closed on a Saturday, a filing deadline MAY extend (ON Legislation Act s.89(2); AB Interpretation Act s.22(2)) - flagged with a note on Saturday filing deadlines, never computed (we do not know your office's hours)",
    "ON: s.87.4(4) transition (contracts entered before 2026-01-01: first annual release is the 'second anniversary ... that follows' the in-force day) IS encoded by on-annual-first, but the wording is ambiguous and our reading needs counsel; AFP project agreements (s.87.4(5)) are not modelled",
    "ON: any 'first 90 days of contract' short lien period (not found in the current Act)",
    "ON: a general 45-day pleadings deadline (not found in the current Act)",
    "Both: whether a given job is in scope (public works, pre-July-2018 Ontario contracts, Parts I.1/II.1 transition) - YOU must confirm; see `applicability`",
]

SOURCES = {
    "AB overview": "https://www.alberta.ca/prompt-payment-rules-for-construction-industry",
    "AB regulation": "https://open.alberta.ca/publications/2022_023",
    "AB Act (PDF)": "https://kings-printer.alberta.ca/documents/Acts/P26P4.pdf",
    "AB Regulation (PDF)": "https://kings-printer.alberta.ca/documents/Regs/2022_023.pdf",
    "AB Interpretation Act (PDF)": "https://kings-printer.alberta.ca/documents/Acts/I08.pdf",
    "ON Act": "https://www.ontario.ca/laws/statute/90c30",
    "ON Legislation Act, 2006": "https://www.ontario.ca/laws/statute/06l21",
    "ON 2026 amendments summary (secondary)": "https://cassels.com/insights/the-construction-act-whats-new-in-the-new-year/",
}

RULES = {
    "ab_invoice_payment_days": AB_INVOICE_PAYMENT_DAYS,
    "ab_dispute_notice_days": AB_DISPUTE_NOTICE_DAYS,
    "ab_sub_payment_days": AB_SUB_PAYMENT_DAYS,
    "on_lien_preserve_days": ON_LIEN_PRESERVE_DAYS,
    "on_lien_perfect_days": ON_LIEN_PERFECT_DAYS,
    "on_holdback_rate": ON_HOLDBACK_RATE,
    "on_owner_payment_after_lien_days": ON_OWNER_PAYMENT_AFTER_LIEN_DAYS,
    "on_pass_down_days": ON_PASS_DOWN_DAYS,
    "on_invoice_deficiency_days": ON_INVOICE_DEFICIENCY_DAYS,
    "on_annual_notice_days": ON_ANNUAL_NOTICE_DAYS,
    "on_annual_payment_window_days": [ON_ANNUAL_PAYMENT_MIN_DAYS, ON_ANNUAL_PAYMENT_MAX_DAYS],
}


# ---------------------------------------------------------------------------
# Source-cited registry. `evidence` is a phrase that appears (after whitespace
# normalisation) in the official text named by `source`; tools/verify_sources.py
# re-checks it. `read_on` is when a human last read the text.
# ---------------------------------------------------------------------------
READ_ON = "2026-11-07"

SOURCE_TEXTS = {
    "ON_ACT": ("Ontario Construction Act, R.S.O. 1990, c. C.30 (consolidation from Jan 1, 2026)",
               "https://www.ontario.ca/laws/statute/90c30", "html"),
    "AB_ACT": ("Alberta Prompt Payment and Construction Lien Act, RSA 2000, c. P-26.4 (current as of Apr 1, 2025)",
               "https://kings-printer.alberta.ca/documents/Acts/P26P4.pdf", "pdf"),
    "AB_REG": ("Alberta Prompt Payment and Adjudication Regulation, Alta Reg 23/2022 (current as of Nov 26, 2025)",
               "https://kings-printer.alberta.ca/documents/Regs/2022_023.pdf", "pdf"),
    "ON_LEG": ("Ontario Legislation Act, 2006, S.O. 2006, c. 21, Sched. F",
               "https://www.ontario.ca/laws/statute/06l21", "html"),
    "AB_INTERP": ("Alberta Interpretation Act, RSA 2000, c. I-8",
                  "https://kings-printer.alberta.ca/documents/Acts/I08.pdf", "pdf"),
}


@dataclass(frozen=True)
class Rule:
    id: str
    jurisdiction: str          # "AB" | "ON"
    value: object
    unit: str
    cite: str                  # section reference
    source: str                # key into SOURCE_TEXTS
    evidence: str              # phrase that must appear in the source text
    note: str = ""

    def as_dict(self):
        name, url, _kind = SOURCE_TEXTS[self.source]
        return {"id": self.id, "jurisdiction": self.jurisdiction, "value": self.value,
                "unit": self.unit, "cite": self.cite, "source": name, "url": url,
                "evidence": self.evidence, "read_on": READ_ON, "note": self.note,
                "status": "verified-primary-text"}


REGISTRY: Tuple[Rule, ...] = (
    # Alberta
    Rule("ab.invoice.payment_days", "AB", AB_INVOICE_PAYMENT_DAYS, "days", "PPCLA s.32.2(1)", "AB_ACT",
         "no later than 28 days after receiving the proper invoice"),
    Rule("ab.invoice.dispute_notice_days", "AB", AB_DISPUTE_NOTICE_DAYS, "days", "PPCLA s.32.2(2)", "AB_ACT",
         "no later than 14 days after receiving the proper invoice, the owner gives"),
    Rule("ab.sub.payment_days", "AB", AB_SUB_PAYMENT_DAYS, "days", "PPCLA s.32.3(1)", "AB_ACT",
         "no later than 7 days after receiving payment, pay each subcontractor"),
    Rule("ab.sub.unpaid_passthrough_days", "AB", AB_UNPAID_PASSTHROUGH_DAYS, "days", "PPCLA s.32.3(4)", "AB_ACT",
         "no later than 35 days after giving the proper invoice to the owner",
         "unless the contractor gives the s.32.3(5)/(6) notices"),
    Rule("ab.lien.register_days", "AB", AB_LIEN_REGISTER_DAYS, "days", "PPCLA s.41(1)-(4)(a)", "AB_ACT",
         "terminating 60 days from the day that the last of the materials is furnished"),
    Rule("ab.lien.register_days_special", "AB", AB_LIEN_REGISTER_DAYS_SPECIAL, "days", "PPCLA s.41(1)-(4)(b),(c)", "AB_ACT",
         "terminating 90 days from the day that the last of the materials is furnished",
         "oil/gas well or well site improvements; concrete work"),
    Rule("ab.lien.lis_pendens_days", "AB", AB_LIS_PENDENS_DAYS, "days", "PPCLA s.43(1)", "AB_ACT",
         "within 180 days from the date it is registered"),
    Rule("ab.holdback.rate", "AB", AB_HOLDBACK_RATE, "fraction", "PPCLA s.18(1), s.23(1)", "AB_ACT",
         "retain an amount equal to 10% of the value of the work actually done"),
    Rule("ab.holdback.days", "AB", AB_HOLDBACK_DAYS, "days", "PPCLA s.18(1), s.23(1), s.27(1)-(2)", "AB_ACT",
         "On the expiration of 60 days from the day that the contract is completed",
         "from certificate of substantial performance (major fund) or completion"),
    Rule("ab.holdback.days_special", "AB", AB_HOLDBACK_DAYS_SPECIAL, "days", "PPCLA s.18(1.1),(1.2), s.27(2.1)-(2.21)", "AB_ACT",
         "on the expiration of 90 days from the day that the contract is completed",
         "oil/gas well or well site improvements; concrete work"),
    Rule("ab.adjudication.days", "AB", AB_ADJUDICATION_DAYS, "days", "PPCLA s.33.4(2)", "AB_ACT",
         "more than 30 days after the date of final payment"),
    Rule("ab.annual_holdback.min_price", "AB", AB_ANNUAL_HOLDBACK_MIN_PRICE, "CAD", "Alta Reg 23/2022 s.2(2)", "AB_REG",
         "the prescribed amount of the contract price is $10 000 000",
         "annual/phased holdback payment also needs a schedule > 1 year and no filed liens (PPCLA s.24.1)"),
    Rule("ab.time.day_counting", "AB", "first day excluded, last included", "rule", "Interpretation Act s.22(4),(7)", "AB_INTERP",
         "the day on which the first event happens shall be excluded"),
    Rule("ab.time.holiday_rollforward", "AB", "next non-holiday", "rule", "Interpretation Act s.22(1)", "AB_INTERP",
         "expires or falls on a holiday, the thing may be done on the day next"),
    # Ontario
    Rule("on.invoice.payment_days", "ON", ON_INVOICE_PAYMENT_DAYS, "days", "Construction Act s.6.4(1)", "ON_ACT",
         "no later than 28 days after receiving the proper invoice"),
    Rule("on.invoice.notice_nonpayment_days", "ON", ON_NOTICE_NONPAYMENT_DAYS, "days", "Construction Act s.6.4(2)", "ON_ACT",
         "no later than 14 days after receiving the proper invoice from the contractor"),
    Rule("on.invoice.deficiency_days", "ON", ON_INVOICE_DEFICIENCY_DAYS, "days", "Construction Act s.6.1(2)", "ON_ACT",
         "no later than seven days after receiving the invoice"),
    Rule("on.sub.payment_days", "ON", ON_SUB_PAYMENT_DAYS, "days", "Construction Act s.6.5(1)", "ON_ACT",
         "no later than seven days after receiving payment"),
    Rule("on.sub.unpaid_passthrough_days", "ON", ON_UNPAID_PASSTHROUGH_DAYS, "days", "Construction Act s.6.5(4)", "ON_ACT",
         "no later than 35 days after giving the proper invoice to the owner",
         "unless the contractor gives the s.6.5(5)/(6) notices"),
    Rule("on.holdback.rate", "ON", ON_HOLDBACK_RATE, "fraction", "Construction Act s.22(1)", "ON_ACT",
         "equal to 10 per cent of the price of the services or materials"),
    Rule("on.lien.preserve_days", "ON", ON_LIEN_PRESERVE_DAYS, "days", "Construction Act s.31(2),(3)", "ON_ACT",
         "expires at the conclusion of the 60-day period next following"),
    Rule("on.lien.perfect_days", "ON", ON_LIEN_PERFECT_DAYS, "days", "Construction Act s.36(2)", "ON_ACT",
         "prior to the end of the 90-day period next following the last day"),
    Rule("on.lien.termination_notice_days", "ON", ON_TERMINATION_NOTICE_DAYS, "days", "Construction Act s.31(6)", "ON_ACT",
         "No later than seven days after a contract is terminated"),
    Rule("on.holdback.owner_pay_after_lien_days", "ON", ON_OWNER_PAYMENT_AFTER_LIEN_DAYS, "days", "Construction Act s.26(8)1", "ON_ACT",
         "not later than 14 days after the liens have expired"),
    Rule("on.holdback.pass_down_days", "ON", ON_PASS_DOWN_DAYS, "days", "Construction Act s.26(8)2-3", "ON_ACT",
         "not later than 14 days after receiving payment of a holdback from the owner"),
    Rule("on.annual.notice_days", "ON", ON_ANNUAL_NOTICE_DAYS, "days", "Construction Act s.26(3)", "ON_ACT",
         "Not later than 14 days after the anniversary"),
    Rule("on.annual.payment_window_days", "ON", [ON_ANNUAL_PAYMENT_MIN_DAYS, ON_ANNUAL_PAYMENT_MAX_DAYS], "days", "Construction Act s.26(4)", "ON_ACT",
         "At least 60 days but not later than 74 days after the date on which the notice"),
    Rule("on.adjudication.days", "ON", ON_ADJUDICATION_DAYS, "days", "Construction Act s.13.5(3),(3.1)", "ON_ACT",
         "more than 90 days after the date on which the contract is completed, abandoned or terminated"),
    Rule("on.annual.transition_second_anniversary", "ON", "second anniversary", "rule", "Construction Act s.87.4(4)1", "ON_ACT",
         "is the second anniversary of the day the contract was entered into that follows the day on which section 26",
         "contracts entered into before s.26 came into force; wording ambiguous"),
    Rule("on.annual.s26_in_force", "ON", "2026-01-01", "date", "Construction Act s.26 amendment table", "ON_ACT",
         "2024, c. 20, Sched. 4, s. 26 - 01/01/2026"),
    Rule("on.lien.trustee_expiry", "ON", 60, "days", "Construction Act s.31(2.1)", "ON_ACT",
         "the lien of the trustee of a workers’ trust fund on behalf of a worker or workers"),
    Rule("ab.time.closed_office", "AB", "next open day", "rule", "Interpretation Act s.22(2)", "AB_INTERP",
         "is not open during its regular hours of business"),
    Rule("on.time.closed_office", "ON", "next open day", "rule", "Legislation Act, 2006 s.89(2)", "ON_LEG",
         "expire on a day when the place for doing so is not open during its regular hours of business"),
    Rule("on.time.holiday_rollforward", "ON", "next non-holiday", "rule", "Legislation Act, 2006 s.89(1)", "ON_LEG",
         "Time limits that would otherwise expire on a holiday are extended to include the next day that is not a holiday"),
    Rule("on.time.day_counting", "ON", "first day excluded, last included", "rule", "Legislation Act, 2006 s.89(3)", "ON_LEG",
         "excludes the day on which the first event happens and includes the day on which the second event happens"),
)

# Scope warnings that no date arithmetic can resolve. Printed with every schedule.
APPLICABILITY = {
    "AB": [
        "Alberta government (Public Works Act) contracts are outside the PPCLA payment timelines "
        "(alberta.ca prompt-payment page).",
        "Contracts that pre-date the Aug 29, 2022 start of the new rules may follow the old Act "
        "(alberta.ca prompt-payment page).",
    ],
    "ON": [
        "Contracts/procurements that started before July 1, 2018 stay under the old Act (Construction Act s.87.3(1)).",
        "Prompt-payment and adjudication Parts do not apply to contracts entered into before Oct 1, 2019 "
        "(Construction Act s.87.3(4)).",
    ],
}
