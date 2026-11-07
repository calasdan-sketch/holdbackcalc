import datetime as dt
import json
import random
import string

import pytest

from holdbackcalc import batch
from holdbackcalc.calc import ab_invoice, on_lien_events
from holdbackcalc.cli import main
from holdbackcalc.ics import build_ics
from holdbackcalc.textsafe import clean

D = dt.date
STAMP = dt.datetime(2026, 1, 1, 0, 0, 0)


# ---------------- text safety
def test_clean_strips_terminal_and_bidi_tricks():
    evil = "Job\x1b[31m RED \x07‮evil​⁦x⁩\x00end\nline"
    out = clean(evil)
    assert "\x1b" not in out and "\x07" not in out and "\x00" not in out
    for ch in "‮​⁦⁩":
        assert ch not in out
    assert "\n" not in out


def test_clean_caps_length():
    assert len(clean("a" * 10_000)) <= 120


# ---------------- ICS
def test_ics_is_wellformed_and_deterministic():
    items = [("Tower A", "ab-invoice", d) for d in ab_invoice(D(2026, 1, 1))]
    a, b = build_ics(items, STAMP), build_ics(items, STAMP)
    assert a == b
    assert a.startswith("BEGIN:VCALENDAR\r\n") and a.endswith("END:VCALENDAR\r\n")
    assert a.count("BEGIN:VEVENT") == a.count("END:VEVENT") == 3     # undated placeholder skipped
    assert "DTSTART;VALUE=DATE:20260115" in a and "DTEND;VALUE=DATE:20260116" in a
    assert "not legal advice" in a
    assert a.count("BEGIN:VALARM") == 4            # two hard events x (7d, 1d); reminder has none
    assert "\n" not in a.replace("\r\n", "")


def test_ics_escapes_and_folds():
    class Dl:  # minimal stand-in
        pass
    from holdbackcalc.calc import Deadline
    d = Deadline("x; y, z", D(2026, 5, 5), "line1\nline2 \\ end " + "é" * 100, 0, True, "cite")
    out = build_ics([("P\x1b[2J,;", "c", d)], STAMP)
    assert "\x1b" not in out
    assert "x\\; y\\, z" in out and "\\n" in out
    for line in out.split("\r\n"):
        assert len(line.encode("utf-8")) <= 75
    # unfolding must restore valid UTF-8 text
    out.replace("\r\n ", "").encode("utf-8").decode("utf-8")


def test_ics_cli(capsys):
    assert main(["--ics", "on-lien", "2026-01-01"]) == 0
    out = capsys.readouterr().out
    assert "SUMMARY:preserve lien by" in out and "DTSTART;VALUE=DATE:20260302" in out


# ---------------- batch
def _write(tmp_path, text, name="jobs.csv", mode="w"):
    p = tmp_path / name
    if isinstance(text, bytes):
        p.write_bytes(text)
    else:
        p.write_text(text, encoding="utf-8")
    return str(p)


GOOD = ("project,command,date,certificate,registered,sector\n"
        "Tower A,ab-invoice,2026-06-30,,,\n"
        "Plant B,ab-lien,2026-10-15,,2026-12-01,concrete\n"
        "School C,on-prompt-payment,2026-07-15,,,\n")


def test_batch_merges_and_sorts(tmp_path, capsys):
    assert main(["--json", "--today", "2026-07-20", "batch", _write(tmp_path, GOOD)]) == 0
    rows = json.loads(capsys.readouterr().out)["schedule"]
    dates = [r["date"] for r in rows if r["date"]]
    assert dates == sorted(dates)
    first = rows[0]
    assert first["project"] == "Tower A" and first["days_left"] == -6   # 2026-07-14 is 6 days before today
    assert any(r["project"] == "Plant B" and r["date"] == "2027-05-30" for r in rows)


def test_batch_table_marks_overdue(tmp_path, capsys):
    main(["--today", "2026-08-10", "batch", _write(tmp_path, GOOD)])
    out = capsys.readouterr().out
    assert "OVERDUE" in out and "Tower A" in out


@pytest.mark.parametrize("body", [
    "project,command,date\nA,nope,2026-01-01\n",                       # unknown command
    "project,command,date\nA,ab-invoice,2026-13-01\n",                 # impossible date
    "project,command,date\nA,ab-invoice,1999-01-01\n",                 # year out of range
    "project,command,date\nA,ab-invoice,2026-01-01,extra\n",           # too many fields
    "project,command,date,evil\nA,ab-invoice,2026-01-01,x\n",          # unknown column
    "project,command\nA,ab-invoice\n",                                 # missing column
    "project,command,date,sector\nA,ab-lien,2026-01-01,mining\n",      # bad sector
    "project,command,date\n",                                          # no rows
    "project,command,date\nA,ab-invoice,２０２６-01-01\n",              # full-width digits
])
def test_batch_bad_input_fails_closed(tmp_path, capsys, body):
    assert main(["batch", _write(tmp_path, body)]) == 2
    cap = capsys.readouterr()
    assert cap.out == ""                              # no partial schedule on stdout
    assert "holdbackcalc: error" in cap.err


def test_batch_one_bad_row_rejects_all(tmp_path, capsys):
    body = "project,command,date\nGood,ab-invoice,2026-01-01\nBad,ab-invoice,2026-02-30\n"
    assert main(["batch", _write(tmp_path, body)]) == 2
    err = capsys.readouterr().err
    assert "line 3" in err


def test_batch_binary_nul_and_bad_utf8(tmp_path):
    with pytest.raises(batch.BatchError):
        batch.read_rows(_write(tmp_path, b"project,command,date\nA\x00,ab-invoice,2026-01-01\n"))
    # non-UTF-8 bytes are read as Windows-1252 (what Excel writes), with a stderr note
    rows = batch.read_rows(_write(tmp_path, b"project,command,date\nCaf\xe9,ab-invoice,2026-01-01\n", "b.csv"))
    assert rows[0][0] == "Café"


def test_batch_huge_file_rejected(tmp_path):
    big = "project,command,date\n" + "A,ab-invoice,2026-01-01\n" * 400_000
    with pytest.raises(batch.BatchError):
        batch.read_rows(_write(tmp_path, big))


def test_batch_row_cap(tmp_path):
    body = "project,command,date\n" + "A,ab-invoice,2026-01-01\n" * (batch.MAX_ROWS + 1)
    with pytest.raises(batch.BatchError):
        batch.read_rows(_write(tmp_path, body))


def test_batch_missing_file_and_directory(tmp_path):
    with pytest.raises(batch.BatchError):
        batch.read_rows(str(tmp_path / "nope.csv"))
    with pytest.raises(batch.BatchError):
        batch.read_rows(str(tmp_path))


def test_batch_project_name_is_sanitised(tmp_path, capsys):
    body = 'project,command,date\n"Evil\x1b[31m‮ job",ab-invoice,2026-01-01\n'
    assert main(["batch", _write(tmp_path, body)]) == 0
    out = capsys.readouterr().out
    assert "\x1b" not in out and "‮" not in out
    # Windows paths / BOM files
    p = _write(tmp_path, b"\xef\xbb\xbfproject,command,date\r\nWin,ab-invoice,2026-01-01\r\n", "w.csv")
    assert main(["batch", p]) == 0


# ---------------- CLI robustness / errors
def test_cli_errors_are_exit_2_not_tracebacks(capsys):
    assert main(["on-lien-events", "--role", "contractor"]) == 2            # no events
    assert "no applicable trigger" in capsys.readouterr().err


def test_cli_rejects_far_future_and_past_years():
    for bad in ("0001-01-01", "9999-12-31", "1999-12-31", "2101-01-01"):
        with pytest.raises(SystemExit):
            main(["ab-invoice", bad])


def test_on_lien_events_role_rules():
    # contractor ignores last_supply and sub-certified dates entirely
    d = on_lien_events("contractor", completed=D(2026, 5, 1), last_supply=D(2026, 1, 1),
                       subcontract_certified=D(2026, 1, 2))
    assert d[0].date == D(2026, 6, 30)
    # a certificate only counts when supply was on/before the certified SP date
    d = on_lien_events("contractor", completed=D(2026, 5, 1), cert_published=D(2026, 3, 1))
    assert d[0].date == D(2026, 6, 30)
    d = on_lien_events("contractor", completed=D(2026, 5, 1), cert_published=D(2026, 3, 1), supply_before_sp=True)
    assert d[0].date == D(2026, 4, 30)
    with pytest.raises(ValueError):
        on_lien_events("owner", completed=D(2026, 5, 1))


# ---------------- properties / fuzz (stdlib only)
def test_property_deadlines_never_precede_anchor_and_roll_is_later():
    from holdbackcalc import calc
    rnd = random.Random(7)
    funcs = [calc.ab_invoice, calc.ab_sub_payment, calc.ab_lien, calc.ab_holdback, calc.ab_adjudication,
             calc.on_lien, calc.on_holdback_release, calc.on_invoice_deficiency, calc.on_prompt_payment,
             calc.on_sub_payment, calc.on_annual_holdback, calc.on_adjudication]
    for _ in range(2000):
        a = D(2000, 1, 1) + dt.timedelta(days=rnd.randrange(0, 365 * 100))
        for f in funcs:
            for d in f(a):
                if d.date is not None:
                    assert d.date >= a
                    assert d.rolled is None or d.rolled > d.date
                    assert d.rolled is None or (d.rolled - d.date).days <= 4   # longest holiday run


def test_fuzz_cli_never_tracebacks(capsys):
    rnd = random.Random(11)
    cmds = ["ab-invoice", "ab-lien", "on-lien", "on-adjudication", "batch", "rules", "on-lien-events", "x"]
    alphabet = string.printable + "é‮\x1b"
    for _ in range(400):
        argv = [rnd.choice(cmds)] + ["".join(rnd.choice(alphabet) for _ in range(rnd.randrange(0, 14)))
                                     for _ in range(rnd.randrange(0, 3))]
        try:
            rc = main(argv)
            assert rc in (0, 2)
        except SystemExit as e:           # argparse usage errors are the only allowed exit path
            assert e.code in (0, 2)
        capsys.readouterr()
