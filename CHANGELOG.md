# Changelog

## 0.2.0 (unreleased)

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
