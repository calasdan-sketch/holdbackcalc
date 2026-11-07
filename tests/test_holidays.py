import datetime as dt

import pytest

from holdbackcalc.calc import ab_invoice, on_lien
from holdbackcalc.holidays import _easter, holidays, is_holiday, roll_forward

D = dt.date


def test_easter_known_dates():
    assert _easter(2024) == D(2024, 3, 31)
    assert _easter(2025) == D(2025, 4, 20)
    assert _easter(2026) == D(2026, 4, 5)
    assert _easter(2027) == D(2027, 3, 28)
    assert _easter(2038) == D(2038, 4, 25)


def test_ontario_2026_list():
    h = holidays("ON", 2026)
    for d in [D(2026, 1, 1), D(2026, 2, 16), D(2026, 4, 3), D(2026, 4, 6), D(2026, 5, 18), D(2026, 7, 1),
              D(2026, 9, 7), D(2026, 10, 12), D(2026, 11, 11), D(2026, 12, 25), D(2026, 12, 26)]:
        assert d in h, d


def test_alberta_has_no_thanksgiving_rollforward():
    assert D(2026, 10, 12) in holidays("ON", 2026)
    assert D(2026, 10, 12) not in holidays("AB", 2026)   # unverified for AB -> never rolled


def test_special_christmas_and_boxing_day_rules():
    assert D(2027, 12, 27) in holidays("ON", 2027)      # Christmas Saturday -> Monday also holiday
    assert D(2022, 12, 27) in holidays("ON", 2022)      # Christmas Sunday -> Tuesday also holiday
    assert D(2023, 1, 2) in holidays("ON", 2023)        # New Year's Sunday -> Monday
    assert D(2027, 7, 1) in holidays("ON", 2027)
    assert D(2021, 12, 27) in holidays("AB", 2021)      # Dec 26 Sunday -> Dec 27 (AB s.28(1)(x)(iv))
    assert D(2022, 12, 27) in holidays("AB", 2022)      # Dec 26 Monday -> Dec 27


def test_roll_forward_skips_only_sundays_and_listed_holidays():
    assert roll_forward("ON", D(2026, 4, 3)) == D(2026, 4, 4)    # Good Friday -> Saturday (s.89(1) only)
    assert roll_forward("ON", D(2026, 3, 1)) == D(2026, 3, 2)    # Sunday -> Monday
    assert roll_forward("ON", D(2026, 3, 2)) == D(2026, 3, 2)    # ordinary Monday unchanged
    assert roll_forward("ON", D(2022, 12, 25)) == D(2022, 12, 28)  # Sun Xmas, Mon Boxing, Tue Xmas-in-lieu


def test_is_holiday_sunday_everywhere():
    assert is_holiday("ON", D(2026, 3, 1)) and is_holiday("AB", D(2026, 3, 1))
    assert not is_holiday("ON", D(2026, 3, 2))


def test_unknown_jurisdiction_fails_closed():
    with pytest.raises(ValueError):
        holidays("BC", 2026)


def test_deadline_records_roll_but_keeps_plain_date():
    # 2026-02-15 + 14 days = Sunday 2026-03-01
    d = next(x for x in ab_invoice(D(2026, 2, 15)) if x.label == "dispute notice by (owner)")
    assert d.date == D(2026, 3, 1) and d.rolled == D(2026, 3, 2)
    # a non-holiday date has no roll
    assert on_lien(D(2026, 1, 1))[0].rolled is None


def test_cli_shows_roll_note(capsys):
    from holdbackcalc.cli import main
    main(["ab-invoice", "2026-02-15"])
    out = capsys.readouterr().out
    assert "2026-03-02" in out and "plan to the earlier date" in out
