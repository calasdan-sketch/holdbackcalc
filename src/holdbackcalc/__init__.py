"""holdbackcalc — prompt-payment, holdback and lien deadlines, verified rules only.

NOT legal or financial advice: an administrative date calculator. Every rule is
cited to a section of the official text (see `holdbackcalc rules`); confirm with
counsel for anything that matters.
"""

from .calc import (
    Deadline, ab_adjudication, ab_holdback, ab_invoice, ab_lien, ab_sub_payment,
    on_adjudication, on_annual_holdback, on_holdback_release, on_invoice_deficiency,
    holdback_amount, on_annual_from_contract, on_lien, on_lien_events, on_prompt_payment, on_sub_payment,
)
from .rules import REGISTRY, RULES, UNVERIFIED

__version__ = "0.2.0"
__author__ = "Calas Automations Inc."
__all__ = [
    "Deadline", "ab_invoice", "ab_sub_payment", "ab_lien", "ab_holdback", "ab_adjudication",
    "on_lien", "on_lien_events", "on_holdback_release", "on_invoice_deficiency",
    "on_prompt_payment", "on_sub_payment", "on_annual_holdback", "on_annual_from_contract", "on_adjudication",
    "RULES", "REGISTRY", "UNVERIFIED", "holdback_amount", "__version__", "__author__",
]
