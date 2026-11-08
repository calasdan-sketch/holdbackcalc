# Changelog

## 0.2.0 (unreleased)

### Review round 5 (construction lawyer, project accountant, GC administrator, calendar interoperability, test methodology)

- Author: LICENSE said the GitHub handle; now "Copyright (c) 2026 Calas Automations Inc."; `maintainers` added; `__author__`; calendar PRODID names the company. Pinned by tests, and a built wheel's METADATA is checked.
- Bug: `--json`/`--ics`/`--csv` with `--within` and nothing due printed a plain sentence on stdout, breaking parsers. The sentence now goes to stderr and the document is valid but empty.
- Bug: the same job twice in a batch gave duplicate calendar UIDs (invalid). Repeats are now written once.
- Fail closed: `verify-sources` exited 0 when nothing could be checked; now exits 3.
- Added: `--amount DOLLARS` on `ab-holdback` / `on-holdback` (the 10% in dollars, Decimal arithmetic, strict input); stable `id` on every JSON row (additive); `X-WR-CALNAME` in the calendar file.
- Tests: golden files for text/JSON/CSV/calendar, mutation-style checks that every rule number is pinned (this found `ab-lien` for standard jobs was not pinned by any golden vector; added), seeded property tests, differential tests (independent ordinal arithmetic; `dateutil`/`holidays` if installed), strict calendar parser, hand-known holiday vectors including the Alberta Dec 26/27 rule re-read from the Interpretation Act on 2026-11-08. 223 tests (was 134).
- Upgrade from 0.1.0 checked by running the real 0.1.0 wheel: every command and JSON key still exists; only `ab-invoice` gained a row and `on-annual` row labels changed (already noted in round 3).
- Version stays 0.2.0 (not yet on PyPI).

### Review round 4 (what a stranger who types `pip install` actually gets)

Found by building the wheel and sdist, installing into clean virtualenvs (Python 3.9 and 3.13) and attacking the CLI:
- `holdbackcalc ... | head` (or any closed pipe) printed a traceback; a full disk did too. Now silent / a one-line message. Any other unexpected error prints a short "internal error, please report" with exit status 70 instead of a traceback (`HOLDBACKCALC_DEBUG=1` shows the details). Ctrl-C exits 130.
- `--out FILE` left an empty file behind when the run failed, so the retry said "already exists". The file is now removed on failure.
- `--ics` on Windows would have written `CR CR LF` line endings (text-mode stdout translates the calendar's CRLF again); fixed and tested with an emulated Windows stream. Not run on real Windows.
- `--within -5` was accepted; now an error. Weekday names no longer follow the machine's locale.
- The README told pip users to run `python tools/verify_sources.py`, a file that is not in the wheel. It is now `holdbackcalc verify-sources` (the old script remains as a wrapper). The downloader now caps the download size, only fetches https, deletes its temporary files, says when `pdftotext` is missing, and says "this is not a pass" when nothing could be checked.
- `python -m holdbackcalc` did not work; `on_annual_from_contract` was missing from the package's public names; no `py.typed`.
- Packaging metadata: author now "Calas Automations Inc."; project URLs, classifiers (Python 3.9-3.13, OS independent, typed) added; `setuptools>=77` is now required because an SPDX `license = "MIT"` string needs it (older setuptools would fail to build); sdist now includes CHANGELOG.

Added: `holdbackcalc verify-sources`, `batch -` (CSV from standard input), `--today today`, `schema_version` and `tool_version` in `--json` output (additive), a README "use as a library" example, tests that run every command in the README, and CI on Windows as well as Linux plus a clean-virtualenv wheel smoke test and mypy. Tests: 134 (was 107).

Backward compatible: nothing removed; every JSON key from earlier rounds is unchanged.

### Review round 3 (construction lawyer, Windows AR controller, spreadsheet/attacker, calendar-interop, performance, docs/DX)

Bugs found by hands-on testing and fixed:
- `tools/verify_sources.py` reported 16 false FAILs when ontario.ca returned a script shell; short or non-statute responses are now SKIPPED with instructions (`--from-dir`).
- `pytest -q` failed on a fresh clone (package not on the path); pytest now has `pythonpath = ["src"]`.
- Ontario annual holdback dates were labelled "earliest/latest payment" but were anchored to the *last day* the notice may be published; they are now labelled as outer bounds, and `--published DATE` gives the exact s.26(4) window (breaking label change).
- The Ontario "perfect lien by" row did not say that an unpreserved lien cannot be perfected (s.36(1)); it does now, and mentions sheltering (s.36(4)).
- Legacy Windows consoles crashed on the arrow and dash characters; output now degrades to `?` and JSON falls back to ASCII escapes. `--out FILE` writes UTF-8 (PowerShell `>` writes UTF-16).
- A CSV field over 131,072 characters produced a traceback; it is now a clean error. Duplicate CSV columns are rejected. Week-format dates such as `2026-W01-1` (accepted by newer Pythons) and non-ASCII digits are rejected.
- `batch` rejected Excel files: semicolon-separated (French locale) and Windows-1252 / UTF-16 files now load; commands and sectors are case-insensitive. Bad dates hint at the Excel format fix.
- `--json` and `--ics` together silently picked one; the output flags are now mutually exclusive. The `batch` positional no longer collides with a `--csv` flag.

Added (all cited to the statute text read 2026-11-07):
- `on-annual-first CONTRACT_DATE`: s.87.4(4) transition (this resolves the earlier "only a secondary source says second anniversary" gap; the wording is ambiguous and our reading is flagged for counsel). Rules `on.annual.transition_second_anniversary`, `on.annual.s26_in_force`.
- `on-lien-events --role trustee` (workers' trust fund lien, s.31(2.1)).
- Weekday on every date, `plan_by` (last business day to act when a deadline is on a weekend or holiday), a Saturday-filing flag citing ON Legislation Act s.89(2) / AB Interpretation Act s.22(2).
- `--csv` (formula-injection safe), `--within N` with `--today`, `--out FILE`, stale-rules warning after 180 days (also `stale_warning` in JSON), `SOURCE_DATE_EPOCH` for reproducible `.ics` output.
- Rules: 35 (was 30). Tests: 107 (was 74).

Not built (ideas scored and left out): stable calendar UIDs that survive a corrected anchor date (would collide for two jobs with the same name); French-language output; Quebec/BC/other provinces (rules not verified); adjudication procedure deadlines; Alberta Thanksgiving treatment (not in the Interpretation Act list; proclamation-based); a web UI.

### Review round 2

Expert review (construction lawyer, contractor AR controller, first-time project administrator, legal-data QA engineer). Findings and fixes:

- **Fixed a silent gap:** Ontario's 28/14/7/35-day prompt-payment clock was not encoded at all; only the 7-day deficiency window was. Added `on-prompt-payment`, `on-sub-payment`.
- **Alberta rules the old README called "unverified" are in the Act text** (10% holdback, 60/90-day periods, lien registration, 180-day action, 30-day adjudication limit). Encoded: `ab-lien`, `ab-holdback`, `ab-adjudication`, with oil/gas-well and concrete 90-day sectors. The Act consolidation read is current as of 2025-04-01; later amendments are not checked and are listed as such.
- **Ontario lien expiry is "60 days after the earliest applicable event" by role (s.31), not one date.** Added `on-lien-events`; `on-lien` unchanged for the simple case.
- Holiday awareness (Ontario Legislation Act ss.88-89; Alberta Interpretation Act ss.22, 28): the printed date stays the plain arithmetic date; a later "may roll forward" date is shown separately.
- Source registry: 30 rules with section citations and evidence phrases; `holdbackcalc rules`; `tools/verify_sources.py` re-checks them against the official texts (SKIPPED, never PASSED, when a source is unreachable).
- `batch` (CSV, fail-closed, capped at 5 MB / 10,000 rows), `--ics`, `--today` (days left / OVERDUE), scope checklist on every result, error exit status 2 instead of tracebacks, years limited to 2000-2100.
- Control, bidi and zero-width characters in project names are neutralised in terminal and calendar output.
- `tools/bench.py` benchmark; ruff config; 74 tests (was 15).

Behaviour changes: `ab-invoice` placeholder renamed from "unverified: holdback release" to "holdback release: use ab-holdback"; `what-we-dont-encode` list rewritten; JSON schedule items gain `cite` and `rolled_forward_to`, and the JSON document gains `disclaimer`, `applicability`, `rules_read_on`. JSON is now UTF-8 (not `\u`-escaped).

## 0.1.0

Initial release.
