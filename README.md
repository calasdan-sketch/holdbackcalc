# holdbackcalc

**Prompt-payment, holdback and lien deadlines for Alberta and Ontario construction work. Every rule is cited to a section of the official text and re-checkable with one command; anything we could not verify is left out on purpose.** Give it a date; get a dated schedule, a calendar file, or a whole portfolio of jobs sorted by what is due next.

> **Not legal advice.** This is an administrative date calculator. Lien and holdback deadlines are strict; a missed date can cost the claim. Statutes and your contract may differ from the general rules encoded here (public works, pre-2018 Ontario contracts, oil/gas and concrete special periods, notices you did or did not send). Confirm anything that matters with a construction lawyer in the right province. The tool prints this reminder and a scope checklist with every result.

## Install and first run

```bash
pip install holdbackcalc            # Python 3.9+, no dependencies
holdbackcalc ab-invoice 2026-06-30
```

```
dispute notice by (owner)                  2026-07-14  owner must give notice of dispute within 14 calendar days of receipt  [PPCLA s.32.2(2)]
payment due (owner → contractor)           2026-07-28  proper invoice payable within 28 calendar days  [PPCLA s.32.2(1)]
...
Administrative reminders, not legal advice — verify anything that matters.
```

The printed date is plain arithmetic (anchor day excluded, last day included, as both provinces' time-computation rules say). If it lands on a Sunday or statutory holiday the tool adds a `note:` with the later date the statute *may* allow. Plan to the earlier date.

## Commands

| Province | Command | What it gives you |
|---|---|---|
| AB | `ab-invoice DATE` | owner dispute notice (+14), payment due (+28), contractor pass-through if owner has not paid (+35) |
| AB | `ab-sub-payment DATE` | contractor pays sub (+7 from owner's payment) |
| AB | `ab-lien DATE [--sector oil-gas\|concrete] [--registered DATE]` | register lien (+60, or +90 for oil/gas wells and concrete); with `--registered`, the 180-day action + lis pendens deadline |
| AB | `ab-holdback COMPLETED [--certificate DATE] [--sector ...]` | 10% major/minor lien fund retention and earliest safe-payment dates |
| AB | `ab-adjudication DATE` | last day to give notice of adjudication (30 days after final payment) |
| ON | `on-prompt-payment DATE` | deficiency notice (+7), owner's notice of non-payment (+14), payment (+28), pass-through (+35) |
| ON | `on-sub-payment DATE` | contractor pays subs (+7) |
| ON | `on-lien-events --role contractor\|other ...` | s.31 lien expiry from the **earliest applicable event** (certificate published, completion, last supply, subcontract certified), then the 90-day perfection date |
| ON | `on-lien DATE` | simple form: one trigger event, +60 then +90 |
| ON | `on-holdback DATE` / `on-annual DATE` | holdback release after the lien period; annual release (2026 rules) |
| ON | `on-invoice DATE` | 7-day proper-invoice deficiency window |
| ON | `on-adjudication DATE [--also DATE ...]` | last day for notice of adjudication (90 days; earliest date wins for subcontracts) |
| both | `batch jobs.csv` | many jobs at once: `project,command,date[,certificate,registered,sector]` |
| both | `rules` | every encoded rule with citation and source URL |
| both | `what-we-dont-encode` | the holes, listed |

Global flags go before the command: `--json`, `--ics` (calendar file with 7-day and 1-day alarms), `--today YYYY-MM-DD` (days left, `OVERDUE`).

```bash
holdbackcalc --ics batch jobs.csv > deadlines.ics         # import into Outlook / Google / Apple Calendar
holdbackcalc --today 2026-07-20 batch jobs.csv            # what is due or overdue, across all jobs
holdbackcalc on-lien-events --role other --supply-before-sp \
  --cert-published 2026-04-01 --completed 2026-05-15 --last-supply 2026-03-20
```

## Trust: how rules are verified

`holdbackcalc rules` lists 30 rules; each has a section citation, the official source URL and an "evidence phrase" that appears in that text. Re-check them yourself at any time:

```bash
python tools/verify_sources.py    # downloads the official texts; PASS / FAIL / SKIPPED per rule
```

A rule that cannot be checked is reported SKIPPED, never PASSED. A FAIL means the law may have changed.

Primary sources read on 2026-11-07:
Ontario [Construction Act](https://www.ontario.ca/laws/statute/90c30) (consolidation from Jan 1, 2026) and [Legislation Act, 2006](https://www.ontario.ca/laws/statute/06l21);
Alberta [Prompt Payment and Construction Lien Act](https://kings-printer.alberta.ca/documents/Acts/P26P4.pdf) (**current as of April 1, 2025**), [Regulation 23/2022](https://kings-printer.alberta.ca/documents/Regs/2022_023.pdf) (current as of Nov 26, 2025) and [Interpretation Act](https://kings-printer.alberta.ca/documents/Acts/I08.pdf); the Alberta [prompt-payment overview page](https://www.alberta.ca/prompt-payment-rules-for-construction-industry). Amendments after those consolidation dates were **not** checked.

## What it does NOT encode

```
$ holdbackcalc what-we-dont-encode
```
Includes: Alberta amendments after the consolidation dates above; whether Thanksgiving is a holiday for Alberta time limits; Saturday and closed-office extensions; Ontario workers' trust fund liens; Ontario transition for contracts entered before 2026 (only a secondary source says "second anniversary", not found in the Act text); adjudication procedure deadlines beyond the filing limits; and whether *your* job is in scope. Wrong-province or wrong-contract-date results are the biggest practical risk: read the scope checklist.

## Honest comparison

Measured on this repo (re-run `python tools/bench.py`; `pytest -q`):

| | v0.1.0 | v0.2.0 |
|---|---|---|
| Rules encoded | 11 constants, no citations | 30 rules, each cited + machine-checkable |
| Alberta holdback / lien / adjudication | listed as unverified | encoded from the Act text (with sector periods) |
| Ontario prompt payment (28/14/7/35) | missing | encoded |
| Ontario lien trigger | one date, no role | earliest applicable event by role (s.31) |
| Holiday / Sunday awareness | none | both provinces (rolled date shown separately) |
| Multi-job view, calendar export | none | `batch`, `--ics`, `--today` |
| Tests | 15 | 74 (hand-written golden dates, 2,000-date property sweep, CLI fuzz, hostile CSV) |
| 10,000-job batch | n/a | about 0.07 s on the dev machine |

Against other tools (all **unverified** as to features; we checked only that the pages below were reachable):

| Tool | What we could check | Everything else |
|---|---|---|
| Procore Pay (procore.com/pay) | US-English page text (fetched 2026-11-07, no JS) mentions liens, and does not mention Alberta, Ontario, holdback or prompt payment | Canadian coverage, pricing, deadline features: unverified |
| Textura | site not reachable from our environment | unverified |
| Levelset / other lien-deadline calculators | the lien-deadline URLs we tried returned 404 | Alberta/Ontario coverage: unverified |
| Law-firm calculators | not checked | unverified |

We do not claim to beat any of them on features we could not inspect. What this tool offers is narrow and checkable: free, offline, open source, cited to sections, and honest about its gaps. It is not a payment platform, a document-management system or a source of legal advice.

## Notes

- All offsets are **calendar days** from the anchor date you pass in.
- `--json` includes the scope checklist and the date the rules were read.
- Pair with `clearancewatch` for the coverage side of job compliance.

## License

MIT. Use it, ship it, no warranty.
