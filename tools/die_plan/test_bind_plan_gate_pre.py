"""bind.py pre-bind hook (PLAN-GATE-PRE-1115, COORD r213): a die elab/bind refuses on a plan_gate_pre FAIL, in seconds."""
import json
import sys
import types
from pathlib import Path

import pytest

import bind


class NS:
    def __init__(self, plan, out, asbuilt=None, cmd="bind"):
        self.plan, self.out, self.asbuilt, self.cmd = str(plan), str(out), asbuilt, cmd


@pytest.fixture
def fake(monkeypatch, tmp_path):
    calls = []
    mod = types.ModuleType("plan_gate_pre")

    def check(tree, plan, asbuilt=None, baseline=None, skip=(), **_kw):
        calls.append(dict(tree=tree, plan=plan, baseline=baseline, skip=skip))
        return list(mod.findings)

    mod.check, mod.findings = check, []
    monkeypatch.setitem(sys.modules, "plan_gate_pre", mod)
    monkeypatch.delenv("OT_PLAN_GATE_PRE", raising=False)
    monkeypatch.delenv("OT_PLAN_GATE_BASELINE", raising=False)
    p = tmp_path / "plan.json"
    p.write_text("{}")
    return mod, calls, p, tmp_path / "out"


def test_pass_stamps_and_second_call_skips(fake, capsys):
    mod, calls, p, out = fake
    assert bind._plan_gate_pre(NS(p, out)) == 0
    assert json.loads((out / "plan_gate_pre.json").read_text())["result"] == "pass"
    assert bind._plan_gate_pre(NS(p, out, cmd="elab")) == 0 and len(calls) == 1      # same plan: no repeat
    p.write_text('{"a":1}')
    bind._plan_gate_pre(NS(p, out))
    assert len(calls) == 2
    assert calls[0]["skip"] == ("ROWS", "GEOM")


def test_fail_refuses_and_names_reason(fake, capsys):
    mod, calls, p, out = fake
    mod.findings = ["FAIL SCHEMA-UNKNOWN-KEY 'band_fixed_um' x10 ...", "WARN SCHEMA-JSON-STALE x"]
    assert bind._plan_gate_pre(NS(p, out)) == 2
    txt = capsys.readouterr().out
    assert "REFUSED by plan_gate_pre" in txt and "SCHEMA-UNKNOWN-KEY" in txt
    assert not (out / "plan_gate_pre.json").exists()


def test_modes_and_baseline(fake, monkeypatch):
    mod, calls, p, out = fake
    mod.findings = ["FAIL TOOLS-SKEW x"]
    monkeypatch.setenv("OT_PLAN_GATE_PRE", "warn")
    assert bind._plan_gate_pre(NS(p, out)) == 0
    monkeypatch.setenv("OT_PLAN_GATE_PRE", "off")
    n = len(calls)
    assert bind._plan_gate_pre(NS(p, out)) == 0 and len(calls) == n
    monkeypatch.setenv("OT_PLAN_GATE_PRE", "refuse")
    monkeypatch.setenv("OT_PLAN_GATE_BASELINE", "/x/base.json")
    assert bind._plan_gate_pre(NS(p, out)) == 2
    assert calls[-1]["baseline"] == "/x/base.json" and calls[-1]["skip"] == ()


def test_missing_module_does_not_block(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "plan_gate_pre", None)     # ImportError
    p = tmp_path / "p.json"
    p.write_text("{}")
    assert bind._plan_gate_pre(NS(p, tmp_path / "o")) == 0


def test_main_skips_hook_under_pytest(monkeypatch, tmp_path):
    called = []
    monkeypatch.setattr(bind, "_plan_gate_pre", lambda a: called.append(1) or 2)
    monkeypatch.setattr(bind, "cmd_bind", lambda a: 0)
    assert bind.main(["bind", str(tmp_path / "p.json"), "--out", str(tmp_path / "o")]) == 0 and not called
    monkeypatch.delenv("PYTEST_CURRENT_TEST")
    monkeypatch.setenv("OT_PLAN_GATE_PRE_SERIAL", "1")
    assert bind.main(["bind", str(tmp_path / "p.json"), "--out", str(tmp_path / "o")]) == 2 and called


@pytest.mark.parametrize("gate_rc", [0, 2])
def test_gate_runs_beside_the_bind_and_its_refusal_wins(monkeypatch, tmp_path, gate_rc):
    """PLAN-GATE-BESIDE-1122: the bind starts at once; the gate (a forked child) is joined before main returns"""
    import os
    import time
    ran = []

    def gate(a):
        time.sleep(0.5)
        print("GATE-LINE from the child")
        return gate_rc
    monkeypatch.setattr(bind, "_plan_gate_pre", gate)
    monkeypatch.setattr(bind, "cmd_bind", lambda a: ran.append(time.time()) or 0)
    monkeypatch.delenv("PYTEST_CURRENT_TEST")
    monkeypatch.delenv("OT_PLAN_GATE_PRE_SERIAL", raising=False)
    monkeypatch.delenv("OT_PLAN_GATE_PRE", raising=False)
    t0 = time.time()
    out = tmp_path / "o"
    assert bind.main(["bind", str(tmp_path / "p.json"), "--out", str(out)]) == gate_rc
    assert ran and ran[0] - t0 < 0.4                     # the bind did not wait for the gate
    assert "GATE-LINE" in (out / "plan_gate_pre.log").read_text()
    assert (out / "PLAN_GATE_PRE_REFUSED.txt").exists() == bool(gate_rc)
    assert not bind._PG_CHILD.get("pid") and os.getpid()
