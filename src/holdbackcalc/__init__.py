"""holdbackcalc — prompt-payment and holdback deadlines, verified rules only.

Not legal or financial advice: an administrative date calculator. Figures were
verified against official sources in October 2026 (see README); confirm with
counsel for anything that matters.
"""

from .calc import Deadline, ab_invoice, ab_sub_payment, on_invoice_deficiency, on_lien, on_holdback_release, on_annual_holdback
from .rules import RULES, UNVERIFIED

__version__ = "0.1.0"
__all__ = [
    "Deadline", "ab_invoice", "ab_sub_payment", "on_lien", "on_holdback_release",
    "on_invoice_deficiency", "on_annual_holdback", "RULES", "UNVERIFIED",
    "__version__",
]
