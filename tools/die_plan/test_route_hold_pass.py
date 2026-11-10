"""ROUTE-HOLD-PASS (DIE-HBM-97 11-10, COORD vecd-clkroot-r2): opt-in in-flow FF hold repair on routed RCX, one pass.

Local, no Docker/OpenROAD: the decision (core-owned hold FAIL only), the one-pass in-flow call into eco_loop.run_loop,
eco_loop's in_flow_form not stopping on the late-ECO near-miss numbers, the generator lines and the runner hook."""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import eco_loop  # noqa: E402
import route_hold_pass as R  # noqa: E402

RUNNER = ROOT / "physical/die_plan/hbm_arch_cores/run_kit_hbm.sh"


def kit(tmp_path, on=True, hold="FAIL", port=2061, core=3250, core_wns=-98.94, spec=None, name="kit"):
    k = tmp_path / name
    (k / "signoff" / "ff").mkdir(parents=True)
    (k / "config.mk").write_text("export FOO = 1\n" + ("export OT_ROUTE_HOLD_PASS = 1\n" if on else ""))
    sp = on if spec is None else spec
    (k / "freeze.json").write_text(json.dumps({"flow_defaults": {"route_hold_pass": {"on": bool(sp)}}}))
    rec = {"verdict": "NOT_SIGNED", "checks": {"hold_ff": {"verdict": hold, "wns_ps": -723.9, "violators": port + core},
                                               "setup_tt": {"verdict": "PASS"}, "drc": {"count": 0}}}
    (k / "signoff" / "signoff.json").write_text(json.dumps(rec))
    (k / "signoff" / "ff" / "corner.json").write_text(json.dumps({"std_min_start": {
        "port": port, "other": core, "reg": core, "oport": 0, "trunc": 0, "err": 0, "nonport_n": core,
        "nonport_wns": core_wns, "core_n": core, "core_wns": core_wns}}))
    return k, k / "signoff" / "signoff.json"


def test_decide_runs_on_core_owned_hold_fail(tmp_path):
    k, s = kit(tmp_path)
    go, why = R.decide(k, s)
    assert go and "3250" in why and "-98.94" in why


@pytest.mark.parametrize("kw,frag", [(dict(on=False), "not declared"), (dict(spec=False), "not declared"), (dict(hold="PASS"), "nothing to repair"),
                                     (dict(core=0, core_wns=0.0), "parent")])
def test_decide_skips(tmp_path, kw, frag):
    k, s = kit(tmp_path, **kw)
    go, why = R.decide(k, s)
    assert not go and frag in why


def _after(tmp_path, core, core_wns, hold="FAIL"):
    _, so = kit(tmp_path, hold=hold, port=2061, core=core, core_wns=core_wns, name="pass")
    return so


def test_run_is_one_strict_declared_pass_at_the_flow_target_and_recorded(tmp_path):
    k, s = kit(tmp_path)
    (k / "run_kit_hbm.sh").write_text("#!/bin/bash\n")
    after = _after(tmp_path, 40, -3.2)
    seen = {}

    def fake(kit_, so, **kw):
        seen.update(kw, kit=kit_, so=so)
        return {"verdict": "EXHAUSTED", "reason": "x", "root": str(kw["root"]), "iterations": [{"signoff": str(after)}]}
    rc = R.run(k, s, mem=48, cpus=16, run_loop=fake)
    assert rc == 1
    assert seen["max_iter"] == 1 and seen["strict_one_pass"] and seen["route_hold_form"]
    assert seen["hold_margin"] == eco_loop.HOLD_MARGIN_PS == 5
    assert seen["runner"].endswith("run_kit_hbm.sh")
    out = json.loads((k / "route_hold_pass.json").read_text())
    assert out["run"] and out["on"] and out["passes"] == 1 and out["verdict"] == "EXHAUSTED"
    assert out["before"]["core_n"] == 3250 and out["after"]["core_n"] == 40 and out["core_endpoints_repaired"] == 3210
    base = json.loads(s.read_text())["route_hold_pass"]
    assert base["on"] and base["run"] and base["after_signoff"] == str(after)
    rp = json.loads(after.read_text())["route_hold_pass"]
    assert rp["before"]["core_wns_ps"] == -98.94 and rp["after"]["core_wns_ps"] == -3.2 and rp["passes"] == 1


def test_pass_then_routed_lec(tmp_path):
    k, s = kit(tmp_path)
    after = _after(tmp_path, 0, 0.0, hold="PASS")
    calls = []

    def lec(kit_, res, mem, cpus, tool):
        calls.append(kit_)
        res["lec"] = {"verdict": "EQUIVALENT"}
        return True
    rc = R.run(k, s, lec=True, run_lec=lec,
               run_loop=lambda *a, **kw: {"verdict": "PASS", "iterations": [{"signoff": str(after)}]})
    assert rc == 0 and calls and json.loads((k / "route_hold_pass.json").read_text())["lec"] == "EQUIVALENT"


def test_run_skip_writes_record_and_returns_0(tmp_path):
    k, s = kit(tmp_path, hold="PASS")
    assert R.run(k, s, run_loop=lambda *a, **kw: pytest.fail("must not run")) == 0
    assert json.loads((k / "route_hold_pass.json").read_text())["run"] is False
    assert json.loads(s.read_text())["route_hold_pass"]["run"] is False


def _stub(monkeypatch):
    monkeypatch.setattr(eco_loop, "eligible", lambda rec: (True, "ECO class: hold_ff"))
    monkeypatch.setattr(eco_loop, "eco_mem", lambda kit_, mem: (mem, None))

    class Staged(Exception):
        pass

    def stage(*a, **kw):
        raise Staged()
    monkeypatch.setattr(eco_loop, "stage_so", stage)
    return Staged


def test_eco_loop_declared_form_does_not_stop_at_near_miss(tmp_path, monkeypatch):
    """beyond the near-miss numbers: the late ECO stops (NOT_NEAR_MISS), the declared form goes on to staging"""
    k, s = kit(tmp_path)
    Staged = _stub(monkeypatch)
    r = eco_loop.run_loop(k, s, root=tmp_path / "late", run=lambda *a, **kw: 0)
    assert r["verdict"] == "NOT_NEAR_MISS"
    with pytest.raises(Staged):
        eco_loop.run_loop(k, s, root=tmp_path / "form", max_iter=1, strict_one_pass=True, route_hold_form=True,
                          run=lambda *a, **kw: 0)
    with pytest.raises(ValueError):
        eco_loop.run_loop(k, s, root=tmp_path / "bad", route_hold_form=True, run=lambda *a, **kw: 0)


@pytest.mark.parametrize("kw", [dict(on=False, spec=False), dict(on=True, spec=False), dict(on=False, spec=True)])
def test_eco_loop_form_flag_without_spec_is_an_error(tmp_path, monkeypatch, kw):
    """not a hidden skip: the flag is honoured only when freeze.json AND config.mk declare the form"""
    k, s = kit(tmp_path, **kw)
    _stub(monkeypatch)
    r = eco_loop.run_loop(k, s, root=tmp_path / "x", max_iter=1, strict_one_pass=True, route_hold_form=True,
                          run=lambda *a, **kw: 0)
    assert r["verdict"] == "ERROR" and "does not declare" in r["reason"]


def test_no_eco_on_top_of_a_ran_pass(tmp_path, monkeypatch):
    k, s = kit(tmp_path, core=10, core_wns=-2.0)          # a near miss: the late ECO would otherwise run
    _stub(monkeypatch)
    (k / "route_hold_pass.json").write_text(json.dumps({"run": True}))
    r = eco_loop.run_loop(k, s, root=tmp_path / "top", run=lambda *a, **kw: 0)
    assert r["verdict"] == "NOT_ELIGIBLE" and "no further ECO" in r["reason"]


def test_generator_declares_the_form_in_the_spec():
    sys.path.insert(0, str(ROOT / "physical/die_plan/hbm_arch_cores"))
    import gen_core_kit_hbm as G
    on, off = G.route_hold_pass_spec(True), G.route_hold_pass_spec(False)
    assert on["on"] is True and off["on"] is False and on["passes"] == 1 and on["repair_target_ps"] == 5
    assert on["eco_on_top"] is False
    src = (ROOT / "physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py").read_text()
    assert 'flow["route_hold_pass"] = route_hold_pass_spec(a.route_hold_pass == "on")' in src


def test_generator_lines():
    sys.path.insert(0, str(ROOT / "physical/die_plan/hbm_arch_cores"))
    import gen_core_kit_hbm as G
    lines = G.route_hold_pass_lines()
    assert "export OT_ROUTE_HOLD_PASS = 1" in lines
    tl = [x for x in lines if x.startswith("export OT_ROUTE_HOLD_TOOLS = ")]
    assert tl and (Path(tl[0].split(" = ", 1)[1]) / "route_hold_pass.py").is_file()
    src = (ROOT / "physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py").read_text()
    assert '"--route-hold-pass", default="off"' in src
    assert 'route_hold_pass_lines() if a.route_hold_pass == "on"' in src


def test_runner_hook_after_signoff_only_for_finish_route():
    txt = RUNNER.read_text()
    i, j = txt.index('python3 "$K/signoff.py" run'), txt.index("route_hold_pass.py\" run")
    assert i < j < txt.rindex("exit $rc")
    hook = txt[txt.index("# ROUTE-HOLD-PASS"):txt.rindex("exit $rc")]
    cond = [x for x in hook.splitlines() if x.lstrip().startswith("if {")][0]
    assert '[ "$GOAL" = finish ] || [ "$GOAL" = route ]' in cond and "post" not in cond
    assert subprocess.run(["bash", "-n", str(RUNNER)]).returncode == 0


def test_runner_hook_key_regexes_match_generator_lines(tmp_path):
    sys.path.insert(0, str(ROOT / "physical/die_plan/hbm_arch_cores"))
    import gen_core_kit_hbm as G
    cfg = tmp_path / "config.mk"
    cfg.write_text("\n".join(G.route_hold_pass_lines()) + "\n")
    hook = RUNNER.read_text()
    g = re.search(r"grep -qE '([^']+)' \"\$K/config.mk\"", hook)[1]
    sd = re.search(r"sed -nE '([^']+)' \"\$K/config.mk\"", hook)[1]
    assert subprocess.run(["grep", "-qE", g, str(cfg)]).returncode == 0
    got = subprocess.run(["sed", "-nE", sd, str(cfg)], capture_output=True, text=True).stdout.strip()
    assert got == str(HERE)
