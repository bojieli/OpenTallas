"""KIT-TRIAGE-1/G4 11-01: the OT_GPL_GUARD section of the shared face_flops.tcl (PRE_GLOBAL_PLACE of gen_phys type kits
and of every core kit generator that copies it) is the default-on GPL-0305 class fix:
  sparse kit (movable util < OT_GPL_SPARSE_UTIL, default 5 % since KV-101/PC 11-13, was 2 %) -> routability mode off, timing-driven KEPT (QC sle_fw_v1,
  0.6 %; FLOW-21 11-01: S81 hd_turn_a canary regressed when timing-driven was dropped too);
  routability/timing-driven GPL that diverges with GPL-0305 -> one plain retry (HBM q3_vm_core, programme_store_r10);
  every other kit / error unchanged.  OpenDB and global_placement are mocked in tclsh."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

FF = Path(__file__).with_name("face_flops.tcl").read_text()
GUARD = FF[FF.index("# OT_GPL_GUARD begin"):FF.index("# OT_GPL_GUARD end")]
needs_tcl = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")

# core 1000 x 1000 dbu; insts: [status w h x0 y0 isBlock]
MOCK = r"""
namespace eval ord { proc get_db_block {} { return blk } }
namespace eval gpl { proc replace_reset_cmd {} { puts RESET } }
proc core {op} { switch $op { xMin { return 0 } yMin { return 0 } xMax { return 1000 } yMax { return 1000 } } }
set ::insts {%(INSTS)s}
proc blk {op args} { switch $op { getCoreArea { return core } getInsts { set r {}; set k 0
  foreach x $::insts { lappend r "i$k"; incr k }; return $r } } }
proc unknown {cmd args} {
  if {[regexp {^i(\d+)$} $cmd -> k]} { lassign [lindex $::insts $k] st w h x y b
    switch [lindex $args 0] { getPlacementStatus { return $st } getMaster { return "m$k" }
      getBBox { return "bb$k" } } }
  if {[regexp {^m(\d+)$} $cmd -> k]} { lassign [lindex $::insts $k] st w h x y b
    switch [lindex $args 0] { getWidth { return $w } getHeight { return $h } isBlock { return $b } } }
  if {[regexp {^bb(\d+)$} $cmd -> k]} { lassign [lindex $::insts $k] st w h x y b
    switch [lindex $args 0] { xMin { return $x } yMin { return $y } xMax { return [expr {$x+$w}] } yMax { return [expr {$y+$h}] } } }
  error "unknown $cmd"
}
# mock gpl: %(GPL)s
set ::calls 0
proc global_placement {args} {
  incr ::calls
  puts "CALL $::calls: $args"
  set modal [expr {[lsearch $args -routability_driven] >= 0 || [lsearch $args -timing_driven] >= 0}]
  switch $::gpl_mode {
    ok { return done }
    diverge_modal { if {$modal} { error "GPL-0305" } ; return done }
    diverge_all { error "GPL-0305" }
    other { error "GPL-0301" }
  }
}
set ::gpl_mode %(GPL)s
set ::env(GPL_ROUTABILITY_DRIVEN) 1; set ::env(GPL_TIMING_DRIVEN) 1
%(ENV)s
"""

ARGS = ("-density 0.5 -pad_left 1 -pad_right 1 -routability_driven -random_seed 1 -timing_driven "
        "-keep_resize_below_overflow 0.3 -force_center_initial_place -min_phi_coef 0.95 -max_phi_coef 1.04")
NOROUTE = ("-density 0.5 -pad_left 1 -pad_right 1 -random_seed 1 -timing_driven "
           "-keep_resize_below_overflow 0.3 -force_center_initial_place -min_phi_coef 0.95 -max_phi_coef 1.04")
PLAIN = "-density 0.5 -pad_left 1 -pad_right 1 -random_seed 1 -force_center_initial_place -min_phi_coef 0.95 -max_phi_coef 1.04"
DENSE = [("FIRM", 500, 1000, 0, 0, 0), ("PLACED", 100, 500, 0, 0, 0)]     # 10 %
SPARSE = [("FIRM", 500, 1000, 0, 0, 0), ("PLACED", 100, 50, 0, 0, 0)]     # 1 %


def _run(insts, gpl="ok", env="", call=ARGS, sources=1):
    body = MOCK % dict(INSTS=" ".join("{" + " ".join(map(str, i)) + "}" for i in insts), ENV=env, GPL=gpl)
    tail = ('\nset rc [catch {global_placement ' + call + '} res]\n'
            'puts "RC=$rc RES=$res CALLS=$::calls RD=$::env(GPL_ROUTABILITY_DRIVEN) TD=$::env(GPL_TIMING_DRIVEN)"\n')
    out = subprocess.run(["tclsh"], input=body + GUARD * sources + tail, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return out.stdout


def test_guard_is_the_last_section_of_the_shared_hook():
    assert FF.count("# OT_GPL_GUARD begin") == 1 and FF.rstrip().endswith("# OT_GPL_GUARD end")


@needs_tcl
def test_sparse_kit_drops_routability_keeps_timing_driven():
    out = _run(SPARSE)
    assert re.search(r"movable util 1\.000 %", out) and "routability-driven GPL off" in out, out
    assert f"CALL 1: {NOROUTE}\n" in out and "RC=0 RES=done CALLS=1 RD=0 TD=1" in out, out


@needs_tcl
def test_sparse_kit_divergence_still_falls_back_plain():
    out = _run(SPARSE, "diverge_modal")
    assert f"CALL 1: {NOROUTE}\n" in out and f"CALL 2: {PLAIN}\n" in out, out
    assert "OT_GPL_FALLBACK GPL-0305" in out and "RC=0 RES=done CALLS=2 RD=0 TD=0" in out, out
    out = _run(SPARSE, "diverge_modal", env="set ::env(OT_GPL_FALLBACK) 0")
    assert "RC=1 RES=GPL-0305 CALLS=1 RD=0 TD=1" in out, out


@needs_tcl
def test_sparse_routability_only_call_runs_plain_once():
    out = _run(SPARSE, "diverge_all", call="-density 0.5 -routability_driven -random_seed 1")
    assert "CALL 1: -density 0.5 -random_seed 1\n" in out and "RC=1 RES=GPL-0305 CALLS=1 RD=0 TD=0" in out, out


@needs_tcl
def test_dense_kit_unchanged():
    out = _run(DENSE)
    assert "GPL modes unchanged" in out and f"CALL 1: {ARGS}\n" in out, out
    assert "RC=0 RES=done CALLS=1 RD=1 TD=1" in out and "OT_GPL_FALLBACK" not in out, out


@needs_tcl
def test_gpl_0305_under_modal_gpl_retries_once_plain():
    out = _run(DENSE, "diverge_modal")
    assert f"CALL 1: {ARGS}\n" in out and f"CALL 2: {PLAIN}\n" in out, out
    assert "OT_GPL_FALLBACK GPL-0305" in out and "RESET" in out, out
    assert "RC=0 RES=done CALLS=2 RD=0 TD=0" in out, out


@needs_tcl
def test_plain_divergence_and_other_errors_still_fail():
    out = _run(DENSE, "diverge_all")
    assert "RC=1 RES=GPL-0305 CALLS=2" in out, out                          # one retry only
    out = _run(DENSE, "other")
    assert "RC=1 RES=GPL-0301 CALLS=1" in out and "OT_GPL_FALLBACK" not in out, out


@needs_tcl
def test_already_plain_call_passes_through():
    out = _run(SPARSE, "diverge_all", call=PLAIN)
    assert "OT_GPL_SPARSE" not in out and "RC=1 RES=GPL-0305 CALLS=1" in out, out


@needs_tcl
def test_switches_disable_each_rule():
    out = _run(SPARSE, "diverge_modal", env="set ::env(OT_GPL_SPARSE_UTIL) 0")
    assert "OT_GPL_SPARSE off" in out and "RC=0 RES=done CALLS=2" in out, out   # fallback still on
    out = _run(DENSE, "diverge_modal", env="set ::env(OT_GPL_FALLBACK) 0")
    assert "RC=1 RES=GPL-0305 CALLS=1 RD=1 TD=1" in out, out
    insts = [("PLACED", 100, 50, 0, 0, 0)]                                                  # 0.5 %
    assert "CALLS=1 RD=1 TD=1" in _run(insts, env="set ::env(OT_GPL_SPARSE_UTIL) 0.004")
    assert "CALLS=1 RD=0 TD=1" in _run(insts, env="set ::env(OT_GPL_SPARSE_UTIL) 0.01")


@needs_tcl
def test_firm_outside_core_and_movable_macro_ignored():
    out = _run([("FIRM", 500, 1000, 2000, 0, 0), ("UNPLACED", 900, 900, 0, 0, 1), ("PLACED", 100, 100, 0, 0, 0)])
    assert re.search(r"movable util 1\.000 %", out) and "RD=0 TD=1" in out, out


@needs_tcl
def test_sourcing_twice_wraps_once():
    out = _run(DENSE, "diverge_all", sources=2)
    assert "RC=1 RES=GPL-0305 CALLS=2" in out, out


@needs_tcl
def test_default_threshold_covers_the_silent_blowup_band():
    """KV-101/PC 11-13: kv3_pc_v1 (2.40 %) and S81 dsdv C t1 (2.86 / 3.08 %) diverged silently under routability mode
    (GPL-0089 revert, HPWL x5-6, 0.4-0.9 M buffers from the second timing-driven pass).  Default 5 %: those drop
    routability and keep timing-driven; a kit at 6 % and the 10 % DENSE kit are unchanged."""
    pc = [("FIRM", 500, 1000, 0, 0, 0), ("PLACED", 100, 120, 0, 0, 0)]                 # 2.4 % of the free half
    out = _run(pc)
    assert re.search(r"movable util 2\.400 % < 5\.000 %", out) and "CALLS=1 RD=0 TD=1" in out, out
    six = [("FIRM", 500, 1000, 0, 0, 0), ("PLACED", 100, 300, 0, 0, 0)]                # 6 %
    out = _run(six)
    assert "GPL modes unchanged" in out and "CALLS=1 RD=1 TD=1" in out, out
    assert "CALLS=1 RD=1 TD=1" in _run(pc, env="set ::env(OT_GPL_SPARSE_UTIL) 0.02")   # old default still selectable
