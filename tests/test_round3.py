import csv
import datetime as dt
import io
import json

import pytest

from holdbackcalc import batch, calc
from holdbackcalc.cli import main

D = dt.date


def lab(dl, label):
    return next(d for d in dl if d.label == label)


def run(capsys, *argv):
    rc = main(list(argv))
    return rc, capsys.readouterr()


# ---- legal logic -------------------------------------------------------------
def test_perfection_row_says_lien_must_be_preserved_first():
    for dl in (calc.on_lien(D(2026, 1, 1)), calc.on_lien_events("contractor", completed=D(2026, 1, 1))):
        assert "s.36(1)" in lab(dl, "perfect lien by (commence action)").basis


def test_trustee_role_cites_31_2_1_and_uses_earliest_event():
    dl = calc.on_lien_events("trustee", completed=D(2026, 3, 1), last_supply=D(2026, 2, 1))
    p = lab(dl, "preserve lien by")
    assert p.date == D(2026, 4, 2) and p.cite == "Construction Act s.31(2.1)"


@pytest.mark.parametrize("contract,first", [
    (D(2026, 1, 1), D(2027, 1, 1)),      # on/after in-force day: ordinary first anniversary
    (D(2026, 6, 15), D(2027, 6, 15)),
    (D(2025, 3, 15), D(2027, 3, 15)),    # pre-2026: second anniversary-date after 2026-01-01
    (D(2025, 12, 31), D(2027, 12, 31)),
    (D(2020, 1, 1), D(2028, 1, 1)),      # Jan 1 is not "after" Jan 1 2026 -> 2027-01-01, then 2028
])
def test_first_annual_anniversary_transition(contract, first):
    assert calc.on_first_annual_anniversary(contract) == first


def test_first_annual_rejects_feb_29():
    with pytest.raises(ValueError):
        calc.on_first_annual_anniversary(D(2024, 2, 29))


def test_annual_exact_window_from_actual_publication():
    dl = calc.on_annual_holdback(D(2027, 3, 15), published=D(2027, 3, 20))
    assert lab(dl, "payment window opens").date == D(2027, 5, 19)
    assert lab(dl, "latest payment of accrued holdback").date == D(2027, 6, 2)
    late = calc.on_annual_holdback(D(2027, 3, 15), published=D(2027, 4, 1))
    assert "AFTER" in lab(late, "notice actually published").basis


def test_annual_default_labels_do_not_claim_earliest():
    for d in calc.on_annual_holdback(D(2027, 3, 15)):
        assert "earliest payment" not in d.label


# ---- weekend / closed office --------------------------------------------------
def test_plan_by_is_last_business_day_before_weekend_or_holiday():
    ordinary = lab(calc.ab_lien(D(2026, 1, 9)), "register lien by")      # +60 = Tue 2026-03-10
    assert ordinary.date == D(2026, 3, 10) and ordinary.plan_by is None
    # Sunday 2026-03-01 (ON adjudication, 90 days after 2025-12-01): plan_by is Friday
    adj = lab(calc.on_adjudication(D(2026, 1, 1), [D(2025, 12, 1)]), "notice of adjudication by")
    assert adj.date == D(2026, 3, 1) and adj.plan_by == D(2026, 2, 27)
    # Monday holiday (Family Day 2026-02-16, ON): plan_by skips the weekend too -> Thursday
    fam = lab(calc.on_invoice_deficiency(D(2026, 2, 9)), "deficiency notice window closes")
    assert fam.date == D(2026, 2, 16) and fam.plan_by == D(2026, 2, 13)


def test_saturday_filing_deadline_is_flagged_but_not_moved():
    start = D(2026, 1, 1)
    sat = next(start + dt.timedelta(days=i) for i in range(14) if (start + dt.timedelta(days=i + 60)).weekday() == 5)
    d = lab(calc.ab_lien(sat), "register lien by")
    assert d.date.weekday() == 5 and d.closed_office and d.rolled is None and d.plan_by == d.date - dt.timedelta(days=1)
    assert not lab(calc.ab_invoice(sat), "payment due (owner → contractor)").closed_office


def test_json_has_weekday_plan_by_and_flag(capsys):
    rc, out = run(capsys, "--json", "ab-lien", "2026-01-05")
    row = json.loads(out.out)["schedule"][0]
    assert {"weekday", "plan_by", "closed_office_note"} <= set(row)


# ---- CLI ------------------------------------------------------------------------
def test_format_flags_are_mutually_exclusive(capsys):
    with pytest.raises(SystemExit):
        main(["--json", "--ics", "ab-invoice", "2026-01-01"])


GOOD = "project,command,date\nA,ab-invoice,2026-07-01\nB,ab-lien,2026-01-02\n"


def _w(tmp_path, data, name="j.csv"):
    p = tmp_path / name
    p.write_bytes(data if isinstance(data, bytes) else data.encode())
    return str(p)


def test_within_filters_and_needs_today(tmp_path, capsys):
    f = _w(tmp_path, GOOD)
    rc, _ = run(capsys, "--within", "5", "batch", f)
    assert rc == 2
    rc, out = run(capsys, "--json", "--today", "2026-07-10", "--within", "5", "batch", f)
    rows = json.loads(out.out)["schedule"]
    assert rows and all(r["days_left"] <= 5 for r in rows)
    assert not any(r["project"] == "A" and r["date"] == "2026-07-29" for r in rows)   # not due within 5 days
    rc, out = run(capsys, "--today", "2020-01-01", "--within", "1", "batch", f)
    assert "Nothing due" in out.out


def test_csv_output_neutralises_formulas(tmp_path, capsys):
    f = _w(tmp_path, 'project,command,date\n"=HYPERLINK(""http://x"")",ab-invoice,2026-01-05\n"@x",ab-invoice,2026-01-05\n')
    rc, out = run(capsys, "--csv", "batch", f)
    rows = list(csv.reader(io.StringIO(out.out)))
    assert rows[0][0] == "project"
    assert all(r[0].startswith("'") for r in rows[1:])
    assert not any(c[:1] in "=@" for r in rows for c in r if c)


def test_stale_rules_warning(capsys):
    rc, out = run(capsys, "--today", "2027-12-01", "ab-invoice", "2027-12-01")
    assert "WARNING" in out.out and "days ago" in out.out
    rc, out = run(capsys, "--today", "2026-11-08", "ab-invoice", "2026-11-08")
    assert "WARNING" not in out.out


def test_on_annual_first_command(capsys):
    rc, out = run(capsys, "--json", "on-annual-first", "2025-03-15")
    rows = json.loads(out.out)["schedule"]
    assert rows[0]["date"] == "2027-03-15" and "87.4(4)" in rows[0]["cite"]


# ---- batch hardening --------------------------------------------------------------
def test_semicolon_delimited_excel_file(tmp_path):
    rows = batch.read_rows(_w(tmp_path, "project;command;date\nA;ab-invoice;2026-01-05\n"))
    assert rows[0][0] == "A"


def test_utf16_with_bom(tmp_path):
    rows = batch.read_rows(_w(tmp_path, "project,command,date\nÉcole,ab-invoice,2026-01-05\n".encode("utf-16")))
    assert rows[0][0] == "École"


def test_giant_field_is_clean_error_not_traceback(tmp_path):
    big = 'project,command,date\n"' + "a" * 300_000 + '",ab-invoice,2026-01-05\n'
    with pytest.raises(batch.BatchError):
        batch.read_rows(_w(tmp_path, big))


def test_duplicate_columns_rejected(tmp_path):
    with pytest.raises(batch.BatchError):
        batch.read_rows(_w(tmp_path, "project,command,date,project\nA,ab-invoice,2026-01-05,B\n"))


def test_command_and_sector_case_insensitive(tmp_path):
    rows = batch.read_rows(_w(tmp_path, "project,command,date,sector\nA,AB-Lien,2026-01-05,Oil-Gas\n"))
    assert lab(rows[0][2], "register lien by").date == D(2026, 4, 5)


@pytest.mark.parametrize("bad", ["2026-W01-1", "２０２６-01-05", "20260105", "2026-1-05", " 2026-01-0５"])
def test_date_parser_is_strict(bad):
    with pytest.raises(ValueError):
        batch.parse_date(bad)


def test_date_hint_mentions_excel(tmp_path):
    with pytest.raises(batch.BatchError, match="Excel"):
        batch.read_rows(_w(tmp_path, "project,command,date\nA,ab-invoice,1/5/2026\n"))


def test_ics_mentions_plan_by_and_epoch_is_reproducible(monkeypatch):
    from holdbackcalc.ics import build_ics
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1700000000")
    items = [("P", "on-adjudication", calc.on_adjudication(D(2026, 1, 1), [D(2025, 12, 1)])[0])]
    a, b = build_ics(items), build_ics(items)
    assert a == b and "DTSTAMP:20231114T221320Z" in a and "last business day" in a.replace("\r\n ", "")


def test_out_flag_writes_utf8_and_refuses_overwrite(tmp_path, capsys):
    target = str(tmp_path / "o.ics")
    assert main(["--out", target, "--ics", "ab-invoice", "2026-06-30"]) == 0
    raw = open(target, "rb").read()
    assert raw.startswith(b"BEGIN:VCALENDAR\r\n")
    assert main(["--out", target, "--ics", "ab-invoice", "2026-06-30"]) == 2


def test_legacy_console_does_not_crash(monkeypatch, capsys):
    import io as _io
    import sys
    buf = _io.TextIOWrapper(_io.BytesIO(), encoding="ascii")
    monkeypatch.setattr(sys, "stdout", buf)
    assert main(["ab-invoice", "2026-06-30"]) == 0       # the table contains arrows and dashes
