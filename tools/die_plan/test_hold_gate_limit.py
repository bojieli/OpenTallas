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


def _run(tmp_path, wns, n=5, in_min=None, sdc=None, win=None, stop=True, period=None):
    if shutil.which("tclsh") is None:
        pytest.skip("no tclsh")
    stubs = STUBS.replace("proc sta::worst_slack_cmd {args} {return 1}", f"proc sta::worst_slack_cmd {{args}} {{return {wns}}}")
    stubs = stubs.replace("proc sta::endpoint_violation_count {args} {return 0}",
                          f"proc sta::endpoint_violation_count {{args}} {{return {n}}}")
    if period is not None:
        stubs = stubs.replace('proc get_property {o k} {', 'proc get_property {o k} { if {$k eq "period"} {return %s};' % period)
    (tmp_path / "hold_gate.tcl").write_text(stubs + (HERE / "hold_gate.tcl").read_text())
    if sdc is not None:
        (tmp_path / "constraint.sdc").write_text(sdc)
    env = dict(os.environ)
    env.pop("OT_HOLD_IN_MIN", None)
    env.pop("OT_TAP_WINDOW", None)
    env.pop("OT_HOLD_PREROUTE_STOP", None)
    if stop:  # the legacy limit tests below exercise the opt-in stop; the default is the INFO screen (G5 tests)
        env["OT_HOLD_PREROUTE_STOP"] = "1"
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


# KIT-TRIAGE-1/G5 11-01 (OWNER 12.28b closure first, METHODOLOGY 12.4 a1): by default the limit/cap is a pre-repair
# screen; the kit continues to repair_timing -hold and the routed FF hold sign-off.  Only the -200 ps contract-relative
# stop (COORD 11-01 05:1x) stops.  Numbers: S81 slice_station kits of the 10-31 wave.
@pytest.mark.parametrize("wns,n,win", [(-137.03, 5012, 180), (-279.67, 5947, 140), (-99.71, 4626, 180),
                                       (-237.90, 2778, 100), (-121.23, 2858, None)])
def test_default_screen_is_info(tmp_path, wns, n, win):
    r = _run(tmp_path, wns, n=n, in_min=-40, win=win, stop=False, period=833)
    assert r.returncode == 0, r.stdout + r.stderr
    lim = -100 + min(0, -(win or 0))
    if wns < lim or (n > 2000 and (win or 0) <= 20):
        assert f"OT_HOLD_GATE INFO FF wns_ps {wns:.2f} endpoints {n} " in r.stdout
    else:
        assert f"OT_HOLD_GATE PASS FF wns_ps {wns:.2f} endpoints {n} " in r.stdout


# COORD 11-01 05:1x / OWNER 12.28b: the one default stop is OT_HOLD_STOP_PS = -200 (COORD 11-05 07:36), counted from the kit contract like
# the FLOW-19 limit (stop = -200 + min(0, in_min + 40, -W_t)), so never stricter than main's limit.
def test_default_stops_below_minus_150_on_legacy_contract(tmp_path):
    r = _run(tmp_path, -200.01, n=10, in_min=-40, stop=False, period=833)
    assert r.returncode != 0
    assert ("OT_HOLD_GATE FAIL FF wns_ps -200.01 endpoints 10 (true negative slack): beyond the structural stop -200.0 ps "
            "(OT_HOLD_STOP_PS -200 from contract)") in r.stdout
    r = _run(tmp_path, -200.0, n=10, in_min=-40, stop=False, period=833)
    assert r.returncode == 0 and "OT_HOLD_GATE INFO" in r.stdout, r.stdout + r.stderr


@pytest.mark.parametrize("wns,win,stops", [(-299.9, 100, False), (-300.1, 100, True), (-329.67, 140, False),
                                           (-341.0, 140, True)])
def test_default_stop_counts_from_tap_window(tmp_path, wns, win, stops):
    r = _run(tmp_path, wns, n=10, in_min=-40, win=win, stop=False)
    assert (r.returncode != 0) == stops, r.stdout + r.stderr
    assert ("OT_HOLD_GATE FAIL" if stops else "OT_HOLD_GATE INFO") in r.stdout


def test_default_stop_counts_from_seam_contract(tmp_path):
    r = _run(tmp_path, -190.0, n=10, in_min=-90, stop=False)      # stop -200 + (-90 + 40) = -250
    assert r.returncode == 0 and "OT_HOLD_GATE INFO" in r.stdout, r.stdout + r.stderr


def test_stop_override_opt_in(tmp_path, monkeypatch):
    # DIE-HEAD-59 11-03: OT_HOLD_STOP_PS moves the stop base; the default stop is unchanged without it
    assert "structural stop" in _run(tmp_path, -264.78, in_min=-90).stdout
    monkeypatch.setenv("OT_HOLD_STOP_PS", "-250")
    r = _run(tmp_path, -264.78, in_min=-90)
    assert "structural stop" not in r.stdout
