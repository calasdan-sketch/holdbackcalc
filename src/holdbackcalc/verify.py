"""Re-check every registry rule against the official text.

    holdbackcalc verify-sources              # download the 5 official sources (needs network)
    holdbackcalc verify-sources --from-dir D # use files D/<SOURCE_KEY>.html|.pdf you saved yourself

PDFs need the `pdftotext` program (poppler); without it the Alberta rules are reported
SKIPPED. A source that cannot be fetched or converted is reported SKIPPED, never PASSED.
Exit status is 1 if any rule's evidence phrase is missing from its source (the law may
have changed - re-read it), 0 otherwise.
"""
from __future__ import annotations

import argparse
import html
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

from .rules import REGISTRY, SOURCE_TEXTS

MAX_DOWNLOAD = 60_000_000      # bytes; the real texts are a few MB at most


def norm(text):
    return re.sub(r"\s+", " ", text).replace("’", "'")


def html_to_text(raw):
    raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S)
    return norm(html.unescape(re.sub(r"<[^>]+>", " ", raw)))


def pdf_to_text(path):
    try:
        out = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, check=True, timeout=120)
    except FileNotFoundError:
        print("  pdftotext (poppler) is not installed, so the Alberta PDF sources cannot be read; "
              "those rules are SKIPPED", file=sys.stderr)
        return None
    except (OSError, subprocess.SubprocessError):
        return None
    return norm(out.stdout.decode("utf-8", "replace"))


def load(key, kind, url, from_dir):
    if from_dir:
        path = os.path.join(from_dir, f"{key}.{kind}")
        if not os.path.exists(path):
            return None
        return plausible(key, _read(path, kind))
    if not url.startswith("https://"):          # fail closed: only fetch the registry's https URLs
        return None
    req = urllib.request.Request(url, headers={"User-Agent": "holdbackcalc-verify/1"})
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = resp.read(MAX_DOWNLOAD + 1)
    except Exception as exc:  # network failure => SKIPPED, never PASSED
        print(f"  fetch failed for {key}: {exc}", file=sys.stderr)
        return None
    if len(data) > MAX_DOWNLOAD:
        print(f"  {key}: download larger than {MAX_DOWNLOAD} bytes - treating as unavailable", file=sys.stderr)
        return None
    with tempfile.TemporaryDirectory(prefix="holdbackcalc-") as td:
        path = os.path.join(td, f"{key}.{kind}")
        with open(path, "wb") as fh:
            fh.write(data)
        return plausible(key, _read(path, kind))


def _read(path, kind):
    if kind == "pdf":
        return pdf_to_text(path)
    with open(path, "rb") as fh:
        return html_to_text(fh.read().decode("utf-8", "replace"))


MIN_CHARS = 20_000      # every official text here is far longer; a short page is a JS shell / block page


def plausible(key, text):
    """A response that is not the statute (JS shell, bot-check, error page) must be SKIPPED, not FAILed."""
    if text is None:
        return None
    if len(text) < MIN_CHARS:
        print(f"  {key}: response is only {len(text)} characters - not the statute text "
              "(a script-rendered or blocked page?). Treating as unavailable. Save the page in a "
              f"browser as {key}.html (or .pdf) and use --from-dir.", file=sys.stderr)
        return None
    return text


def main(argv=None):
    ap = argparse.ArgumentParser(prog="holdbackcalc verify-sources", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from-dir", metavar="DIR", help="read saved pages from DIR instead of downloading")
    args = ap.parse_args(argv)
    texts = {k: load(k, kind, url, args.from_dir) for k, (_n, url, kind) in SOURCE_TEXTS.items()}
    failed = skipped = passed = 0
    for rule in REGISTRY:
        text = texts[rule.source]
        if text is None:
            skipped += 1
            print(f"SKIPPED {rule.id}  (source {rule.source} unavailable)")
        elif norm(rule.evidence).lower() in text.lower():
            passed += 1
            print(f"PASS    {rule.id}  {rule.cite}")
        else:
            failed += 1
            print(f"FAIL    {rule.id}  {rule.cite}  evidence not found: {rule.evidence!r}")
    print(f"\n{passed} passed, {failed} failed, {skipped} skipped of {len(REGISTRY)} rules")
    if passed == 0 and failed == 0:
        print("Nothing could be checked (every source was unavailable); this is not a pass.", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
