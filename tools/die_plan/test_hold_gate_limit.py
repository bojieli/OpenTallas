"""COORD 18:0x (3) (A), FLOW-19 10-31: hold_gate.tcl structural limit counted from the kit's seam contract,
lim = -100 + min(0, in_min + 40); in_min from OT_HOLD_IN_MIN, else the kit SDC; endpoint cap 2000 unchanged.
    python3 -m pytest -q tools/die_plan/test_hold_gate_limit.py"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
from test_hold_gate_ring import STUBS  # noqa: E402


def _run(tmp_path, wns, n=5, in_min=None, sdc=None, win=None):
    if shutil.which("tclsh") is None:
        pytest.skip("no tclsh")
    stubs = STUBS.replace("proc sta::worst_slack_cmd {args} {return 1}", f"proc sta::worst_slack_cmd {{args}} {{return {wns}}}")
    stubs = stubs.replace("proc sta::endpoint_violation_count {args} {return 0}",
                          f"proc sta::endpoint_violation_count {{args}} {{return {n}}}")
    (tmp_path / "hold_gate.tcl").write_text(stubs + (HERE / "hold_gate.tcl").read_text())
    if sdc is not None:
        (tmp_path / "constraint.sdc").write_text(sdc)
    env = dict(os.environ)
    env.pop("OT_HOLD_IN_MIN", None)
    env.pop("OT_TAP_WINDOW", None)
    if in_min is not None:
        env["OT_HOLD_IN_MIN"] = str(in_min)
    if win is not None:
        env["OT_TAP_WINDOW"] = str(win)
    return subprocess.run(["tclsh", str(tmp_path / "hold_gate.tcl")], capture_output=True, text=True, env=env)


@pytest.mark.parametrize("in_min,wns,ok", [(-90, -125.65, True), (-90, -150.5, False), (-40, -99.0, True),
                                           (-40, -100.5, False), (0, -100.5, False), (None, -100.5, False)])
def test_limit_counts_from_contract(tmp_path, in_min, wns, ok):
    r = _run(tmp_path, wns, in_min=in_min)
    assert (r.returncode == 0) == ok, r.stdout + r.stderr
    lim = -100 + min(0, (in_min if in_min is not None else -40) + 40)
    assert f"OT_HOLD_GATE structural limit {float(lim)} " in r.stdout


def test_in_min_read_from_kit_sdc_without_env(tmp_path):
    sdc = "create_clock -name clk\nset_input_delay -min -90.0000 -clock vclk $non_clk_in\n"
    r = _run(tmp_path, -125.65, sdc=sdc)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OT_HOLD_GATE structural limit -150.0 (contract in_min -90.0000," in r.stdout
    assert "SID -min -40 -clock vclk" in r.stdout          # the overlay itself is unchanged (env contract only)


def test_endpoint_cap_legacy_contract_only(tmp_path):
    # legacy contract (in_min >= -40, W_t <= 20): cap 2000 as before
    assert _run(tmp_path, -10, n=2001, in_min=-40).returncode != 0
    assert _run(tmp_path, -10, n=2001, in_min=-40, win=20).returncode != 0
    # contract kits: no endpoint cap (HEAD hd_spn_end l49x -115.12 / 4437 at in_min -90)
    r = _run(tmp_path, -115.12, n=4437, in_min=-90)
    assert r.returncode == 0 and "endpoint cap none" in r.stdout, r.stdout + r.stderr
    assert _run(tmp_path, -10, n=5000, in_min=-40, win=60).returncode == 0


@pytest.mark.parametrize("in_min,win,wns,ok", [(-90, 130, -161.80, True), (-90, 130, -230.5, False),
                                               (-40, 60, -159.0, True), (-40, 60, -160.5, False),
                                               (-90, 20, -125.0, True), (-40, 20, -119.0, True),
                                               (-40, 20, -120.5, False), (-40, 0, -100.5, False)])
def test_limit_counts_tap_window(tmp_path, in_min, win, wns, ok):
    # HEAD hd_tile l48y: W_hd_tile 130 -> lim -230 (wns -161.80 / 11952 endpoints)
    r = _run(tmp_path, wns, n=11952 if win > 20 or in_min < -40 else 5, in_min=in_min, win=win)
    assert (r.returncode == 0) == ok, r.stdout + r.stderr
    assert f"structural limit {float(-100 + min(0, in_min + 40, -win))} " in r.stdout
