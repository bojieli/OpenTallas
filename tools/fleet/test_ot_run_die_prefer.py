"""DIECLASS_1125 (COORD 11-25 00:3x): die-class jobs prefer epyc12 (the die slice), then epyc7, intel1; kits keep the normal choice."""
import importlib.machinery, importlib.util, os
from pathlib import Path

P = str(Path(__file__).with_name("ot-run"))
_l = importlib.machinery.SourceFileLoader("ot_run_die_prefer", P)
R = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_die_prefer", _l))
_l.exec_module(R)


def row(free, ncpu=96, load=10.0):
    return {"free_gb": free, "admit_gb": free, "avail_gb": free, "ncpu": ncpu, "load1": load, "load": load}


def test_die_level_commands_detected():
    assert R.die_level_cmd(["python3", "-I", "tools/die_plan/plan_gate_pre.py", "check"])
    assert R.die_level_cmd("bash /l/kv-allfix/a5t7i1/run_a5t7_gate.sh")
    assert R.die_level_cmd(["python3", "tools/die_plan/bind.py", "bind", "p.json"])
    assert not R.die_level_cmd(["python3", "tools/die_plan/bind.py", "kit-rtl", "--type", "x"])
    assert not R.die_level_cmd(["openroad", "-exit", "route.tcl"])


def test_die_prefers_epyc12_then_epyc7_then_intel1(monkeypatch):
    monkeypatch.setattr(R, "physically_capable", lambda r, m: True)
    res = {"epyc2": row(900), "epyc12": row(100, load=200.0), "epyc7": row(500), "intel1": row(400, ncpu=112)}
    R.PREFER_DIE[0] = True
    try:
        assert R.choose(dict(res), 64)[0] == "epyc12"
        res.pop("epyc12")
        assert R.choose(dict(res), 64)[0] == "epyc7"
        res.pop("epyc7")
        assert R.choose(dict(res), 64)[0] == "intel1"
    finally:
        R.PREFER_DIE[0] = False


def test_type_job_not_steered(monkeypatch):
    monkeypatch.setattr(R, "physically_capable", lambda r, m: True)
    monkeypatch.setattr(R, "_choose", lambda res, mem, threads, die: ("epyc2", False))
    R.PREFER_DIE[0] = False
    assert R.choose({"epyc2": row(900), "epyc12": row(900)}, 64)[0] == "epyc2"


def test_die_spills_from_a_host_over_2_5x_cores_to_the_next_listed_one(monkeypatch):
    """FLEET-OPS 11-25: epyc12 at load 304/96 -> epyc7; epyc8 and epyc10 are on the die list after intel1"""
    monkeypatch.setattr(R, "physically_capable", lambda r, m: True)
    res = {"epyc12": row(300, load=304.0), "epyc7": row(300, load=102.0), "intel1": row(300, ncpu=112, load=90.0), "epyc8": row(500, load=78.0), "epyc10": row(600, load=50.0)}
    R.PREFER_DIE[0] = True
    try:
        assert R.choose(dict(res), 64)[0] == "epyc7"
        res["epyc7"] = row(300, load=300.0); res["intel1"] = row(300, ncpu=112, load=400.0)
        assert R.choose(dict(res), 64)[0] == "epyc8"
        res["epyc8"] = row(500, load=300.0)
        assert R.choose(dict(res), 64)[0] == "epyc10"
        res["epyc10"] = row(600, load=300.0)
        assert R.choose(dict(res), 64)[0] == "epyc12"          # all saturated: the first listed host, as before
        monkeypatch.setenv("OT_RUN_DIE_SPILL_X", "0")
        res["epyc7"] = row(300, load=10.0)
        assert R.choose(dict(res), 64)[0] == "epyc12"          # 0 = the old order
    finally:
        R.PREFER_DIE[0] = False
