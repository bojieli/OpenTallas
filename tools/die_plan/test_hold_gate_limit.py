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


def _run(tmp_path, wns, n=5, in_min=None, sdc=None):
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
    if in_min is not None:
        env["OT_HOLD_IN_MIN"] = str(in_min)
    return subprocess.run(["tclsh", str(tmp_path / "hold_gate.tcl")], capture_output=True, text=True, env=env)


@pytest.mark.parametrize("in_min,wns,ok", [(-90, -125.65, True), (-90, -150.5, False), (-40, -99.0, True),
                                           (-40, -100.5, False), (0, -100.5, False), (None, -100.5, False)])
def test_limit_counts_from_contract(tmp_path, in_min, wns, ok):
    r = _run(tmp_path, wns, in_min=in_min)
    assert (r.returncode == 0) == ok, r.stdout + r.stderr
    lim = -100 + min(0, (in_min if in_min is not None else -40) + 40)
    assert f"OT_HOLD_GATE structural limit {float(lim)}" in r.stdout or f"structural limit {lim}" in r.stdout


def test_in_min_read_from_kit_sdc_without_env(tmp_path):
    sdc = "create_clock -name clk\nset_input_delay -min -90.0000 -clock vclk $non_clk_in\n"
    r = _run(tmp_path, -125.65, sdc=sdc)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OT_HOLD_GATE structural limit -150.0 (contract in_min -90.0000 window 0 legacy 0)" in r.stdout
    assert "SID -min -40 -clock vclk" in r.stdout          # the overlay itself is unchanged (env contract only)


def test_endpoint_cap_legacy_only(tmp_path):
    """COORD 10-31: the 2000 cap applies to legacy-contract kits (in_min >= -40, W <= 20) only."""
    assert _run(tmp_path, -10, n=2001, in_min=-40).returncode != 0
    assert _run(tmp_path, -10, n=2001, in_min=-90).returncode == 0


def test_limit_counts_from_window(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_TAP_WINDOW", "130")
    monkeypatch.setenv("OT_HOLD_OUT_MIN", "0")
    assert _run(tmp_path, -161.8, n=11952, in_min=-90).returncode == 0          # HEAD l48y hd_tile: lim -230
    assert _run(tmp_path, -230.5, n=10, in_min=-90).returncode != 0
