# Round 5 review

Method note: no independent sub-agents were available, so one reviewer played each hat in turn and ran real commands for each. Windows and macOS were never run (static review and emulation only).

## Specialists and findings

| Hat | Finding | Proving command |
|---|---|---|
| Construction lawyer (AB) | Alberta holiday list in code matches Interpretation Act s.28(1)(x): Sundays, New Year, Alberta Family Day, Good Friday, Easter Monday, Victoria Day, Canada Day, Labour Day, Remembrance Day, Christmas, and Dec 26 (Dec 27 if Dec 26 is a Sunday or Monday). Thanksgiving is not on the list (proclamation days are not modelled). No change needed | `curl` of I08.pdf + `pdftotext`, read s.28(1)(x), 2026-11-08 |
| Construction lawyer (ON) | Ontario Act and Legislation Act pages still return a script shell; the 20 Ontario rules and the Ontario holiday rules remain machine-unverified. I did not work around the site's bot check | `holdbackcalc verify-sources` (15 PASS, 20 SKIPPED) |
| Project accountant | Dollar amounts were missing; a bookkeeper must know what to retain. Added `--amount` (Decimal, strict input, half-up rounding flagged as an unverified convention; base choice left to the user) | `holdbackcalc ab-holdback 2026-09-01 --amount 125000.50` |
| GC administrator | `--json --within N` with nothing due printed prose on stdout (broke parsers). Fixed | `holdbackcalc --json --today 2026-01-01 --within 1 batch j.csv` |
| Calendar/ICS engineer | Same job twice gave duplicate UIDs. Fixed (written once). Added calendar name. A strict RFC 5545 reader in the tests (CRLF, 75-octet folding, balanced blocks, required properties, unique UIDs, injected END:VEVENT neutralised) passes for every command. Alarms on all-day events: some apps ignore imported reminders; not tested here | `grep '^UID' | sort | uniq -d` |
| QA / test methodology | Mutation-style check (add 1 to each rule number) showed `ab-lien` standard period was in no golden vector; added. Seeded property tests (3,000 random jobs) and differential tests (ordinal arithmetic; `dateutil` Easter and `holidays` library when installed, both ran here) found no disagreement | `pytest -q` in a venv with `hypothesis python-dateutil holidays` |
| Release engineer / upgrade | Ran the real 0.1.0 wheel beside this tree: all 0.1.0 commands and JSON keys exist; `ab-invoice` gained a row, `on-annual` labels changed (round 3). Old docs had `verify-sources` exit 0 when nothing was checked; now 3. LICENSE carried the GitHub handle; fixed | `pip download holdbackcalc==0.1.0`, `cmp.py` diff |
| Competitor maintainer | BuilderLien: still a waitlist page (Ontario, $99/$199 per month listed) on 2026-11-08. Osler page could not be fetched this time (earlier reading kept, marked) | WebFetch |
| Debug | 3,000 random `--amount` strings: no crash; locale C / ascii output ok; spaces in paths ok; 10,001-row CSV refused cleanly; no-network `verify-sources` skips and exits 3 | shell, see CHANGELOG |

## Scored ideas (value / differentiation / effort / risk, 1-5)

| # | Idea | V | D | E | R | Status |
|---|---|---|---|---|---|---|
| 1 | Author line "Calas Automations Inc." everywhere + pinning tests | 5 | 1 | 1 | 1 | DONE |
| 2 | Valid empty machine output with `--within` | 5 | 2 | 1 | 1 | DONE |
| 3 | No duplicate calendar UIDs | 4 | 2 | 1 | 1 | DONE |
| 4 | `verify-sources` fails closed when nothing checked | 4 | 2 | 1 | 1 | DONE |
| 5 | `--amount` holdback dollars | 5 | 4 | 2 | 2 | DONE |
| 6 | Stable JSON row `id` | 4 | 3 | 1 | 1 | DONE |
| 7 | Golden files for all four formats | 4 | 1 | 2 | 1 | DONE |
| 8 | Mutation-style rule-number check | 4 | 2 | 2 | 1 | DONE |
| 9 | Seeded property tests + optional hypothesis | 4 | 1 | 2 | 1 | DONE |
| 10 | Differential vs dateutil / holidays (optional) | 3 | 1 | 2 | 1 | DONE |
| 11 | Strict calendar conformance test | 4 | 2 | 2 | 1 | DONE |
| 12 | Calendar name + company PRODID | 2 | 1 | 1 | 1 | DONE |
| 13 | README: script/agent section | 3 | 2 | 1 | 1 | DONE |
| 14 | Stable calendar UIDs surviving corrected dates | 3 | 3 | 3 | 3 | NOT-DONE (same-name collisions) |
| 15 | French output | 3 | 4 | 4 | 3 | NOT-DONE (needs legal reviewer) |
| 16 | BC / other provinces | 4 | 4 | 5 | 5 | NOT-DONE (rules unverified) |
| 17 | Web UI | 3 | 2 | 4 | 2 | NOT-DONE |
| 18 | Alberta Thanksgiving / proclamation days | 2 | 2 | 2 | 4 | NOT-DONE |
| 19 | Adjudication procedure deadlines | 3 | 4 | 4 | 4 | NOT-DONE |
| 20 | Read Ontario statute reliably in the checker | 4 | 3 | 4 | 2 | NOT-DONE (needs a legit saved copy or a browser) |
| 21 | Trusted publishing from CI | 3 | 1 | 2 | 2 | NOT-DONE (Dan's PyPI settings) |
| 22 | `--roll` option showing rolled date | 2 | 2 | 2 | 4 | NOT-DONE (plan to the earlier date on purpose) |
| 23 | MCP server / Claude Code hook | 3 | 3 | 3 | 2 | NOT-DONE (`--json` documented instead) |
| 24 | Amount column in batch CSV | 3 | 3 | 2 | 2 | NOT-DONE |
| 25 | Pure-Python PDF reading (no pdftotext) | 3 | 1 | 4 | 3 | NOT-DONE |

## Could not test
Windows, macOS; Python 3.10-3.12 (3.9 not rerun this round; 3.13 was). Ontario statute text (site serves a script shell). Whether Google/Outlook/Apple honour the alarms in imported all-day events. Osler and Textura pages (fetch failed / unreachable). The golden files are regression pins generated by the code; the date values in them were spot-checked by hand (lien +60/+90, Christmas-Friday deficiency window, 2027 second-anniversary reading), not independently verified for every row. Legal meaning of each rule is not re-audited. Nothing pushed, tagged or uploaded.
