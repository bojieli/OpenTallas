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


# ---- rule 3 (FABLE-FIX-S81-STRIP 11-16): sparse exit overflow, opt-in OT_GPL_SPARSE_OVERFLOW ----
OVF = "set ::env(OT_GPL_SPARSE_OVERFLOW) 0.25"
# timing-driven call at exit 0.25: second pass at 0.30, buffers kept below 0.35 (the kit's 0.3 is raised)
NOROUTE_X = (NOROUTE.replace("-keep_resize_below_overflow 0.3", "-keep_resize_below_overflow 0.35")
             + " -timing_driven_net_reweight_overflow {64 30} -overflow 0.25")


@needs_tcl
def test_sparse_exit_overflow_added_to_sparse_kit_only():
    out = _run(SPARSE, env=OVF)
    assert f"CALL 1: {NOROUTE_X}\n" in out and "OT_GPL_SPARSE exit overflow 0.25" in out, out
    assert "RC=0 RES=done CALLS=1 RD=0 TD=1" in out, out
    out = _run(DENSE, env=OVF)                                              # 10 %: not sparse, call unchanged
    assert f"CALL 1: {ARGS}\n" in out and "-overflow" not in out and "RD=1 TD=1" in out, out


@needs_tcl
def test_sparse_exit_overflow_off_is_the_old_call():
    for env in ("", "set ::env(OT_GPL_SPARSE_OVERFLOW) 0", 'set ::env(OT_GPL_SPARSE_OVERFLOW) ""'):
        out = _run(SPARSE, env=env)
        assert f"CALL 1: {NOROUTE}\n" in out and "-overflow" not in out, (env, out)


@needs_tcl
def test_sparse_exit_overflow_replaces_a_smaller_explicit_overflow():
    # GPL-EXIT-WINS-1122: the S81 die -overflow 0.2 must not disable the sparse early stop 0.25
    out = _run(SPARSE, env=OVF, call=ARGS + " -overflow 0.2")
    assert f"CALL 1: {NOROUTE_X}\n" in out and "replaces the explicit -overflow 0.2" in out, out
    assert "-overflow 0.2 " not in out.split("CALL 1: ")[1].splitlines()[0] + " ", out


def test_sparse_exit_overflow_keeps_a_larger_explicit_overflow():
    out = _run(SPARSE, env=OVF, call=ARGS + " -overflow 0.3")
    assert f"CALL 1: {NOROUTE} -overflow 0.3\n" in out and "replaces" not in out, out


@needs_tcl
def test_sparse_exit_keeps_the_second_timing_driven_pass():
    td = "-density 0.5 -timing_driven -keep_resize_below_overflow %s -min_phi_coef 0.95"
    out = _run(SPARSE, env=OVF, call=td % "0.25")                           # the S81 leaf kit call
    assert ("CALL 1: " + td % "0.35" + " -timing_driven_net_reweight_overflow {64 30} -overflow 0.25\n") in out, out
    out = _run(SPARSE, env=OVF, call=td % "0.5")                            # a higher keep threshold is not lowered
    assert ("CALL 1: " + td % "0.5" + " -timing_driven_net_reweight_overflow {64 30} -overflow 0.25\n") in out, out
    out = _run(SPARSE, env=OVF, call="-density 0.5 -timing_driven")         # no keep threshold named: one is added
    assert "CALL 1: -density 0.5 -timing_driven -keep_resize_below_overflow 0.35 -timing_driven_net_reweight_overflow {64 30} -overflow 0.25\n" in out, out
    own = td % "0.25" + " -timing_driven_net_reweight_overflow {79 40}"     # the kit's own list is kept
    out = _run(SPARSE, env=OVF, call=own)
    assert ("CALL 1: " + own.replace("0.25", "0.35") + " -overflow 0.25\n") in out, out
    out = _run(SPARSE, env="set ::env(OT_GPL_SPARSE_OVERFLOW) 0.3", call=td % "0.25")
    assert "-keep_resize_below_overflow 0.4 " in out and "{64 35} -overflow 0.3\n" in out, out


@needs_tcl
def test_sparse_exit_overflow_reaches_plain_call_and_fallback_retry():
    out = _run(SPARSE, env=OVF, call=PLAIN)                                 # gen phys --gpl-plain kit
    assert f"CALL 1: {PLAIN} -overflow 0.25\n" in out and "RC=0 RES=done CALLS=1" in out, out
    out = _run(SPARSE, "diverge_all", env=OVF, call=PLAIN)                  # a plain call is never retried
    assert "RC=1 RES=GPL-0305 CALLS=1" in out, out
    out = _run(SPARSE, "diverge_modal", env=OVF)
    assert f"CALL 2: {PLAIN} -overflow 0.25\n" in out and "RC=0 RES=done CALLS=2 RD=0 TD=0" in out, out
    out = _run(DENSE, "diverge_modal", env=OVF)                             # dense fallback: no exit change
    assert f"CALL 2: {PLAIN}\n" in out, out


@needs_tcl
def test_sparse_exit_overflow_bad_value_is_an_error():
    for bad in ("abc", "1.0", "-0.1"):
        out = _run(SPARSE, env=f"set ::env(OT_GPL_SPARSE_OVERFLOW) {bad}")
        assert "RC=1" in out and "OT_GPL_SPARSE_OVERFLOW must be" in out and "CALLS=0" in out, (bad, out)


def test_gen_phys_sparse_overflow_default_s81_only(monkeypatch):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import gen_phys as P
    monkeypatch.delenv("OT_GPL_SPARSE_OVERFLOW", raising=False)
    assert P.gpl_sparse_overflow("s81") == 0.25
    assert P.gpl_sparse_overflow("qwen_kvsys") is None and P.gpl_sparse_overflow(None) is None
    assert "export OT_GPL_SPARSE_OVERFLOW = 0.25" in P.gpl_sparse_overflow_cfg("s81")
    assert P.gpl_sparse_overflow_cfg("hbm") == []
    monkeypatch.setenv("OT_GPL_SPARSE_OVERFLOW", "0.3")
    assert P.gpl_sparse_overflow("hbm") == 0.3 and "export OT_GPL_SPARSE_OVERFLOW = 0.3" in P.gpl_sparse_overflow_cfg("hbm")
    monkeypatch.setenv("OT_GPL_SPARSE_OVERFLOW", "0")
    assert P.gpl_sparse_overflow("s81") is None and P.gpl_sparse_overflow_cfg("s81") == []
    for bad in ("1", "-0.2", "x"):
        monkeypatch.setenv("OT_GPL_SPARSE_OVERFLOW", bad)
        with pytest.raises(ValueError):
            P.gpl_sparse_overflow("s81")


@needs_tcl
def test_sparse_spread_caps_density_and_raises_pad_only_on_sparse_kits():
    # FABLE-FIX-S81-SERDES 11-17: S81 serdes__t13 H3p packed 1.4 % of movable cells to the 0.5 target (DRT-0255)
    env = "set ::env(OT_GPL_SPARSE_DENSITY) 0.3; set ::env(OT_GPL_SPARSE_PAD) 2"
    out = _run(SPARSE, env=env)
    want = NOROUTE.replace("-density 0.5 -pad_left 1 -pad_right 1", "-density 0.3 -pad_left 2 -pad_right 2")
    assert "OT_GPL_SPARSE spread" in out and f"CALL 1: {want}\n" in out, out
    out = _run(DENSE, env=env)                                   # a dense kit keeps its arguments
    assert "OT_GPL_SPARSE spread" not in out and f"CALL 1: {ARGS}\n" in out, out
    out = _run(SPARSE, env="set ::env(OT_GPL_SPARSE_DENSITY) 0.6")     # never raises a lower target, pad untouched
    assert f"CALL 1: {NOROUTE}\n" in out, out
    out = _run(SPARSE, "diverge_modal", env=env)                  # the plain retry is spread too
    assert "CALL 2: " + PLAIN.replace("-density 0.5 -pad_left 1 -pad_right 1", "-density 0.3 -pad_left 2 -pad_right 2") in out, out
    out = _run(SPARSE, call=PLAIN, env=env)                       # an already-plain call on a sparse kit is spread
    assert "CALL 1: " + PLAIN.replace("-density 0.5 -pad_left 1 -pad_right 1", "-density 0.3 -pad_left 2 -pad_right 2") in out, out
    out = _run(SPARSE, env="set ::env(OT_GPL_SPARSE_DENSITY) x")
    assert "RC=1" in out and "OT_GPL_SPARSE_DENSITY must be a number" in out, out


# ---- GPL-GROWTH-1126 (HEAD-INT-R2, C-GPL-TD-INFLATION): OT_GPL_GROWTH report line / opt-in gate ----
GROW = "lappend ::insts {PLACED 10 10 0 0 0}; lappend ::insts {PLACED 10 10 0 0 0}; lappend ::insts {PLACED 10 10 0 0 0}"


def _run_grow(env="", insts=DENSE):
    body = MOCK % dict(INSTS=" ".join("{" + " ".join(map(str, i)) + "}" for i in insts), ENV=env, GPL="ok")
    body = body.replace("incr ::calls\n", "incr ::calls\n  " + GROW + "\n", 1)       # the call inserts 3 buffers (DENSE has 2 insts)
    tail = ('\nset rc [catch {global_placement -density 0.5 -timing_driven} res]\nputs "RC=$rc RES=$res"\n')
    out = subprocess.run(["tclsh"], input=body + GUARD + tail, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return out.stdout


@needs_tcl
def test_growth_report_line_default_never_fails():
    out = _run_grow()
    assert "OT_GPL_GROWTH cells 2 -> 5 (+150.0 %)" in out and "limit none" in out and "RC=0 RES=done" in out, out


@needs_tcl
def test_growth_gate_opt_in_fails_above_limit_only():
    out = _run_grow("set ::env(OT_GPL_GROWTH_MAX) 0.3")
    assert "RC=1" in out and "OT_GPL_GROWTH FAIL" in out and "limit 30.0 %" in out, out
    out = _run_grow("set ::env(OT_GPL_GROWTH_MAX) 2.0")
    assert "RC=0 RES=done" in out and "limit 2.0" in out, out
    out = _run_grow('set ::env(OT_GPL_GROWTH_MAX) ""')
    assert "limit none" in out and "RC=0" in out, out
    assert "RC=1" in _run_grow("set ::env(OT_GPL_GROWTH_MAX) abc")


@needs_tcl
def test_growth_wrapper_keeps_the_guard_behaviour():
    out = _run(SPARSE, "diverge_modal")
    assert "OT_GPL_FALLBACK" in out and "RC=0 RES=done CALLS=2" in out and "OT_GPL_GROWTH cells" in out, out
    out = _run(DENSE, "other")
    assert "RC=1 RES=GPL-0301 CALLS=1" in out and "OT_GPL_GROWTH" not in out, out      # a failed call reports nothing


# ---- FIRM-RESIZE-1126 (HEAD-INT-R2, C-FIRM-RESIZE-OVERLAP): at-risk FIRM cells, report + opt-in dont_touch ----
FR_MOCK = r"""
namespace eval ord { proc get_db_block {} { return blk }; proc get_db {} { return db } }
proc db {op} { return [list lib] }
proc lib {op} { return [list M:DFFHQNx1_ASAP7_75t_R M:DFFHQNx2_ASAP7_75t_R M:DFFHQNx3_ASAP7_75t_R M:INVx1_ASAP7_75t_R M:TAPCELL_ASAP7_75t_R] }
array set ::MW {DFFHQNx1_ASAP7_75t_R 20 DFFHQNx2_ASAP7_75t_R 28 DFFHQNx3_ASAP7_75t_R 36 INVx1_ASAP7_75t_R 6 TAPCELL_ASAP7_75t_R 4}
# insts: name master status x0 y0
set ::I {%(INSTS)s}
proc blk {op} { set r {}; foreach x $::I { lappend r "I:[lindex $x 0]" }; return $r }
proc inst_of {c} { foreach x $::I { if {"I:[lindex $x 0]" eq $c} { return $x } } }
proc unknown {cmd args} {
  if {[string match I:* $cmd]} { lassign [inst_of $cmd] n m st x y
    switch [lindex $args 0] { getName { return $n } getPlacementStatus { return $st } getMaster { return "M:$m" } getBBox { return "B:$cmd" }
      setDoNotTouch { puts "DONT_TOUCH $n"; return } } }
  if {[string match M:* $cmd]} { set m [string range $cmd 2 end]
    switch [lindex $args 0] { getName { return $m } getWidth { return $::MW($m) } getHeight { return 10 } isBlock { return 0 } getMasters { return [list] } } }
  if {$cmd eq "lib"} { return }
  if {[string match B:* $cmd]} { lassign [inst_of [string range $cmd 2 end]] n m st x y
    switch [lindex $args 0] { xMin { return $x } yMin { return $y } xMax { return [expr {$x+$::MW($m)}] } yMax { return [expr {$y+10}] } } }
  error "unknown $cmd $args"
}
"""
FR_FUNCS = GUARD[GUARD.index("proc ot_firm_resize_risk"):GUARD.index("# GPL-GROWTH-1126")]


def _fr(insts, env=""):
    body = FR_MOCK % dict(INSTS=" ".join("{" + " ".join(map(str, i)) + "}" for i in insts))
    # lib getMasters: the mock lib returns the master handles
    body = body.replace("proc lib {op} { return", "proc lib {op} { if {$op eq \"getMasters\"} { return [list M:DFFHQNx1_ASAP7_75t_R M:DFFHQNx2_ASAP7_75t_R M:DFFHQNx3_ASAP7_75t_R M:INVx1_ASAP7_75t_R M:TAPCELL_ASAP7_75t_R] }; return")
    body = body.replace("proc db {op} { return [list lib] }", "proc db {op} { return [list lib] }")
    out = subprocess.run(["tclsh"], input=body + env + "\n" + FR_FUNCS + "\not_firm_resize_guard\n", capture_output=True, text=True)
    assert out.returncode == 0, out.stderr + out.stdout
    return out.stdout


FR_ROW = [("a", "DFFHQNx1_ASAP7_75t_R", "FIRM", 0, 0),        # x1 abutting the next FIRM cell: x2 (28) reaches 22 -> at risk
          ("b", "DFFHQNx1_ASAP7_75t_R", "FIRM", 20, 0),       # next is 60 away: safe
          ("c", "DFFHQNx1_ASAP7_75t_R", "FIRM", 80, 0),       # next is a LOCKED tap at 100 (x3 reaches 116): at risk
          ("t", "TAPCELL_ASAP7_75t_R", "LOCKED", 100, 0),
          ("p", "DFFHQNx1_ASAP7_75t_R", "FIRM", 200, 0),      # next is PLACED: DPL legalises it, not at risk
          ("q", "INVx1_ASAP7_75t_R", "PLACED", 205, 0),
          ("r", "DFFHQNx1_ASAP7_75t_R", "FIRM", 0, 10)]


@needs_tcl
def test_firm_resize_risk_reports_growers_and_default_does_not_freeze():
    out = _fr(FR_ROW)
    assert "OT_FIRM_RESIZE_RISK firm_std_cells=5 at_risk=2 freeze=0" in out, out     # r (row 2) has no right neighbour
    assert "OT_FIRM_RESIZE_RISK_CELL a DFFHQNx1" in out and "OT_FIRM_RESIZE_RISK_CELL c DFFHQNx1" in out, out
    assert "DONT_TOUCH" not in out and "b DFF" not in out and "p DFF" not in out, out


@needs_tcl
def test_firm_resize_freeze_is_a_sizing_lock_not_dont_touch(tmp_path):
    # HEAD-INT-R2 11-26: dont_touch on a FIRM cell made repair_design refuse to buffer its nets (RSZ-3006); the lock records masters instead
    out = _fr(FR_ROW, f"set ::env(OT_FIRM_RESIZE_FREEZE) 1; set ::env(RESULTS_DIR) {tmp_path}")
    assert "DONT_TOUCH" not in out and "freeze=1" in out, out
    assert "size lock on 2 FIRM cells" in out and "no dont_touch" in out, out
    rows = sorted((tmp_path / "ot_firm_size_lock.txt").read_text().splitlines())
    assert rows == ["a\tDFFHQNx1_ASAP7_75t_R", "c\tDFFHQNx1_ASAP7_75t_R"], rows
    assert "OT_FIRM_RESIZE_RISK" not in _fr(FR_ROW, "set ::env(OT_FIRM_RESIZE_RISK) 0")


@needs_tcl
def test_firm_resize_default_writes_no_lock_file(tmp_path):
    out = _fr(FR_ROW, f"set ::env(RESULTS_DIR) {tmp_path}")
    assert "freeze=0" in out and not (tmp_path / "ot_firm_size_lock.txt").exists(), out


@needs_tcl
def test_firm_size_lock_keeps_first_master_seen(tmp_path):
    # a second global_placement call in the same process must not overwrite the recorded master with a grown one
    env = f"set ::env(OT_FIRM_RESIZE_FREEZE) 1; set ::env(RESULTS_DIR) {tmp_path}; set ::ot_firm_size_lock [dict create a DFFHQNx1_ASAP7_75t_R]"
    rows = [("a", "DFFHQNx2_ASAP7_75t_R", "FIRM", 0, 0), ("t", "TAPCELL_ASAP7_75t_R", "LOCKED", 10, 0)]
    _fr(rows, env)
    assert (tmp_path / "ot_firm_size_lock.txt").read_text().splitlines() == ["a\tDFFHQNx1_ASAP7_75t_R"]


def test_firm_resize_guard_runs_before_the_call_and_report_errors_do_not_stop_a_kit():
    assert GUARD.index("ot_firm_resize_guard} fr_err") < GUARD.index("::ot_gpl_guarded {*}$args")
    assert "OT_FIRM_RESIZE_RISK ERROR (report skipped)" in GUARD
