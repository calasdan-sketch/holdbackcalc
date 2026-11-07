"""Neutralise untrusted text (project names from CSV, etc.) before it reaches a terminal or calendar."""
import unicodedata

# Bidi controls, zero-width and invisible formatting characters used for spoofing.
_BAD = set("\u061c\u180e\u200b\u200c\u200d\u200e\u200f\u2060\u2061\u2062\u2063\u2064\ufeff"
           "\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069")


def clean(text: str, limit: int = 120) -> str:
    """Replace control / bidi / zero-width characters with '?', collapse whitespace, cap length."""
    out = []
    for ch in str(text):
        cat = unicodedata.category(ch)
        if ch in _BAD or cat == "Cc" or cat == "Cs" or cat == "Co":
            out.append(" " if ch in "\t\r\n" else "?")
        else:
            out.append(ch)
    s = " ".join("".join(out).split())
    return s if len(s) <= limit else s[: limit - 1] + "…"
