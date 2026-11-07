"""Data-QA: the registry, the constants and the calculator must agree."""
import importlib.util
import json
import os
import re

from holdbackcalc import rules as R
from holdbackcalc.cli import main

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_ids_unique_and_wellformed():
    ids = [r.id for r in R.REGISTRY]
    assert len(ids) == len(set(ids)) >= 30
    for r in R.REGISTRY:
        assert re.fullmatch(r"(ab|on)\.[a-z_.0-9]+", r.id)
        assert r.id.startswith(r.jurisdiction.lower() + ".")
        assert r.source in R.SOURCE_TEXTS
        assert r.cite and len(r.evidence) >= 25   # an evidence phrase must be specific
        assert R.SOURCE_TEXTS[r.source][1].startswith("https://")


def test_registry_values_match_constants():
    by = {r.id: r.value for r in R.REGISTRY}
    assert by["ab.invoice.payment_days"] == R.AB_INVOICE_PAYMENT_DAYS == 28
    assert by["ab.invoice.dispute_notice_days"] == R.AB_DISPUTE_NOTICE_DAYS == 14
    assert by["ab.sub.payment_days"] == R.AB_SUB_PAYMENT_DAYS == 7
    assert by["ab.lien.register_days"] == R.AB_LIEN_REGISTER_DAYS == 60
    assert by["ab.lien.register_days_special"] == R.AB_LIEN_REGISTER_DAYS_SPECIAL == 90
    assert by["ab.lien.lis_pendens_days"] == R.AB_LIS_PENDENS_DAYS == 180
    assert by["ab.holdback.rate"] == R.AB_HOLDBACK_RATE == 0.10
    assert by["on.lien.preserve_days"] == R.ON_LIEN_PRESERVE_DAYS == 60
    assert by["on.lien.perfect_days"] == R.ON_LIEN_PERFECT_DAYS == 90
    assert by["on.annual.payment_window_days"] == [60, 74]
    assert R.ON_OWNER_PAYMENT_TOTAL_DAYS == 74
    assert by["on.adjudication.days"] == R.ON_ADJUDICATION_DAYS == 90
    assert by["on.invoice.payment_days"] == R.ON_INVOICE_PAYMENT_DAYS == 28


def test_every_numeric_constant_is_registered():
    numeric = {n: v for n, v in vars(R).items()
               if re.fullmatch(r"(AB|ON)_[A-Z_]+", n) and isinstance(v, (int, float)) and not isinstance(v, bool)}
    registered = {json.dumps(r.value) for r in R.REGISTRY} | {
        json.dumps(x) for r in R.REGISTRY if isinstance(r.value, list) for x in r.value}
    derived = {"ON_OWNER_PAYMENT_TOTAL_DAYS"}          # 60 + 14, covered by two registered rules
    for name, val in numeric.items():
        if name in derived:
            continue
        assert json.dumps(val) in registered, f"{name}={val} has no registry entry"


def test_rules_command_json(capsys):
    assert main(["--json", "rules"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data["rules"]) == len(R.REGISTRY)
    assert all(r["status"] == "verified-primary-text" and r["url"] for r in data["rules"])


def test_rules_command_table(capsys):
    assert main(["rules"]) == 0
    out = capsys.readouterr().out
    assert "on.lien.preserve_days" in out and "verify_sources" in out


def _load_tool():
    spec = importlib.util.spec_from_file_location("verify_sources", os.path.join(ROOT, "tools", "verify_sources.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.MIN_CHARS = 0          # these tests use tiny synthetic texts
    return mod


def test_verifier_skips_a_shell_page_instead_of_failing(tmp_path, capsys):
    tool = _load_tool()
    tool.MIN_CHARS = 20_000
    (tmp_path / "ON_ACT.html").write_text("<html><body>Loading...</body></html>")
    assert tool.main(["--from-dir", str(tmp_path)]) == 0       # nothing FAILED
    out = capsys.readouterr()
    assert "FAIL" not in out.out and "SKIPPED on.lien.preserve_days" in out.out
    assert "not the statute text" in out.err


def test_verifier_flags_missing_phrase_and_skips_missing_sources(tmp_path, capsys):
    tool = _load_tool()
    # Ontario Act text WITHOUT the phrases -> FAIL (negative control); other sources absent -> SKIPPED
    (tmp_path / "ON_ACT.html").write_text("<html><body>nothing relevant here</body></html>")
    assert tool.main(["--from-dir", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "FAIL    on.lien.preserve_days" in out and "SKIPPED ab.invoice.payment_days" in out
    assert "PASS" not in out


def test_verifier_passes_when_text_contains_every_phrase(tmp_path, capsys):
    tool = _load_tool()
    on_text = " ".join(r.evidence for r in R.REGISTRY if r.source == "ON_ACT")
    (tmp_path / "ON_ACT.html").write_text(f"<html><p>{on_text}</p></html>")
    assert tool.main(["--from-dir", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "PASS    on.lien.preserve_days" in out and "FAIL" not in out
