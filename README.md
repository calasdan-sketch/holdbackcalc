# holdbackcalc

**Prompt-payment, holdback and lien deadlines for Alberta and Ontario construction work. Every rule is cited to a section of the official text and re-checkable with one command; anything we could not verify is left out on purpose.** Give it a date; get a dated schedule, a calendar file, or a whole portfolio of jobs sorted by what is due next.

> **Not legal advice.** This is an administrative date calculator. Lien and holdback deadlines are strict; a missed date can cost the claim. Statutes and your contract may differ from the general rules encoded here (public works, pre-2018 Ontario contracts, oil/gas and concrete special periods, notices you did or did not send). Confirm anything that matters with a construction lawyer in the right province. The tool prints this reminder and a scope checklist with every result.

## Install and first run

```bash
pip install holdbackcalc            # Python 3.9+, no dependencies
holdbackcalc ab-invoice 2026-06-30
```

> The version on PyPI (0.1.0) is older than this repository (0.2.0, unreleased). Until 0.2.0 is published, commands such as `batch`, `--csv`, `on-annual-first`, `on-lien-events` and `verify-sources` need a checkout: `git clone https://github.com/calasdan-sketch/holdbackcalc && pip install ./holdbackcalc`. Check what you have with `holdbackcalc --version`.

```bash
holdbackcalc --version
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
| AB | `ab-holdback COMPLETED [--certificate DATE] [--sector ...] [--amount DOLLARS]` | 10% major/minor lien fund retention and earliest safe-payment dates; with `--amount`, also the 10% in dollars (rounded to the cent) |
| AB | `ab-adjudication DATE` | last day to give notice of adjudication (30 days after final payment) |
| ON | `on-prompt-payment DATE` | deficiency notice (+7), owner's notice of non-payment (+14), payment (+28), pass-through (+35) |
| ON | `on-sub-payment DATE` | contractor pays subs (+7) |
| ON | `on-lien-events --role contractor\|other\|trustee ...` | s.31 lien expiry from the **earliest applicable event** (certificate published, completion, last supply, subcontract certified), then the 90-day perfection date |
| ON | `on-lien DATE` | simple form: one trigger event, +60 then +90 |
| ON | `on-holdback DATE [--amount DOLLARS]` / `on-annual DATE [--published DATE]` | holdback release after the lien period; annual release (2026 rules), exact window once you know the notice date |
| ON | `on-annual-first CONTRACT_DATE` | first annual release for a contract, including the pre-2026 transition (s.87.4(4); our reading needs counsel) |
| ON | `on-invoice DATE` | 7-day proper-invoice deficiency window |
| ON | `on-adjudication DATE [--also DATE ...]` | last day for notice of adjudication (90 days; earliest date wins for subcontracts) |
| both | `batch jobs.csv` | many jobs at once: `project,command,date[,certificate,registered,sector]` |
| both | `batch -` | same, reading the CSV from standard input |
| both | `rules` | every encoded rule with citation and source URL |
| both | `verify-sources` | re-check every rule against the official statute text (needs network) |
| both | `what-we-dont-encode` | the holes, listed |

Global flags go before the command: `--json`, `--ics` (calendar file with 7-day and 1-day alarms), `--csv` (spreadsheet-safe), `--out FILE` (UTF-8 file; use it instead of `>` in Windows PowerShell, which writes UTF-16), `--today YYYY-MM-DD` or `--today today` (days left, `OVERDUE`), `--within N` (with `--today`: only what is overdue or due in the next N days).

Every date shows its weekday. A date on a weekend or holiday also shows the **last business day to act**; a Saturday filing deadline is flagged because the statutes may extend it if the office is closed (never computed, since we cannot know your office's hours). Batch CSVs may be UTF-8, UTF-16 or Excel's Windows-1252, comma- or semicolon-separated (Excel in French and other locales); dates must be `YYYY-MM-DD`. Output carries a warning once the rules are more than 180 days past their last check.

`--amount` takes plain digits with at most two decimals (`125000.50`); the 10% is applied to the number you give (Alberta: value of the work actually done, PPCLA s.18(1); Ontario: price of the services or materials, Construction Act s.22(1)). You choose the base, for example whether GST/HST is in it; ask your accountant. Rounding is half-up to the cent (the texts we read do not state a rounding rule: unverified).

Exit status: `0` success, `2` bad input (plain-English message on stderr, nothing on stdout, no traceback), `70` a bug in holdbackcalc (please report it), `130` Ctrl-C. `verify-sources` exits `1` if a rule's text is not found and `3` if nothing could be checked at all (never a silent pass). `--json` output carries `schema_version` (currently 1), `tool_version`, and every schedule row has a stable `id` (a slug of the label; key scripts on it, because labels may be reworded). With `--within`, an empty result stays valid JSON / calendar / CSV and the "nothing due" message goes to stderr. Results go to stdout, messages and warnings to stderr.

```bash
holdbackcalc --ics batch jobs.csv > deadlines.ics         # import into Outlook / Google / Apple Calendar (all-day events; some calendar apps ignore imported reminders: not tested here)
holdbackcalc --today 2026-07-20 batch jobs.csv            # what is due or overdue, across all jobs
holdbackcalc on-lien-events --role other --supply-before-sp \
  --cert-published 2026-04-01 --completed 2026-05-15 --last-supply 2026-03-20
```

## Trust: how rules are verified

`holdbackcalc rules` lists 35 rules; each has a section citation, the official source URL and an "evidence phrase" that appears in that text. Re-check them yourself at any time:

```bash
holdbackcalc verify-sources    # downloads the official texts; PASS / FAIL / SKIPPED per rule
holdbackcalc verify-sources --from-dir DIR   # if a site (e.g. ontario.ca) serves a script shell: save the pages from a browser as ON_ACT.html, ON_LEG.html, AB_ACT.pdf, AB_REG.pdf, AB_INTERP.pdf
```

Alberta's PDFs need the free `pdftotext` program (poppler); without it those rules are SKIPPED. On 2026-11-07 a live run from our test machine gave 15 PASS for Alberta and 20 SKIPPED for Ontario (ontario.ca served a script shell), so the Ontario texts were not re-verified in the latest review round. A rule that cannot be checked is reported SKIPPED, never PASSED; a page that is clearly not the statute (too short) is SKIPPED too, not FAILED (before this round the Ontario page produced 16 false FAILs). A FAIL means the law may have changed.

Primary sources read on 2026-11-07:
Ontario [Construction Act](https://www.ontario.ca/laws/statute/90c30) (consolidation from Jan 1, 2026) and [Legislation Act, 2006](https://www.ontario.ca/laws/statute/06l21);
Alberta [Prompt Payment and Construction Lien Act](https://kings-printer.alberta.ca/documents/Acts/P26P4.pdf) (**current as of April 1, 2025**), [Regulation 23/2022](https://kings-printer.alberta.ca/documents/Regs/2022_023.pdf) (current as of Nov 26, 2025) and [Interpretation Act](https://kings-printer.alberta.ca/documents/Acts/I08.pdf); the Alberta [prompt-payment overview page](https://www.alberta.ca/prompt-payment-rules-for-construction-industry). Amendments after those consolidation dates were **not** checked.

## What it does NOT encode

```
$ holdbackcalc what-we-dont-encode
```
Includes: Alberta amendments after the consolidation dates above; whether Thanksgiving is a holiday for Alberta time limits; Saturday and closed-office extensions; Ontario workers' trust fund liens; Ontario trust-fund liens other than the expiry date (`--role trustee`), general liens and AFP project agreements; the wording of the pre-2026 annual-release transition is ambiguous (we encode one reading, `on-annual-first`); adjudication procedure deadlines beyond the filing limits; and whether *your* job is in scope. Wrong-province or wrong-contract-date results are the biggest practical risk: read the scope checklist.

## Honest comparison

Measured on this repo (re-run `python tools/bench.py`; `pytest -q`):

| | v0.1.0 | v0.2.0 (this unreleased line) |
|---|---|---|
| Rules encoded | 11 constants, no citations | 35 rules, each cited + machine-checkable (30 before the latest review round) |
| Alberta holdback / lien / adjudication | listed as unverified | encoded from the Act text (with sector periods) |
| Ontario prompt payment (28/14/7/35) | missing | encoded |
| Ontario lien trigger | one date, no role | earliest applicable event by role (s.31), incl. workers' trust fund |
| Ontario annual holdback | one anchor | exact window from the real notice date; pre-2026 transition command |
| Holiday / weekend awareness | none | holidays rolled (both provinces), last business day to act, Saturday-filing flag |
| Multi-job view, exports | none | `batch` (UTF-8/16, Excel, `;`), `--ics`, `--csv`, `--within`, `--out` |
| Tests | 15 | 223 (about 219 run with no extras; a few need network or optional packages) (hand-checked golden dates, golden files for text/JSON/CSV/calendar, mutation-style checks of every rule number, seeded property tests, differential checks, calendar conformance, CLI fuzz, hostile CSV, README commands, packaging) |
| 10,000-job batch | n/a | 0.5-0.65 s here (about 15,000-19,000 jobs/s; noisy shared machine; round 5 changed no hot path) |

Against other tools (all **unverified** as to features; we checked only that the pages below were reachable):

| Tool | What we could check | Everything else |
|---|---|---|
| Procore Pay (procore.com/pay) | US-English page text (fetched 2026-11-07, no JS) mentions liens, and does not mention Alberta, Ontario, holdback or prompt payment | Canadian coverage, pricing, deadline features: unverified |
| Osler "Owner Payment Date Calculator" (osler.com) | Ontario only; one input (date the owner received a proper invoice); three outputs (deficiency notice, notice of non-payment, payment); moves a deadline on a holiday to the next business day; page says "at your own risk" (read 2026-11-07; not re-fetched 2026-11-08, the page request failed) | Pricing and anything beyond that page: unverified. Note the difference: we print the plain-arithmetic date and show the rolled date separately |
| BuilderLien (builderlien-landing.pages.dev) | Ontario only; paid ($99 / $199 per month listed); still a waitlist page with a February 2026 launch date when re-read 2026-11-08 | Whether it launched, and its accuracy: unverified |
| Norton Rose Fulbright "PPCLA Advisor" | exists (search result 2026-11-07); we did not open it | Alberta coverage and features: unverified |
| Textura | site not reachable from our environment | unverified |
| Levelset / other lien-deadline calculators | the lien-deadline URLs we tried returned 404; a 2026-11-07 web search for an AB/ON lien or holdback calculator surfaced law-firm explainers and PDFs (e.g. Bennett Jones, Miller Thomson), not calculators; we did not read them in full | Alberta/Ontario coverage: unverified |
| Law-firm calculators | not checked | unverified |

We do not claim to beat any of them on features we could not inspect. What this tool offers is narrow and checkable: free, offline, open source, cited to sections, and honest about its gaps. It is not a payment platform, a document-management system or a source of legal advice.

## Use from scripts or AI agents

`--json` is the interface: stable `schema_version`, per-row `id`, exit codes above, errors only on stderr. Example: `holdbackcalc --json --today today --within 14 batch jobs.csv` lists what is overdue or due in two weeks. There is no MCP server or hook; none is claimed.

## Use as a Python library

```python
import datetime as dt
from holdbackcalc import ab_invoice
for d in ab_invoice(dt.date(2026, 6, 30)):
    print(d.date, d.label, d.cite)
```

## Notes

- All offsets are **calendar days** from the anchor date you pass in.
- `--json` includes the scope checklist and the date the rules were read.
- Pair with `clearancewatch` for the coverage side of job compliance.

## License

MIT, copyright 2026 Calas Automations Inc. Use it, ship it, no warranty.
