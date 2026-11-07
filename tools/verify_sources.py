#!/usr/bin/env python3
"""Re-check every registry rule against the official text.

    python tools/verify_sources.py              # download the 5 official sources (needs network)
    python tools/verify_sources.py --from-dir D # use files D/<SOURCE_KEY>.html|.pdf you saved yourself

PDFs need the `pdftotext` program (poppler). A source that cannot be fetched or
converted is reported SKIPPED, never PASSED. Exit status is 1 if any rule's
evidence phrase is missing from its source (the law may have changed - re-read it).
"""
import argparse
import html
import os
import re
import subprocess
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from holdbackcalc.rules import REGISTRY, SOURCE_TEXTS  # noqa: E402


def norm(text):
    return re.sub(r"\s+", " ", text).replace("’", "'")


def html_to_text(raw):
    raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S)
    return norm(html.unescape(re.sub(r"<[^>]+>", " ", raw)))


def pdf_to_text(path):
    try:
        out = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, check=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    return norm(out.stdout.decode("utf-8", "replace"))


def load(key, kind, url, from_dir):
    path = None
    if from_dir:
        path = os.path.join(from_dir, f"{key}.{kind}")
        if not os.path.exists(path):
            return None
    else:
        req = urllib.request.Request(url, headers={"User-Agent": "holdbackcalc-verify/1"})
        try:
            data = urllib.request.urlopen(req, timeout=90).read()
        except Exception as exc:  # network failure => SKIPPED, never PASSED
            print(f"  fetch failed for {key}: {exc}", file=sys.stderr)
            return None
        import tempfile
        fd, path = tempfile.mkstemp(suffix="." + kind)
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
    if kind == "pdf":
        text = pdf_to_text(path)
    else:
        with open(path, "rb") as fh:
            text = html_to_text(fh.read().decode("utf-8", "replace"))
    return plausible(key, text)


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
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from-dir")
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
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
