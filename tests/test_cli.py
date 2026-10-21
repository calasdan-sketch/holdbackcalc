"""CLI tests."""
import json

import pytest

from holdbackcalc.cli import main


def test_ab_invoice_json(capsys):
    assert main(["--json", "ab-invoice", "2026-01-01"]) == 0
    data = json.loads(capsys.readouterr().out)
    labels = [d["label"] for d in data["schedule"]]
    assert any("payment due" in l for l in labels)
    assert data["note"].startswith("administrative")


def test_on_lien_table(capsys):
    assert main(["on-lien", "2026-01-01"]) == 0
    out = capsys.readouterr().out
    assert "2026-03-02" in out and "2026-05-31" in out
    assert "not legal advice" in out


def test_on_holdback_and_annual(capsys):
    assert main(["on-holdback", "2026-01-01"]) == 0
    assert "2026-03-16" in capsys.readouterr().out
    assert main(["on-annual", "2026-01-01"]) == 0
    out = capsys.readouterr().out
    assert "publish annual-release notice by" in out and "2026-03-30" in out


def test_ab_sub_payment_and_invoice(capsys):
    assert main(["ab-sub-payment", "2026-03-02"]) == 0
    assert "2026-03-09" in capsys.readouterr().out
    assert main(["on-invoice", "2026-06-01"]) == 0
    assert "2026-06-08" in capsys.readouterr().out


def test_what_we_dont_encode(capsys):
    assert main(["what-we-dont-encode"]) == 0
    out = capsys.readouterr().out
    assert "AB: statutory holdback" in out
    assert "https://www.ontario.ca/laws/statute/90c30" in out


def test_bad_date_rejected():
    with pytest.raises(SystemExit):
        main(["ab-invoice", "not-a-date"])


def test_missing_subcommand():
    with pytest.raises(SystemExit):
        main([])
