"""PRECHECK-R2: plan_advisory driver + plan_gate_pre ADVISORY class: WARN-only, never a FAIL, a crashing check is 'not checked'."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_advisory as PA  # noqa: E402
import plan_gate_pre as PGP  # noqa: E402


def test_crashing_check_is_not_checked(monkeypatch, tmp_path):
    mod = tmp_path / "adv_boom_r2.py"
    mod.write_text("def findings(raw, plan_path, tree=None, **kw):\n    raise RuntimeError('boom')\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(PA, "CHECKS", (("BOOM", "adv_boom_r2"),))
    out = PA.run({}, "p.json")
    assert out == ["WARN ADV-BOOM not checked: RuntimeError: boom"]


def test_lines_forced_warn_capped_and_debug_dropped(monkeypatch, tmp_path):
    mod = tmp_path / "adv_many_r2.py"
    mod.write_text("def findings(raw, plan_path, tree=None, **kw):\n"
                   "    return ['# coverage x', 'FAIL t1: x'] + ['WARN ADV-MANY t%d: y' % i for i in range(40)]\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(PA, "CHECKS", (("MANY", "adv_many_r2"),))
    out = PA.run({}, "p.json")
    assert all(x.startswith("WARN ADV-MANY") for x in out) and len(out) == PA.MAX_LINES + 1
    assert not any("# coverage" in x for x in out)


def test_off_switch(monkeypatch):
    monkeypatch.setenv("OT_PLAN_ADVISORY", "off")
    assert PA.run({"partition_types": {}}, "p.json") == []


def test_gate_advisory_never_fails(monkeypatch, tmp_path):
    p = tmp_path / "plan.json"
    p.write_text(json.dumps({"partition_types": {}}))
    monkeypatch.setattr(PA, "run", lambda raw, plan, tree=None, **kw: ["ADV-X t: something", "WARN ADV-Y t: z"])
    out = PGP.advisory_lines(str(tmp_path), str(p))
    assert out == ["WARN ADV-X t: something", "WARN ADV-Y t: z"]
    assert "ADVISORY" in PGP.CLASSES


def test_real_checks_on_empty_plan_are_quiet():
    out = PA.run({"partition_types": {}, "ports": [], "lanes": []}, "p.json")
    assert all(x.startswith("WARN ADV-") for x in out)
