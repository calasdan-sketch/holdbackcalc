"""Round 4: what a stranger who ran `pip install holdbackcalc` actually experiences."""
import io
import json
import os
import re
import shlex
import subprocess
import sys

import pytest

import holdbackcalc
from holdbackcalc import calc
from holdbackcalc.cli import main

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")


def run(capsys, *argv):
    rc = main(list(argv))
    return rc, capsys.readouterr()


# ---- failure discipline: no tracebacks ----------------------------------------
class _BrokenOut(io.StringIO):
    def write(self, s):
        raise BrokenPipeError(32, "Broken pipe")


def test_broken_pipe_is_quiet(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdout", _BrokenOut())
    assert main(["ab-invoice", "2026-06-30"]) == 1
    assert "Traceback" not in capsys.readouterr().err


def test_disk_full_is_a_plain_error(monkeypatch, capsys):
    class Full(io.StringIO):
        def write(self, s):
            raise OSError(28, "No space left on device")
    monkeypatch.setattr(sys, "stdout", Full())
    assert main(["ab-invoice", "2026-06-30"]) == 2
    err = capsys.readouterr().err
    assert "No space left" in err and "Traceback" not in err


def test_unexpected_bug_gives_message_and_exit_70(monkeypatch, capsys):
    def boom(*a, **k):
        raise RuntimeError("secret internals")
    monkeypatch.setattr(calc, "ab_invoice", boom)
    import holdbackcalc.batch as b
    monkeypatch.setattr(b.calc, "ab_invoice", boom)
    monkeypatch.delenv("HOLDBACKCALC_DEBUG", raising=False)
    rc, cap = run(capsys, "ab-invoice", "2026-06-30")
    assert rc == 70 and "internal error" in cap.err and "secret internals" not in cap.err
    assert "github.com/calasdan-sketch/holdbackcalc/issues" in cap.err
    monkeypatch.setenv("HOLDBACKCALC_DEBUG", "1")
    with pytest.raises(RuntimeError):
        main(["ab-invoice", "2026-06-30"])


def test_ctrl_c_exit_code(monkeypatch, capsys):
    import holdbackcalc.cli as cli

    def stop(_argv):
        raise KeyboardInterrupt
    monkeypatch.setattr(cli, "_main", stop)
    assert main([]) == 130


def test_within_rejects_negative_and_junk(capsys):
    for bad in ("-5", "abc", "1.5"):
        with pytest.raises(SystemExit) as e:
            main(["--today", "2026-07-01", "--within", bad, "ab-invoice", "2026-06-30"])
        assert e.value.code == 2
        assert "Traceback" not in capsys.readouterr().err


def test_today_accepts_the_word_today(capsys):
    rc, cap = run(capsys, "--today", "today", "--json", "ab-invoice", "2026-06-30")
    assert rc == 0 and "days_left" in json.loads(cap.out)["schedule"][0]


# ---- calendar newline handling (Windows) --------------------------------------
def test_ics_is_not_double_translated_on_a_crlf_platform(monkeypatch):
    """A Windows text stdout turns \\n into \\r\\n. The .ics already has CRLF; it must stay CRLF."""
    raw = io.BytesIO()
    win = io.TextIOWrapper(raw, encoding="utf-8", newline="\r\n", write_through=True)   # what Windows gives you
    monkeypatch.setattr(sys, "stdout", win)
    assert main(["--ics", "ab-invoice", "2026-06-30"]) == 0
    data = raw.getvalue()
    assert b"\r\r\n" not in data and data.count(b"\r\n") > 10
    assert data.startswith(b"BEGIN:VCALENDAR\r\n") and data.endswith(b"END:VCALENDAR\r\n")


# ---- weekday names do not depend on the machine's locale ----------------------
def test_weekday_names_are_fixed_english():
    import datetime as dt
    assert [calc.weekday_name(dt.date(2026, 6, 29) + dt.timedelta(days=i)) for i in range(7)] == \
        ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# ---- batch from standard input -------------------------------------------------
def test_batch_reads_stdin(monkeypatch, capsys):
    csv_bytes = b"project,command,date\nA,ab-invoice,2026-06-30\n"

    class FakeStdin:
        buffer = io.BytesIO(csv_bytes)
    monkeypatch.setattr(sys, "stdin", FakeStdin())
    rc, cap = run(capsys, "--json", "batch", "-")
    assert rc == 0 and json.loads(cap.out)["schedule"][0]["project"] == "A"


def test_batch_stdin_too_big_is_clean_error(monkeypatch, capsys):
    from holdbackcalc import batch

    class FakeStdin:
        buffer = io.BytesIO(b"x" * (batch.MAX_BYTES + 10))
    monkeypatch.setattr(sys, "stdin", FakeStdin())
    rc, cap = run(capsys, "batch", "-")
    assert rc == 2 and "larger than" in cap.err and cap.out == ""


# ---- JSON contract ---------------------------------------------------------------
def test_json_has_schema_and_tool_version(capsys):
    rc, cap = run(capsys, "--json", "on-lien", "2026-01-01")
    data = json.loads(cap.out)
    assert data["schema_version"] == 1 and data["tool_version"] == holdbackcalc.__version__


# ---- verify-sources subcommand ----------------------------------------------------
def test_verify_sources_subcommand_runs_offline(tmp_path, capsys):
    rc, cap = run(capsys, "verify-sources", "--from-dir", str(tmp_path))
    assert rc == 0                                       # nothing present -> everything SKIPPED, nothing FAILED
    assert "0 passed, 0 failed, 35 skipped" in cap.out
    assert "not a pass" in cap.err


# ---- public API / packaging consistency ----------------------------------------------
def test_every_name_in_all_exists_and_new_function_is_exported():
    for name in holdbackcalc.__all__:
        assert hasattr(holdbackcalc, name), name
    assert "on_annual_from_contract" in holdbackcalc.__all__


def test_version_is_the_same_everywhere():
    py = open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8").read()
    version = re.search(r'^version = "([^"]+)"', py, re.M).group(1)
    assert version == holdbackcalc.__version__
    log = open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8").read()
    assert re.search(rf"^## {re.escape(version)}\b", log, re.M)


def test_metadata_names_the_owner_and_repo():
    py = open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8").read()
    assert 'name = "Calas Automations Inc."' in py
    assert "https://github.com/calasdan-sketch/holdbackcalc" in py
    assert 'license = "MIT"' in py and "setuptools>=77" in py      # SPDX license strings need setuptools 77+
    lic = open(os.path.join(ROOT, "LICENSE"), encoding="utf-8").read()
    assert lic.startswith("MIT License")
    assert os.path.exists(os.path.join(SRC, "holdbackcalc", "py.typed"))


def test_python_dash_m_works():
    env = dict(os.environ, PYTHONPATH=SRC)
    out = subprocess.run([sys.executable, "-m", "holdbackcalc", "--version"], capture_output=True, text=True, env=env)
    assert out.returncode == 0 and out.stdout.startswith("holdbackcalc ")


def test_no_args_is_a_usage_error_not_a_traceback():
    env = dict(os.environ, PYTHONPATH=SRC)
    out = subprocess.run([sys.executable, "-m", "holdbackcalc"], capture_output=True, text=True, env=env)
    assert out.returncode == 2 and "Traceback" not in out.stderr and "usage:" in out.stderr


def test_runs_from_a_directory_with_spaces(tmp_path):
    d = tmp_path / "my jobs folder"
    d.mkdir()
    (d / "my jobs.csv").write_text("project,command,date\nA b,ab-invoice,2026-06-30\n", encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=SRC)
    out = subprocess.run([sys.executable, "-m", "holdbackcalc", "batch", "my jobs.csv"], cwd=d,
                         capture_output=True, text=True, env=env)
    assert out.returncode == 0 and "A b" in out.stdout


# ---- the README's own commands must work --------------------------------------------
def _readme_commands():
    text = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    cmds = []
    for block in re.findall(r"```bash\n(.*?)```", text, re.S):
        block = block.replace("\\\n", " ")
        for line in block.splitlines():
            line = line.split(" #")[0].strip()
            if line.startswith("holdbackcalc "):
                cmds.append(line)
    return cmds


def test_readme_has_commands_to_check():
    assert len(_readme_commands()) >= 4


@pytest.mark.parametrize("line", _readme_commands())
def test_readme_command_runs(line, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "jobs.csv").write_text(
        "project,command,date,certificate,registered,sector\n"
        "Maple St,ab-invoice,2026-06-30,,,\nOak Ave,on-prompt-payment,2026-07-02,,,\n", encoding="utf-8")
    line = line.split(" > ")[0]
    if line.startswith("holdbackcalc verify-sources"):
        pytest.skip("needs network")
    argv = shlex.split(line)[1:]
    try:
        rc = main(argv)
    except SystemExit as e:          # --version exits through argparse
        rc = e.code or 0
    assert rc == 0, line
    assert capsys.readouterr().out


def test_failed_run_does_not_leave_an_output_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bad.csv").write_text("project,command,date\nA,nope,2026-06-30\n", encoding="utf-8")
    rc, cap = run(capsys, "--out", "o.txt", "batch", "bad.csv")
    assert rc == 2 and not (tmp_path / "o.txt").exists()
    rc, cap = run(capsys, "--out", "o.txt", "on-lien-events", "--role", "contractor")
    assert rc == 2 and not (tmp_path / "o.txt").exists()
    rc, cap = run(capsys, "--out", "o.txt", "ab-invoice", "2026-06-30")
    assert rc == 0 and (tmp_path / "o.txt").read_text(encoding="utf-8").startswith("dispute notice")
    rc, cap = run(capsys, "--out", "o.txt", "ab-invoice", "2026-06-30")        # still refuses to overwrite
    assert rc == 2 and (tmp_path / "o.txt").exists()
