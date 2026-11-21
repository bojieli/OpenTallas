"""FLOW-23 HOLD-GUARD-GRT: the single-mode GRT hold repair (ORFS repair_timing_helper from grt_pre.tcl) runs in
buffer-capped chunks and stops on hold met / stall / time cap instead of running unbounded (S81 dpkit 27-47 h, s81_cl
canary 44 h at WNS flat).  Mock OpenROAD in tclsh: repair_timing_helper adds buffers and moves hold WNS per a script."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
GUARD = (HERE / "hold_guard_grt.tcl").read_text()

MOCK = r"""
set ::calls {}
set ::n 1000
set ::ws -50.0
set ::tns -5000.0
set ::need 1000000
namespace eval ord { proc get_db_block {} { return ::blk } }
proc ::blk {m} { return [lrepeat $::n x] }
set ::sdc_log {}
proc write_sdc {args} { lappend ::sdc_log write_sdc; set f [open [lindex $args end] w]; puts $f x; close $f }
proc read_sdc {f} { lappend ::sdc_log read_sdc }
proc all_clocks {} { return {clk} }
proc get_property {o p} { return {clksrc} }
proc get_full_name {o} { return $o }
proc all_inputs {} { return {clksrc din0 din1} }
proc set_false_path {args} { lappend ::sdc_log "false_path $args" }
proc unset_path_exceptions {args} { lappend ::sdc_log "unset $args" }
proc worst_slack {args} { return $::ws }
proc total_negative_slack {args} { return $::tns }
proc repair_timing_helper {args} {
  lappend ::calls $args
  if {[lsearch -exact $args -hold] < 0} { return }
  set j [lsearch -exact $args -max_buffer_percent]
  set cap [expr {int([lindex $args [expr {$j + 1}]] * $::n / 100.0)}]
  # the native repair wants ::need buffers per call; a smaller cap ends it with RSZ-0060 (as OpenROAD does)
  set add [expr {min($cap, $::need)}]
  incr ::n $add
  set ::ws [expr {$::ws + [MODEL]}]
  set ::tns [expr {min(0.0, $::tns * 0.99)}]
  if {$cap <= $::need} { error "\[ERROR RSZ-0060\] Max buffer count reached." }
}
%s
%s
repair_timing_helper -setup_margin 0 -hold_margin 10 -repair_tns 100 -skip_last_gasp -max_buffer_percent 100 -verbose
puts "SDCLOG $::sdc_log"
puts "NCALLS [llength $::calls]"
foreach c $::calls { puts "CALL $c" }
puts "WS $::ws"
"""


def run(model, env=None, preamble=""):
    e = {k: v for k, v in os.environ.items() if not k.startswith("OT_HOLD")}
    e.update({"OT_HOLD_CHUNK_S": "0", "OT_HOLD_CHUNK_BUF_MIN": "20"})   # fixed 20-buffer chunks (2 % of the mock)
    e.update(env or {})
    src = MOCK.replace("[MODEL]", model) % (preamble, GUARD)
    return tcl(src, e)


def tcl(src, env=None):
    # a script FILE: tclsh reading stdin keeps going after an error (rc 0)
    with tempfile.NamedTemporaryFile("w", suffix=".tcl", delete=False) as f:
        f.write(src)
    try:
        r = subprocess.run(["tclsh", f.name], capture_output=True, text=True, env=env, timeout=60)
    finally:
        os.unlink(f.name)
    assert r.returncode == 0 and not r.stderr, r.stderr
    return r.stdout


pytestmark = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")


def calls(out):
    return [l[5:].split() for l in out.splitlines() if l.startswith("CALL ")]


def test_setup_then_chunked_hold_until_margin():
    out = run("20.0")                    # -50 -> -30 -> -10 -> +10: margin reached after 3 chunks
    c = calls(out)
    assert "-setup" in c[0] and "-hold" not in c[0] and c[0][c[0].index("-max_buffer_percent") + 1] == "100"
    hold = c[1:]
    assert len(hold) == 3 and all("-hold" in x and "-setup" not in x for x in hold)
    assert all(float(x[x.index("-max_buffer_percent") + 1]) < 100 for x in hold)
    assert "-hold_margin" in hold[0] and "10" in hold[0]   # margins / options untouched
    assert "OT_HOLD_STALL" not in out


def test_stall_stops_with_marker():
    out = run("0.1", {"OT_HOLD_STALL_WINDOW_S": "0"})       # 0.1 ps/chunk and 1 % TNS < 2 %: stalled
    assert "OT_HOLD_STALL NEEDS_RTL stage=grt reason=stalled" in out
    assert len(calls(out)) == 2


def test_time_cap():
    out = run("0.5", {"OT_HOLD_MAX_HOURS": "0", "OT_HOLD_STALL_WINDOW_S": "99999"})
    # WAVE-FRICTION-1: the wall cap no longer ends the repair; it logs once and continues
    assert "OT_HOLD_TIMELOG" in out and "NO CAP" in out


def test_hold_met_margin_chase_stalls():
    out = run("($::ws >= 3 ? 0.0 : 53.0)", {"OT_HOLD_STALL_MIN_WS": "3"})   # -50 -> 3, then no gain: stop at ws >= the stall floor
    assert "hold met (ws >= stall floor)" in out and len(calls(out)) == 3


def test_native_finish_ends_guard():
    # the native repair ends below the chunk cap (it needs 10 buffers, the chunk allows 20) -> no further chunk
    out = run("1.0", preamble="set ::need 10")
    assert "native hold repair finished inside the chunk" in out and len(calls(out)) == 2


def test_total_budget_kept():
    # the call's own -max_buffer_percent (here 100 % of 1000) still bounds the sum of the chunks
    out = run("0.0001", {"OT_HOLD_MIN_GAIN_PCT": "0", "OT_HOLD_STALL_WINDOW_S": "99999"})
    assert "total buffer budget 100 % used" in out and 50 <= len(calls(out)) - 1 <= 55   # ~20-buffer chunks, 1000 total


def test_disabled_and_mm_inert():
    for env in ({"OT_HOLD_GUARD": "0"}, {"OT_HOLD_MM": "1"}):
        out = run("20.0", env)
        assert len(calls(out)) == 1 and "OT_HOLD_GUARD_GRT" not in out


def test_mm_guard_present_inert():
    out = run("20.0", preamble="proc ot_repair_timing {args} {}")
    assert len(calls(out)) == 1


def test_setup_only_passthrough_and_single_install():
    src = MOCK.replace("[MODEL]", "20.0") % ("", GUARD + "\n" + GUARD)
    src = src.replace("repair_timing_helper -setup_margin 0 -hold_margin 10", "repair_timing_helper -setup -setup_margin 0")
    out = tcl(src)
    assert out.count("OT_HOLD_GUARD_GRT installed") == 1 and len(calls(out)) == 1


def test_hooks_source_guard():
    assert "hold_guard_grt.tcl" in (HERE / "grt_pre.tcl").read_text()
    for f in ("gen_phys.py", "core_flow.py"):
        assert '"hold_guard_grt.tcl"' in (HERE / f).read_text(), f


def test_first_chunk_is_buffer_min():
    # HOLD-CHUNK-1: the first chunk is OT_HOLD_CHUNK_BUF_MIN buffers, not 0.25 % of the instances
    out = run("0.0001", {"OT_HOLD_CHUNK_BUF_MIN": "7", "OT_HOLD_MIN_GAIN_PCT": "0", "OT_HOLD_STALL_WINDOW_S": "99999"})
    assert "(cap 7)" in out


ZV = "namespace eval sta { proc endpoint_violation_count {m} { return [expr {$::ws < 0 ? 5 : 0}] } }"


def test_zero_violators_stops_the_margin_chase():
    out = run("3.0", preamble=ZV)                       # -50 +3 per chunk; margin 10: stops at the first chunk with 0 violators (ws >= 0)
    assert "0 hold violators" in out and float(out.split("WS ")[1]) < 10.0
    off = run("3.0", {"OT_HOLD_ZERO_VIOL_STOP": "0"}, preamble=ZV)
    assert "0 hold violators" not in off and float(off.split("WS ")[1]) >= 10.0


def sdclog(out):
    return [l for l in out.splitlines() if l.startswith("SDCLOG")][0]


def test_input_ports_are_excluded_from_the_hold_repair_and_the_sdc_is_restored():
    """HOLD-SKIP-PORTS 11-19: the hold repair runs with a temporary hold false path from the input data ports (not the clock source); the original SDC is read back"""
    out = run("20.0")
    log = sdclog(out)
    assert "false_path -hold -from {din0 din1}" in log and "clksrc" not in log.split("false_path")[1].split("}")[0]
    assert log.index("write_sdc") < log.index("false_path") < log.index("unset") < log.index("read_sdc")
    assert "OT_HOLD_SKIP_PORTS begin input_ports=2" in out and "restored the full SDC" in out


def test_setup_only_and_opt_outs_leave_the_sdc_alone():
    assert "false_path" not in sdclog(run("20.0", env={"OT_HOLD_SKIP_PORTS": "0"}))
    assert "false_path" not in sdclog(run("20.0", env={"OT_GRT_PORT_HOLD_INCLUDE": "1", "OT_GRT_PORT_HOLD_PORTS": "1"}))       # the explicit port opt-in
    assert "false_path" in sdclog(run("20.0", env={"OT_GRT_PORT_HOLD_INCLUDE": "1"}))                                          # a stale INCLUDE alone (kit made before 11-18 lever 3) is ignored
    assert "false_path" not in sdclog(run("20.0", preamble="set ::ot_grt_nonport_installed native\n"))      # the nonport adapter already scopes it


# FLOW-GRT-RESID 11-21: the FF-only GRT session (OT_VCLK_CORNER=ff) treats the setup half of repair_timing as advisory
def test_ff_session_skips_setup_repair_by_default():
    out = run("20.0", {"OT_VCLK_CORNER": "ff"})
    c = calls(out)
    assert c and all("-setup" not in x for x in c) and all("-hold" in x for x in c)     # hold chunks only
    assert out.count("OT_FF_SETUP_ADVISORY") == 1 and "setup repair skipped" in out


def test_ff_session_cap_mode_and_full_mode():
    out = run("20.0", {"OT_VCLK_CORNER": "ff", "OT_FF_SETUP_MODE": "cap", "OT_FF_SETUP_MAX_PASSES": "7"})
    first = calls(out)[0]
    assert "-setup" in first and first[first.index("-max_passes") + 1] == "7"
    out = run("20.0", {"OT_VCLK_CORNER": "ff", "OT_FF_SETUP_MODE": "full"})
    assert "-setup" in calls(out)[0] and "-max_passes" not in calls(out)[0] and "OT_FF_SETUP_ADVISORY" not in out


def test_tt_session_is_unchanged():
    out = run("20.0")
    assert "-setup" in calls(out)[0] and "OT_FF_SETUP_ADVISORY" not in out


def test_ff_session_setup_only_call_is_skipped():
    pre = "repair_timing_helper -setup_margin 0 -skip_last_gasp\n"
    out = run("20.0", {"OT_VCLK_CORNER": "ff"}, preamble="")
    assert out  # combined call covered above; a setup-only call:
    src = MOCK.replace("[MODEL]", "20.0") % ("", GUARD)
    src = src.replace("repair_timing_helper -setup_margin 0 -hold_margin 10 -repair_tns 100 -skip_last_gasp -max_buffer_percent 100 -verbose",
                      "repair_timing_helper -setup -setup_margin 0 -verbose")
    e = {k: v for k, v in os.environ.items() if not k.startswith("OT_HOLD")}
    e["OT_VCLK_CORNER"] = "ff"
    o = tcl(src, e)
    assert "NCALLS 0" in o and "setup repair skipped" in o
