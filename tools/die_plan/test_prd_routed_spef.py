"""FLOW-11 10-30 (DIE-QC-50 BTAB): the post-route ECO session keeps the routed SPEF over every later estimate."""
import shutil
import subprocess
from pathlib import Path

import pytest

PRD = Path(__file__).resolve().parent / "post_route_drv"
pytestmark = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")


def _procs():
    s = (PRD / "prd_hook.tcl").read_text()
    a = s.index("proc ot_prd_spef_read")
    b = s.index("\nproc ot_prd_spef_arm")
    e = s.index("\n}\n", s.index("proc ::estimate_parasitics", b)) + 3
    return s[a:e]


MOCK = """proc read_spef {args} { puts "READ $args" }
proc estimate_parasitics {args} { puts "EST $args"; return est }
"""


def _run(body, env=""):
    r = subprocess.run(["tclsh"], input=MOCK + env + _procs() + body, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return [l for l in r.stdout.splitlines() if l.startswith(("READ", "EST"))]


def test_two_mode_session_rereads_routed_spef_in_both_scenes_after_every_estimate():
    out = _run("set ::ot_mm_active 1\nproc ot_mm_sc {} { return WC }\not_prd_spef_arm /r/6_final.spef\n"
               "puts [estimate_parasitics -global_routing]\nestimate_parasitics -placement\n")
    assert out == ["READ -corner WC /r/6_final.spef", "READ -corner BC /r/6_final.spef",
                   "EST -global_routing", "READ -corner WC /r/6_final.spef", "READ -corner BC /r/6_final.spef",
                   "EST -placement", "READ -corner WC /r/6_final.spef", "READ -corner BC /r/6_final.spef"]


def test_single_corner_session_and_rearm_wraps_once():
    out = _run("ot_prd_spef_arm /r/s.spef\not_prd_spef_arm /r/s.spef\nestimate_parasitics -global_routing\n")
    assert out == ["READ /r/s.spef", "READ /r/s.spef", "EST -global_routing", "READ /r/s.spef"]


def test_opt_out_is_the_old_single_read():
    out = _run("ot_prd_spef_arm /r/s.spef\nestimate_parasitics -global_routing\n",
               env="set ::env(OT_PRD_ROUTED_SPEF) 0\n")
    assert out == ["READ /r/s.spef", "EST -global_routing"]


def test_hook_arms_before_the_freeze_and_repairs():
    s = (PRD / "prd_hook.tcl").read_text()
    order = ["ot_prd_spef_arm $::env(RESULTS_DIR)/6_final.spef", "ot_clk_freeze\n", "repair_design {*}${_drv_args}",
             "ot_repair_hold_guarded $args"]
    pos = [s.index(x) for x in order]
    assert pos == sorted(pos)
    assert "\n  read_spef $::env(RESULTS_DIR)/6_final.spef" not in s
