"""The rules — every constant here was verified against an official source.

We deliberately encode NOTHING we could not verify: see UNVERIFIED for the
holes (Alberta's statutory holdback percentage and release clock chief among
them). A calculator that invents a legal deadline is worse than no calculator.
"""

# --- Alberta (Prompt Payment and Construction Lien Act / Prompt Payment and
# Adjudication Regulation, Alta Reg 23/2022). Sources:
# https://www.alberta.ca/prompt-payment-rules-for-construction-industry
# https://open.alberta.ca/publications/2022_023
AB_INVOICE_PAYMENT_DAYS = 28          # payer pays a proper invoice within 28 calendar days
AB_DISPUTE_NOTICE_DAYS = 14           # owner must give notice of dispute within 14 calendar days
AB_SUB_PAYMENT_DAYS = 7               # contractor pays the sub within 7 days of receiving the owner's payment

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
ON_ADJUDICATION_DAYS = 90             # 2026: adjudication up to 90 days after completion/abandonment/termination

# --- What we could NOT verify from official text (October 2026) and therefore
# do not compute. Configure these yourself only if you have the rule.
UNVERIFIED = [
    "AB: statutory holdback percentage and the post-substantial-performance release clock",
    "AB: substantial-performance payment deadline and base-building/partial-performance treatment",
    "AB: detailed adjudication filing deadlines",
    "ON: any 'first 90 days of contract' short lien period (not found in the current Act)",
    "ON: a general 45-day pleadings deadline (not found in the current Act)",
]

SOURCES = {
    "AB overview": "https://www.alberta.ca/prompt-payment-rules-for-construction-industry",
    "AB regulation": "https://open.alberta.ca/publications/2022_023",
    "ON Act": "https://www.ontario.ca/laws/statute/90c30",
    "ON 2026 amendments summary": "https://cassels.com/insights/the-construction-act-whats-new-in-the-new-year/",
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
