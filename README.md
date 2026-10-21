# holdbackcalc

**Prompt-payment and holdback deadlines for Alberta and Ontario construction work — verified rules only.** Give it an anchor date (invoice received, payment received, lien trigger event, contract anniversary); it gives back a dated schedule you can drop into a calendar or CI reminder.

> **Not legal advice.** An administrative date calculator. Every constant was verified against official sources in October 2026 — and everything we could *not* verify is deliberately **not encoded**: run `holdbackcalc what-we-dont-encode` to see the holes.

## Install

```bash
pip install holdbackcalc
```

## Alberta

```bash
holdbackcalc ab-invoice 2026-01-01        # proper invoice received
holdbackcalc ab-sub-payment 2026-03-02    # owner's payment received by the contractor
```

| Deadline | Rule |
|---|---|
| dispute notice by: **received + 14 days** | owner must give notice of dispute within 14 calendar days |
| payment due (owner → contractor): **received + 28 days** | proper invoice payable within 28 calendar days |
| payment due (contractor → sub): **owner payment + 7 days** | pay the sub within 7 days of receiving the owner's payment |

Deliberately blank: **holdback release** — Alberta's statutory holdback percentage and release clock could not be verified from official text, so no date is invented.

## Ontario

```bash
holdbackcalc on-lien 2026-01-01           # from the trigger event (e.g. publication of substantial performance)
holdbackcalc on-holdback 2026-01-01       # 10% holdback schedule from the same event
holdbackcalc on-invoice 2026-06-01        # proper-invoice deficiency window (2026 rules)
holdbackcalc on-annual 2026-01-01         # annual holdback release, contracts ≥ Jan 1 2026
```

| Deadline | Rule |
|---|---|
| preserve lien by: **event + 60 days** | 60-day lien preservation period |
| perfect lien by: **preserve deadline + 90 days** | 90 days to commence the action |
| owner must pay holdback: **event + 74 days** | lien period (60) + owner's 14 days to pay after expiry |
| pass downstream: **payment + 14 days** | contractor/sub has 14 days after receipt |
| deficiency notice: **invoice + 7 days** (2026) | otherwise the invoice is deemed proper |
| annual notice: **anniversary + 14 days** (2026) | payment window opens at notice +60, closes at notice +74 |

`--json` gives a machine-readable schedule for automation.

## What it does NOT encode

```
$ holdbackcalc what-we-dont-encode
  - AB: statutory holdback percentage and the post-substantial-performance release clock
  - AB: substantial-performance payment deadline and base-building/partial-performance treatment
  - AB: detailed adjudication filing deadlines
  - ON: any 'first 90 days of contract' short lien period (not found in the current Act)
  - ON: a general 45-day pleadings deadline (not found in the current Act)
```

These were checked against official text in October 2026 and **could not be confirmed**. A calculator that guesses a legal deadline is worse than no calculator.

## Sources

- Alberta prompt payment overview: https://www.alberta.ca/prompt-payment-rules-for-construction-industry
- Prompt Payment and Adjudication Regulation, Alta Reg 23/2022: https://open.alberta.ca/publications/2022_023
- Ontario Construction Act (consolidated to Jan 1, 2026): https://www.ontario.ca/laws/statute/90c30
- 2026 amendments summary: https://cassels.com/insights/the-construction-act-whats-new-in-the-new-year/

## Notes

- All offsets are **calendar days** from the anchor date you pass in.
- Deadlines that depend on a later event (e.g. pass-down timing) print as reminders with no date unless you supply the trigger.
- Pair with `clearancewatch` for the coverage side of job compliance.

## License

MIT-style: use it, ship it, no warranty.
