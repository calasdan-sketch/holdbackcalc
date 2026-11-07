"""Golden vectors: expected dates written out by hand from a wall calendar, one per rule path."""
import json

import pytest

from holdbackcalc.cli import main

# (argv, {label: expected ISO date})
VECTORS = [
    (["ab-invoice", "2026-06-30"], {"dispute notice by (owner)": "2026-07-14",
                                    "payment due (owner → contractor)": "2026-07-28",
                                    "contractor pays subs if owner has not paid": "2026-08-04"}),
    (["ab-lien", "2026-10-15"], {"register lien by": "2026-12-14"}),
    (["ab-lien", "2026-10-15", "--sector", "oil-gas"], {"register lien by": "2027-01-13"}),
    (["ab-lien", "2026-10-15", "--sector", "concrete", "--registered", "2026-12-01"],
     {"register lien by": "2027-01-13", "commence action + register lis pendens by": "2027-05-30"}),
    (["ab-holdback", "2026-09-01", "--certificate", "2026-06-01"],
     {"major lien fund: retention/safe-payment date": "2026-07-31",
      "minor lien fund: retention/safe-payment date": "2026-10-31"}),
    (["ab-holdback", "2026-09-01", "--certificate", "2026-06-01", "--sector", "oil-gas"],
     {"major lien fund: retention/safe-payment date": "2026-08-30",
      "minor lien fund: retention/safe-payment date": "2026-11-30"}),
    (["ab-holdback", "2026-09-01"], {"major lien fund: retention/safe-payment date": "2026-10-31"}),
    (["ab-adjudication", "2026-08-31"], {"notice of adjudication by": "2026-09-30"}),
    (["on-prompt-payment", "2026-07-15"], {"deficiency notice window closes": "2026-07-22",
                                           "owner's notice of non-payment by": "2026-07-29",
                                           "payment due (owner → contractor)": "2026-08-12",
                                           "contractor pays subs if owner has not paid": "2026-08-19"}),
    (["on-sub-payment", "2026-07-15"], {"payment due (contractor → sub)": "2026-07-22"}),
    (["on-lien-events", "--role", "other", "--supply-before-sp", "--cert-published", "2026-04-01",
      "--completed", "2026-05-15", "--last-supply", "2026-03-20"],
     {"preserve lien by": "2026-05-19", "perfect lien by (commence action)": "2026-08-17"}),
    (["on-lien-events", "--role", "contractor", "--supply-before-sp", "--cert-published", "2026-04-01",
      "--completed", "2026-05-15"],
     {"preserve lien by": "2026-05-31", "perfect lien by (commence action)": "2026-08-29"}),
    (["on-lien-events", "--role", "contractor", "--completed", "2026-05-15", "--cert-published", "2026-04-01"],
     {"preserve lien by": "2026-07-14", "perfect lien by (commence action)": "2026-10-12"}),
    (["on-lien-events", "--role", "contractor", "--completed", "2026-05-15", "--terminated", "2026-05-01"],
     {"publish notice of termination by": "2026-05-08"}),
    (["on-adjudication", "2026-05-15"], {"notice of adjudication by": "2026-08-13"}),
    (["on-adjudication", "2026-05-15", "--also", "2026-04-10", "--also", "2026-03-20"],
     {"notice of adjudication by": "2026-06-18"}),
]


@pytest.mark.parametrize("argv,expected", VECTORS)
def test_golden(argv, expected, capsys):
    assert main(["--json"] + argv) == 0
    got = {r["label"]: r["date"] for r in json.loads(capsys.readouterr().out)["schedule"]}
    for label, date in expected.items():
        assert got[label] == date, (argv, label)
