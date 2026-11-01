#!/usr/bin/env python3
"""Opt-in ORFS synth hook: keep constant-D flops (yosys opt_dff/wreduce -keepdc) without changing opt_merge.

    python3 -I synth_keepdc.py /OpenROAD-flow-scripts/flow/scripts/synth.tcl     # inside the DISPOSABLE kit container

KV-FN-7 / DIE-KV-60 ctlin (COORD 11-01 09:1x): yosys `synth` takes no -keepdc (and SYNTH_ARGS=-keepdc is a command
syntax error), so a kit that needs the face flops of a constant field kept (KV ctl o_hroot: 48 async-reset flops whose D
the S32 specialisation folds to 0; default opt_dff turns them into a TIELO net shared by 562 loads = face_guard
'shared') cannot get it from a kit variable.  This rewrites the container's synth.tcl (never the image, never a repo
copy) the way tools/die_plan/native_bb.py / orfs_hold_mm.py patch it:
  * `synth -flatten -run :fine ...` -> yosys' documented begin+coarse pass list (yosys synth.cc, -flatten),
  * `synth -top ... -run fine: -noabc ...` -> the documented fine+check pass list (-noabc, the same -extra-map),
  * every `opt` of those lists and of the rest of synth.tcl -> ot_opt: yosys opt's own pass order (opt.cc), with
    -keepdc ONLY on opt_dff; opt_expr / opt_merge keep their default, so identical capture flops still merge as in the
    default flow (KV-FN-7 variant A, -keepdc on every pass, kept +777 FF of unmerged duplicates; variant B +100 FF);
  * wreduce -> wreduce -keepdc.
Measured (KV-FN-7 keepdc_b, ctl A kit 9ba0e452): face_guard shared 149 -> 101 (the 48 constant o_hroot class cleared,
the other 101 identical to default), +100 FF, area 23579 vs 23565 um2, PORT_GATE 6849/6849.
Fail-closed: an unrecognised synth.tcl (either synth call missing) is an error, never a silent default run.
Idempotent: a patched file is left as is.
"""
import re
import sys
from pathlib import Path

MARK = "# OT_SYNTH_KEEPDC"
COARSE_CALL = "synth -flatten -run :fine {*}$synth_full_args"
FINE_CALL = "synth -top $::env(DESIGN_NAME) -run fine: -noabc {*}$synth_full_args"
# yosys synth.cc `begin` + `coarse` with -flatten, no -lut/-booth, share on (synth_full_args carries no -noshare here)
COARSE = """hierarchy -check
  yosys proc
  check
  flatten
  opt_expr
  opt_clean
  check
  ot_opt -nodffe -nosdff
  fsm
  ot_opt
  wreduce -keepdc
  peepopt
  opt_clean
  alumacc
  share
  ot_opt
  memory -nomap
  opt_clean
  log OT_SYNTH_KEEPDC coarse done"""
# yosys synth.cc `fine` + `check` with -noabc; techmap gets the same -extra-map ORFS passes in synth_full_args
FINE = """ot_opt -fast -full
  memory_map
  ot_opt -full
  techmap -map +/techmap.v -map $::env(FLOW_HOME)/platforms/common/lcu_kogge_stone.v
  ot_opt -fast
  hierarchy -check
  stat
  check
  log OT_SYNTH_KEEPDC fine done"""
# yosys opt.cc pass order (fixed 6 iterations instead of "until no change"), -keepdc on opt_dff only
PROC = MARK + r''' (tools/die_plan/synth_keepdc.py): opt with -keepdc on opt_dff only
proc ot_opt {args} {
  set fast [expr {[lsearch $args -fast] >= 0}]
  set full [expr {[lsearch $args -full] >= 0}]
  set purge [expr {[lsearch $args -purge] >= 0 ? "-purge" : ""}]
  set nd {}
  foreach f {-nodffe -nosdff} { if {[lsearch $args $f] >= 0} { lappend nd $f } }
  set ex [expr {$full ? "-mux_undef -mux_bool -undriven -fine" : ""}]
  set rf [expr {$full ? "-full" : ""}]
  if {$fast} {
    for {set i 0} {$i < 6} {incr i} {
      opt_expr {*}$ex; opt_merge; opt_dff {*}$nd -keepdc; opt_clean {*}$purge
    }
  } else {
    opt_expr {*}$ex; opt_merge -nomux
    for {set i 0} {$i < 6} {incr i} {
      opt_muxtree; opt_reduce {*}$rf; opt_merge; if {$full} { opt_share }
      opt_dff {*}$nd -keepdc; opt_clean {*}$purge; opt_expr {*}$ex
    }
  }
  log "OT_OPT_KEEPDC $args"
}
'''


def patch_text(s):
    if MARK in s:
        return s, 0
    extra = "-extra-map $::env(FLOW_HOME)/platforms/common/lcu_kogge_stone.v"
    if s.count(COARSE_CALL) < 1 or s.count(FINE_CALL) != 1 or extra not in s or "set synth_full_args" not in s:
        raise ValueError("unrecognised ORFS synth.tcl (synth calls / extra-map changed); refusing the keepdc hook")
    s = s.replace(COARSE_CALL, COARSE).replace(FINE_CALL, FINE)
    n = 0

    def rep(m):
        nonlocal n
        n += 1
        return m.group(1) + "ot_opt" + m.group(2)
    s = re.sub(r"(?m)^(\s*)opt((?: [^\n]*)?)$", rep, s)     # remaining bare `opt ...` lines (post-dfflibmap opt etc.)
    i = s.index("set synth_full_args")
    return s[:i] + PROC + s[i:], n


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    p = Path(sys.argv[1])
    s, n = patch_text(p.read_text())
    if n or MARK not in p.read_text():
        p.write_text(s)
    print(f"OT_SYNTH_KEEPDC patched {p} (other opt -> ot_opt x{n})")


if __name__ == "__main__":
    main()
