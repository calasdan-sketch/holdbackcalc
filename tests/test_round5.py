"""Round 5: author pins, golden files for every output format, property-based and differential
tests, mutation-style sanity, calendar-file conformance, money amounts, machine-format discipline."""
import datetime as dt
import json
import os
import random
import re
import subprocess
import sys
import zipfile
from decimal import Decimal

import pytest

import holdbackcalc
from holdbackcalc import batch, calc, holidays, rules as R
from holdbackcalc.cli import main
from holdbackcalc.ics import build_ics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD = os.path.join(ROOT, "tests", "golden")
AUTHOR = "Calas Automations Inc."


def run(capsys, *argv):
    rc = main(list(argv))
    return rc, capsys.readouterr()


# ------------------------------------------------------------------ author line
def test_author_is_pinned_everywhere():
    py = open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8").read()
    assert f'authors = [{{ name = "{AUTHOR}" }}]' in py
    assert f'maintainers = [{{ name = "{AUTHOR}" }}]' in py
    assert "email" not in py.split("[project.urls]")[0]          # never invent an email
    lic = open(os.path.join(ROOT, "LICENSE"), encoding="utf-8").read()
    assert f"Copyright (c) 2026 {AUTHOR}" in lic.splitlines()[2]
    assert holdbackcalc.__author__ == AUTHOR
    assert AUTHOR in build_ics([]).splitlines()[2]               # PRODID


def test_no_handle_used_as_author_label():
    bad = re.compile(r"(copyright|author|maintainer)[^\n]*calasdan", re.I)
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ".mypy_cache", ".pytest_cache",
                                                ".ruff_cache", "holdbackcalc.egg-info", "dist", "build")]
        for f in files:
            if f.endswith((".py", ".md", ".toml", ".yml", ".csv", ".ics", ".txt", ".json")) or f == "LICENSE":
                if f == "test_round5.py":
                    continue
                txt = open(os.path.join(base, f), encoding="utf-8", errors="replace").read()
                assert not bad.search(txt), os.path.join(base, f)


# ------------------------------------------------------------------ golden files (all four formats)
CASES = {
    "batch": ["batch", os.path.join("tests", "golden", "jobs.csv")],
    "ab_holdback_amount": ["ab-holdback", "2026-09-01", "--certificate", "2026-06-01", "--amount", "125000.50"],
    "on_holdback_amount": ["on-holdback", "2026-05-15", "--amount", "80000"],
    "on_lien_events": ["on-lien-events", "--role", "other", "--supply-before-sp", "--cert-published",
                       "2026-04-01", "--completed", "2026-05-15", "--last-supply", "2026-03-20",
                       "--terminated", "2026-03-01"],
    "on_annual_published": ["on-annual", "2026-03-01", "--published", "2026-03-10"],
    "on_adjudication_sub": ["on-adjudication", "2026-05-15", "--also", "2026-04-10"],
}
FORMATS = {"text": [], "json": ["--json"], "csv": ["--csv"], "ics": ["--ics"]}


def _render(name, fmt, capsys, monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1767225600")         # fixed DTSTAMP: 2026-01-01T00:00:00Z
    monkeypatch.chdir(ROOT)
    rc = main(FORMATS[fmt] + ["--today", "2026-07-20"] + CASES[name])
    cap = capsys.readouterr()
    assert rc == 0 and cap.err == ""
    return cap.out


@pytest.mark.parametrize("fmt", sorted(FORMATS))
@pytest.mark.parametrize("name", sorted(CASES))
def test_golden_file(name, fmt, capsys, monkeypatch):
    got = _render(name, fmt, capsys, monkeypatch)
    ext = {"text": "txt"}.get(fmt, fmt)
    path = os.path.join(GOLD, f"{name}.{ext}")
    if os.environ.get("UPDATE_GOLDEN") == "1":                    # maintainers only; review the diff by hand
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(got)
    with open(path, encoding="utf-8", newline="") as fh:
        assert got == fh.read()


# ------------------------------------------------------------------ mutation-style sanity
def _all_golden(capsys, monkeypatch):
    out = {}
    for name in CASES:
        for fmt in ("json", "ics"):
            out[(name, fmt)] = _render(name, fmt, capsys, monkeypatch)
    return out


def _golden_text(name, fmt):
    ext = {"text": "txt"}.get(fmt, fmt)
    with open(os.path.join(GOLD, f"{name}.{ext}"), encoding="utf-8", newline="") as fh:
        return fh.read()


# ON_OWNER_PAYMENT_AFTER_LIEN_DAYS only feeds the derived TOTAL constant at import time (checked below)
NUMERIC = sorted(n for n in dir(R) if re.fullmatch(r"(AB|ON)_[A-Z0-9_]*(DAYS|RATE)", n)
                 and n != "ON_OWNER_PAYMENT_AFTER_LIEN_DAYS")


def test_derived_constant_matches_its_parts():
    assert R.ON_OWNER_PAYMENT_TOTAL_DAYS == R.ON_LIEN_PRESERVE_DAYS + R.ON_OWNER_PAYMENT_AFTER_LIEN_DAYS


@pytest.mark.parametrize("const", NUMERIC)
def test_golden_files_notice_a_changed_rule_constant(const, capsys, monkeypatch):
    """If any rule number moved by one, the golden files must fail (else that number is untested)."""
    old = getattr(R, const)
    monkeypatch.setattr(R, const, old + (1 if isinstance(old, int) else 0.01))
    changed = any(_render(n, "json", capsys, monkeypatch) != _golden_text(n, "json") for n in CASES)
    assert changed, f"{const} is not pinned by any golden file"


@pytest.mark.parametrize("patch", ["no_easter_monday", "no_good_friday", "victoria_off_by_week",
                                   "no_boxing_shift", "no_sunday_rule"])
def test_golden_or_vectors_notice_broken_holiday_logic(patch, monkeypatch):
    """Holiday logic mutants must be caught by the hand-written holiday vectors below."""
    real_common = holidays._common
    if patch == "no_easter_monday":
        monkeypatch.setattr(holidays, "_common", lambda y: real_common(y) - {holidays._easter(y) + dt.timedelta(days=1)})
    elif patch == "no_good_friday":
        monkeypatch.setattr(holidays, "_common", lambda y: real_common(y) - {holidays._easter(y) - dt.timedelta(days=2)})
    elif patch == "victoria_off_by_week":
        monkeypatch.setattr(holidays, "_victoria_day", lambda y: real_vd(y) + dt.timedelta(days=7))
    elif patch == "no_boxing_shift":
        monkeypatch.setattr(holidays, "_alberta", lambda y: real_common(y) | {dt.date(y, 7, 1), dt.date(y, 12, 26)})
    elif patch == "no_sunday_rule":
        monkeypatch.setattr(holidays, "is_holiday", lambda j, d: d in holidays.holidays(j, d.year))
    holidays._cache.clear()
    try:
        with pytest.raises(AssertionError):
            _check_hand_holidays()
    finally:
        holidays._cache.clear()


real_vd = holidays._victoria_day


# ------------------------------------------------------------------ hand-known holiday vectors
def _check_hand_holidays():
    D = dt.date
    # Easter Sundays from published tables (2024-03-31, 2025-04-20, 2026-04-05, 2027-03-28, 2030-04-21)
    for y, e in [(2024, D(2024, 3, 31)), (2025, D(2025, 4, 20)), (2026, D(2026, 4, 5)),
                 (2027, D(2027, 3, 28)), (2030, D(2030, 4, 21))]:
        assert holidays._easter(y) == e
    for j in ("AB", "ON"):
        assert holidays.is_holiday(j, D(2026, 4, 3))        # Good Friday 2026
        assert holidays.is_holiday(j, D(2026, 4, 6))        # Easter Monday 2026
        assert holidays.is_holiday(j, D(2026, 5, 18))       # Victoria Day 2026 (Monday before May 25)
        assert holidays.is_holiday(j, D(2025, 5, 19))       # Victoria Day 2025
        assert not holidays.is_holiday(j, D(2026, 5, 25))
        assert holidays.is_holiday(j, D(2026, 9, 7))        # Labour Day 2026
        assert holidays.is_holiday(j, D(2026, 2, 16))       # Family Day 2026 (3rd Monday of February)
        assert holidays.is_holiday(j, D(2026, 11, 11))
        assert holidays.is_holiday(j, D(2026, 7, 5))        # a Sunday
    assert holidays.is_holiday("ON", D(2026, 10, 12))       # Thanksgiving 2026 (Ontario list)
    assert not holidays.is_holiday("AB", D(2026, 10, 12))   # not in the Alberta Interpretation Act list
    # Alberta Interpretation Act s.28(1)(x)(iv): Dec 26, or Dec 27 when Dec 26 is a Sunday or Monday
    assert holidays.is_holiday("AB", D(2026, 12, 26))       # Saturday
    assert holidays.is_holiday("AB", D(2027, 12, 27))       # Dec 26 2027 is a Sunday
    assert holidays.is_holiday("AB", D(2022, 12, 27))       # Dec 26 2022 is a Monday
    assert not holidays.is_holiday("AB", D(2022, 12, 26))


def test_hand_known_holidays():
    holidays._cache.clear()
    _check_hand_holidays()


# ------------------------------------------------------------------ property-based (seeded; no dependency)
def _rand_date(rng):
    return dt.date(2000, 1, 1) + dt.timedelta(days=rng.randrange(0, 365 * 100 + 25))


def _outputs_for(rng):
    d = _rand_date(rng)
    cert = d - dt.timedelta(days=rng.randrange(0, 200)) if rng.random() < .5 else None
    reg = d + dt.timedelta(days=rng.randrange(0, 90)) if rng.random() < .5 else None
    sector = rng.choice(calc.SECTORS)
    cmd = rng.choice(batch.BATCH_COMMANDS)
    return d, cmd, batch.run(cmd, d, certificate=cert, registered=reg, sector=sector)


def test_invariants_over_random_inputs():
    rng = random.Random(20261108)
    for _ in range(3000):
        anchor, cmd, dls = _outputs_for(rng)
        jur = "AB" if cmd.startswith("ab-") else "ON"
        ids = [d.id for d in dls]
        assert len(ids) == len(set(ids)), (cmd, ids)
        for d in dls:
            assert re.fullmatch(r"[a-z0-9_]+", d.id)
            if d.date is None:
                continue
            assert d.cite and d.basis and d.label
            if not d.hard and d.plan_by is None:      # informational rows (anniversaries) carry no weekend logic
                continue
            if d.rolled:
                assert d.rolled > d.date and not holidays.is_holiday(jur, d.rolled)
                assert holidays.is_holiday(jur, d.date)
            if d.plan_by:
                assert d.plan_by < d.date
                assert d.plan_by.weekday() < 5 and not holidays.is_holiday(jur, d.plan_by)
                assert d.date.weekday() >= 5 or holidays.is_holiday(jur, d.date)
            else:
                assert d.date.weekday() < 5 and not holidays.is_holiday(jur, d.date)
            if d.closed_office:
                assert d.date.weekday() == 5
            json.dumps(d.as_dict())                              # always serialisable


def test_offsets_equal_independent_ordinal_arithmetic():
    """Differential: the dates equal anchor + n computed by a second, independent method (ordinals)."""
    rng = random.Random(7)
    for _ in range(2000):
        a = _rand_date(rng)
        for d in calc.ab_invoice(a)[:3]:
            assert d.date.toordinal() == a.toordinal() + d.days
        for d in calc.on_prompt_payment(a):
            assert d.date.toordinal() == a.toordinal() + d.days
        assert calc.ab_lien(a, "oil-gas")[0].date.toordinal() == a.toordinal() + 90
        assert calc.ab_lien(a)[0].date.toordinal() == a.toordinal() + 60


def test_shifting_the_anchor_shifts_every_date_equally():
    rng = random.Random(11)
    for _ in range(1000):
        a = _rand_date(rng)
        k = rng.randrange(1, 400)
        a2 = a + dt.timedelta(days=k)
        for fn in (calc.ab_invoice, calc.on_prompt_payment, calc.on_holdback_release, calc.on_lien):
            for x, y in zip(fn(a), fn(a2)):
                if x.date:
                    assert (y.date - x.date).days == k


def test_hypothesis_if_installed():
    hyp = pytest.importorskip("hypothesis")
    st = pytest.importorskip("hypothesis.strategies")

    @hyp.settings(max_examples=300, deadline=None)
    @hyp.given(st.dates(min_value=dt.date(2000, 1, 1), max_value=dt.date(2100, 12, 31)),
               st.sampled_from(batch.BATCH_COMMANDS))
    def prop(d, cmd):
        for x in batch.run(cmd, d):
            if x.date is not None:
                assert x.date >= d
                assert x.plan_by is None or x.plan_by <= x.date
    prop()


def test_easter_matches_dateutil_if_installed():
    easter = pytest.importorskip("dateutil.easter")
    for y in range(2000, 2101):
        assert holidays._easter(y) == easter.easter(y)


def test_statutory_days_agree_with_holidays_package_if_installed():
    """Differential against an independent library: every day it calls one of these holidays must be
    a day we treat as a holiday (it is not a source of law; it only catches arithmetic slips)."""
    lib = pytest.importorskip("holidays")
    names = ("New Year", "Family Day", "Good Friday", "Victoria Day", "Labour Day", "Thanksgiving", "Christmas Day")
    for prov in ("ON", "AB"):
        for y in range(2008, 2101):
            ref = lib.country_holidays("CA", subdiv=prov, years=y)
            for d, nm in ref.items():
                if nm.startswith(names) and "observed" not in nm.lower() and not (prov == "AB" and "Thanksgiving" in nm):
                    assert holidays.is_holiday(prov, d), (prov, d, nm)


# ------------------------------------------------------------------ calendar-file conformance
def parse_ics_strict(text):
    assert text.endswith("\r\n") and "\n" not in text.replace("\r\n", "")
    raw_lines = text[:-2].split("\r\n")
    for ln in raw_lines:
        assert len(ln.encode("utf-8")) <= 75, ln
    lines = []
    for ln in raw_lines:
        if ln.startswith(" "):
            lines[-1] += ln[1:]
        else:
            lines.append(ln)
    assert lines[0] == "BEGIN:VCALENDAR" and lines[-1] == "END:VCALENDAR"
    assert "VERSION:2.0" in lines and any(x.startswith("PRODID:") for x in lines)
    stack, events, cur = [], [], None
    for ln in lines:
        assert not re.search(r"[\x00-\x08\x0b-\x1f\x7f]", ln)
        if ln.startswith("BEGIN:"):
            stack.append(ln[6:])
            if ln == "BEGIN:VEVENT":
                cur = {"alarms": 0}
        elif ln.startswith("END:"):
            assert stack.pop() == ln[4:]
            if ln == "END:VEVENT":
                events.append(cur)
                cur = None
        elif cur is not None and stack[-1] == "VEVENT":
            k, _, v = ln.partition(":")
            cur[k.split(";")[0]] = v
        elif stack[-1] == "VALARM" and ln.startswith("TRIGGER"):
            cur["alarms"] += 1
    assert not stack
    for e in events:
        for k in ("UID", "DTSTAMP", "DTSTART", "DTEND", "SUMMARY"):
            assert k in e, (k, e)
        assert e["DTEND"] > e["DTSTART"] and re.fullmatch(r"\d{8}", e["DTSTART"])
    uids = [e["UID"] for e in events]
    assert len(uids) == len(set(uids)), "duplicate UIDs"
    return events


def test_every_command_exports_a_conformant_calendar(monkeypatch):
    monkeypatch.chdir(ROOT)
    rows = batch.read_rows(os.path.join("tests", "golden", "jobs.csv"))
    items = [(p, c, d) for p, c, dl in rows for d in dl]
    events = parse_ics_strict(build_ics(items))
    assert len(events) == sum(1 for _p, _c, d in items if d.date is not None)


def test_duplicate_jobs_do_not_give_duplicate_uids(tmp_path, capsys):
    f = tmp_path / "j.csv"
    f.write_text("project,command,date\nA,ab-invoice,2026-06-30\nA,ab-invoice,2026-06-30\nB,ab-invoice,2026-06-30\n")
    rc, cap = run(capsys, "--ics", "batch", str(f))
    assert rc == 0
    ev = parse_ics_strict(cap.out)
    assert len(ev) == 6            # 3 dated rows per invoice job, the repeated job counted once


def test_hostile_project_name_cannot_inject_calendar_lines(tmp_path, capsys):
    f = tmp_path / "j.csv"
    f.write_text('project,command,date\n"x\r\nEND:VEVENT\r\nBEGIN:VEVENT‮;,\\",ab-invoice,2026-06-30\n', encoding="utf-8")
    rc, cap = run(capsys, "--ics", "batch", str(f))
    assert rc == 0
    ev = parse_ics_strict(cap.out)
    assert len(ev) == 3 and "‮" not in cap.out


# ------------------------------------------------------------------ machine formats stay machine-readable
def test_within_with_nothing_due_keeps_json_ics_csv_parseable(tmp_path, capsys):
    f = tmp_path / "j.csv"
    f.write_text("project,command,date\nA,ab-invoice,2026-06-30\n")
    rc, cap = run(capsys, "--json", "--today", "2026-01-01", "--within", "1", "batch", str(f))
    assert rc == 0 and json.loads(cap.out)["schedule"] == [] and "Nothing due" in cap.err
    rc, cap = run(capsys, "--ics", "--today", "2026-01-01", "--within", "1", "batch", str(f))
    assert rc == 0 and parse_ics_strict(cap.out) == []
    rc, cap = run(capsys, "--csv", "--today", "2026-01-01", "--within", "1", "batch", str(f))
    assert rc == 0 and cap.out.count("\n") == 1
    rc, cap = run(capsys, "--today", "2026-01-01", "--within", "1", "batch", str(f))
    assert rc == 0 and "Nothing due" in cap.out and cap.err == ""


def test_json_rows_carry_stable_ids(capsys):
    rc, cap = run(capsys, "--json", "on-prompt-payment", "2026-07-15")
    ids = [r["id"] for r in json.loads(cap.out)["schedule"]]
    assert ids == ["deficiency_notice_window_closes", "owner_s_notice_of_non_payment_by",
                   "payment_due_owner_contractor", "contractor_pays_subs_if_owner_has_not_paid"]


def test_verify_sources_exit_is_not_zero_when_nothing_was_checked(tmp_path, capsys):
    rc, cap = run(capsys, "verify-sources", "--from-dir", str(tmp_path))
    assert rc == 3 and "not a pass" in cap.err


# ------------------------------------------------------------------ money amounts
@pytest.mark.parametrize("cmd,args,expect", [
    ("ab-holdback", ["2026-09-01", "--amount", "125000.50"], "CAD 125,000.50 x 10% = CAD 12,500.05"),
    ("on-holdback", ["2026-05-15", "--amount", "80000"], "CAD 80,000.00 x 10% = CAD 8,000.00"),
    ("ab-holdback", ["2026-09-01", "--amount", "0.05"], "= CAD 0.01"),          # 0.005 rounds half-up
    ("ab-holdback", ["2026-09-01", "--amount", "0.04"], "= CAD 0.00"),
    ("on-holdback", ["2026-05-15", "--amount", "9999999999999.99"], "= CAD 1,000,000,000,000.00"),
])
def test_amount(capsys, cmd, args, expect):
    rc, cap = run(capsys, cmd, *args)
    assert rc == 0 and expect in cap.out
    assert ("PPCLA ss.18(1), 23(1)" if cmd.startswith("ab") else "Construction Act s.22(1)") in cap.out


@pytest.mark.parametrize("bad", ["-5", "1e5", "$5", "1,000", "12.345", "nan", "inf", "", "٣٤٥", "1" * 14, " ", "5."])
def test_amount_rejects_everything_unusual(capsys, bad):
    with pytest.raises(SystemExit) as e:
        main(["ab-holdback", "2026-09-01", "--amount", bad])
    assert e.value.code == 2
    cap = capsys.readouterr()
    assert cap.out == "" and "Traceback" not in cap.err


def test_holdback_amount_function_fails_closed():
    for bad in (Decimal("NaN"), Decimal("-1"), Decimal("Infinity"), 5, "5"):
        with pytest.raises(ValueError):
            calc.holdback_amount("AB", bad)
    with pytest.raises(ValueError):
        calc.holdback_amount("BC", Decimal(5))


# ------------------------------------------------------------------ upgrade path from the published 0.1.0
def test_every_0_1_0_command_and_json_key_still_exists(capsys):
    """0.1.0 offered these commands and JSON keys (checked by running the real 0.1.0 wheel, see docs/ROUND5.md)."""
    for cmd in ("ab-invoice", "ab-sub-payment", "on-lien", "on-holdback", "on-invoice", "on-annual"):
        rc, cap = run(capsys, "--json", cmd, "2026-06-30")
        data = json.loads(cap.out)
        assert rc == 0 and {"schedule", "note"} <= set(data)
        for row in data["schedule"]:
            assert {"label", "date", "basis", "days", "hard"} <= set(row)


# ------------------------------------------------------------------ built artefacts carry the author (needs `build`)
def test_built_wheel_metadata_names_the_author(tmp_path):
    pytest.importorskip("build")
    out = subprocess.run([sys.executable, "-m", "build", "--wheel", "--outdir", str(tmp_path), ROOT],
                         capture_output=True, text=True)
    if out.returncode != 0:
        pytest.skip("wheel build not possible here (offline build isolation?)")
    whl = next(p for p in os.listdir(tmp_path) if p.endswith(".whl"))
    with zipfile.ZipFile(os.path.join(tmp_path, whl)) as z:
        meta = z.read([n for n in z.namelist() if n.endswith("METADATA")][0]).decode()
        lic = z.read([n for n in z.namelist() if n.endswith("LICENSE")][0]).decode()
    assert f"Author: {AUTHOR}" in meta and f"Maintainer: {AUTHOR}" in meta
    assert f"Copyright (c) 2026 {AUTHOR}" in lic
