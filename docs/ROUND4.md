# Round 4 review: the stranger's first hour

Honest note on method: this environment could not spawn independent sub-agents, so one reviewer played every role below. Treat the "specialists" as hats, not as separate people. Each finding lists the command that showed it. Nothing was run on Windows or macOS.

## Specialists and findings

| Hat | Finding | Proving command |
|---|---|---|
| First-time user (README only, clean venv) | README tells pip users to run `python tools/verify_sources.py`; the file is not in the wheel | `unzip -l dist/*.whl` |
| First-time user | `python -m holdbackcalc` fails | `python -m holdbackcalc --version` in the clean venv |
| First-time user | running with no command shows a 400-character usage line | `holdbackcalc` |
| Release engineer | author was a GitHub handle; no project URLs; thin classifiers; no `py.typed`; `setuptools>=68` cannot build an SPDX `license = "MIT"` (needs 77+); sdist lacked CHANGELOG | `python -m build`, `unzip -p dist/*.whl '*/METADATA'` |
| Release engineer | `on_annual_from_contract` not importable from the package | `python -c "import holdbackcalc as h; h.on_annual_from_contract"` |
| Registry check | PyPI has only 0.1.0; repo is 0.2.0 | `pip index versions holdbackcalc` |
| Supply chain | zero runtime dependencies (clean venv `pip list` shows only the package). The source checker downloaded without a size cap and leaked temp files | `uv pip list`, code read |
| Hostile-input fuzzer | 3,000 random argument combinations: no crash. Closed pipe and full disk gave tracebacks | `holdbackcalc batch jobs.csv \| head -1`, `... > /dev/full` |
| Hostile-input fuzzer | `--within -5` accepted | `holdbackcalc --today 2026-07-01 --within -5 ...` |
| CLI integrator | `--out` left an empty file when the run failed, blocking the retry | `holdbackcalc --out o.txt on-lien-events --role contractor; ls` |
| Concurrency | 12 parallel `--out` to one name: exactly 1 wins, 11 clean errors | shell loop |
| Windows reviewer (static only) | `--ics` writes CRLF through a text stdout, which Windows turns into CR CR LF; PowerShell `>` UTF-16 already handled by `--out`; no `shell=True`, `os.replace` or signals used; temp file in the checker is closed before use | code read, emulated stream test |
| Locale | `strftime("%a")` follows the machine locale | code read |
| Performance | import 0.1 s cold, 10,000-job batch 0.54-0.59 s; unchanged | `python tools/bench.py` |
| Competitor maintainer | Osler's free Ontario calculator covers only the 7/14/28-day invoice clock and rolls holiday deadlines forward; BuilderLien (Ontario, paid, was a waitlist). Neither covers Alberta, holdback or liens in one tool as far as their pages show | WebFetch, 2026-11-07 |

## Scored ideas (value / differentiation / effort / risk each 1-5; higher value and differentiation are better, higher effort and risk are worse)

| # | Idea | Value | Diff. | Effort | Risk | Status |
|---|---|---|---|---|---|---|
| 1 | Ship the source checker inside the package (`verify-sources`) | 5 | 5 | 2 | 1 | DONE |
| 2 | Quiet handling of closed pipe / disk full / Ctrl-C / unexpected bug | 5 | 2 | 2 | 1 | DONE |
| 3 | Remove empty `--out` file on failure | 4 | 1 | 1 | 1 | DONE |
| 4 | `python -m holdbackcalc` | 3 | 1 | 1 | 1 | DONE |
| 5 | Complete packaging metadata, `py.typed`, setuptools 77 | 5 | 1 | 1 | 1 | DONE |
| 6 | Tests that run every README command | 5 | 2 | 2 | 1 | DONE |
| 7 | CI on Windows + clean-venv wheel smoke test + mypy | 5 | 2 | 2 | 1 | DONE (cannot be run here) |
| 8 | CRLF-safe `.ics` on Windows | 4 | 1 | 1 | 1 | DONE (emulated) |
| 9 | `batch -` (stdin) | 3 | 2 | 1 | 1 | DONE |
| 10 | `schema_version` in JSON | 4 | 2 | 1 | 1 | DONE |
| 11 | `--today today` | 2 | 1 | 1 | 1 | DONE |
| 12 | Locale-proof weekday names | 3 | 1 | 1 | 1 | DONE |
| 13 | Library usage example in README | 3 | 1 | 1 | 1 | DONE |
| 14 | Reject negative `--within` | 2 | 1 | 1 | 1 | DONE |
| 15 | Export `on_annual_from_contract` | 2 | 1 | 1 | 1 | DONE |
| 16 | Stable calendar UIDs surviving corrected dates | 3 | 3 | 3 | 3 | NOT-DONE (collides for same-named jobs) |
| 17 | French output | 3 | 4 | 4 | 3 | NOT-DONE (needs a fluent legal reviewer) |
| 18 | BC / other provinces | 4 | 4 | 5 | 5 | NOT-DONE (rules unverified; fail closed) |
| 19 | Web UI | 3 | 2 | 4 | 2 | NOT-DONE |
| 20 | Alberta Thanksgiving treatment | 2 | 2 | 2 | 4 | NOT-DONE (not in the Interpretation Act list) |
| 21 | Adjudication procedure deadlines | 3 | 4 | 4 | 4 | NOT-DONE |
| 22 | Read Ontario statute reliably in the checker (browser-rendered page) | 4 | 3 | 4 | 2 | NOT-DONE |
| 23 | Publish via trusted publishing from CI | 3 | 1 | 2 | 2 | NOT-DONE (needs Dan's PyPI settings) |
| 24 | Show the rolled date as an option like Osler does (`--roll`) | 2 | 2 | 2 | 4 | NOT-DONE (we plan to the earlier date on purpose) |

## Could not test
Windows and macOS (static review and emulation only; CI added). Python 3.10-3.12 were not run this round (3.9 and 3.13 were). The Ontario Act text could not be re-read: ontario.ca served a script shell, so the 20 Ontario rules were not re-verified; Alberta's 15 passed live. The legal meaning of each rule was not re-audited, only that the cited phrases still exist (Alberta). No upload to PyPI, no tag, no push. Competitor features beyond their landing pages are unverified.
