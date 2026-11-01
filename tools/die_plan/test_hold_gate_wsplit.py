"""DIE-HEAD-53 (opt-in OT_HOLD_WINDOW_SPLIT=1): hold_gate.tcl splits the plan tap-window (W) demand from the kit's
structural hold: structural = re-timed with the kit SDC window lines at 0 (ws >= lim, internal endpoints <= 2000,
input-port endpoints = planned demand), contract = real SDC ws >= lim - W.  Off: unchanged.
    python3 -m pytest -q tools/die_plan/test_hold_gate_wsplit.py"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
from test_hold_gate_ring import STUBS  # noqa: E402

EXTRA = """
set ::W0 0
proc set_clock_latency {args} { set ::W0 1; puts "SCL $args" }
proc sta::worst_slack_cmd {args} { if {$::W0} {return $::WS0}; return $::WS }
proc sta::endpoint_violation_count {args} { if {$::W0} {return $::N0}; return $::N }
proc get_ports {x} { return $x }
proc find_timing_paths {args} { return [dict keys $::PD] }
rename get_property _gp0
proc get_property {o k} { if {[string match path* $o]} { return [dict get $::PD $o $k] }; return [_gp0 $o $k] }
"""
SDC = ("create_clock -name clk\n"
       "set_clock_latency -source -early -clock clk -130.0000 [get_ports {clk clk_t1}]\n"
       "set_clock_latency -source -late -clock clk 0.0000 [get_ports {clk clk_t1}]\n"
       "set_clock_latency -source -early -clock clk -45.0000 [get_ports {clk_c1}]\n")


def _run(tmp_path, ws, n, ws0, n0, internal, inputs, split=True, sdc=SDC):
    if shutil.which("tclsh") is None:
        pytest.skip("no tclsh")
    pd = "set ::PD [dict create]\n"
    pd += f"for {{set i 0}} {{$i < {internal}}} {{incr i}} {{ dict set ::PD path_i$i slack -20.0; dict set ::PD path_i$i startpoint u$i/q }}\n"
    pd += f"for {{set i 0}} {{$i < {inputs}}} {{incr i}} {{ dict set ::PD path_p$i slack -42.0; dict set ::PD path_p$i startpoint a }}\n"
    pd += "dict set ::PD path_ok slack 3.0; dict set ::PD path_ok startpoint b\n"
    head = STUBS + EXTRA + f"set ::WS {ws}; set ::N {n}; set ::WS0 {ws0}; set ::N0 {n0}\n" + pd
    (tmp_path / "hold_gate.tcl").write_text(head + (HERE / "hold_gate.tcl").read_text())
    if sdc is not None:
        (tmp_path / "constraint.sdc").write_text(sdc)
    env = dict(os.environ, OT_HOLD_IN_MIN="-90", OT_HOLD_OUT_MIN="0", OT_TAP_WINDOW="130")
    env.pop("OT_HOLD_WINDOW_SPLIT", None)
    if split:
        env["OT_HOLD_WINDOW_SPLIT"] = "1"
    return subprocess.run(["tclsh", str(tmp_path / "hold_gate.tcl")], capture_output=True, text=True, env=env)


def test_l48y_shape_passes_with_split(tmp_path):
    r = _run(tmp_path, -161.8, 11952, -131.1, 3373, internal=1100, inputs=2273)
    assert r.returncode == 0, r.stdout + r.stderr
    scl = [ln for ln in r.stdout.splitlines() if ln.startswith("SCL")]
    assert scl == ["SCL -source -early -clock clk 0 {clk clk_t1}"], scl     # only the -W window line is zeroed
    assert "internal 1100 (ws -20.00) + planned input 2273 (ws -42.00)" in r.stdout
    assert "OT_HOLD_GATE PASS FF wns_ps -161.80 endpoints 11952" in r.stdout


def test_split_off_is_unchanged(tmp_path):
    r = _run(tmp_path, -161.8, 11952, -131.1, 3373, internal=1100, inputs=2273, split=False)
    assert r.returncode != 0 and "OT_HOLD_GATE FAIL FF wns_ps -161.80 endpoints 11952" in r.stdout
    assert "SCL" not in r.stdout


@pytest.mark.parametrize("ws,ws0,internal", [(-281.0, -131.1, 10), (-161.8, -151.0, 10), (-161.8, -131.1, 2001)])
def test_split_still_fails_structural_or_beyond_contract(tmp_path, ws, ws0, internal):
    r = _run(tmp_path, ws, 9999, ws0, 3000, internal=internal, inputs=5)
    assert r.returncode != 0, r.stdout + r.stderr
    assert "OT_HOLD_GATE FAIL" in r.stdout


def test_split_without_window_line_fails_closed(tmp_path):
    r = _run(tmp_path, -161.8, 11952, -131.1, 3373, internal=10, inputs=5, sdc="create_clock -name clk\n")
    assert r.returncode != 0 and "no 'set_clock_latency -source -early -130" in r.stderr


def test_split_not_needed_when_plain_pass(tmp_path):
    r = _run(tmp_path, -20.0, 10, -1.0, 1, internal=1, inputs=0)
    assert r.returncode == 0 and "WINDOW_SPLIT" not in r.stdout and "OT_HOLD_GATE PASS FF wns_ps -20.00" in r.stdout
