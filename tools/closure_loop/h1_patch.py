#!/usr/bin/env python3
"""FLOW-HOLD rule H1 for an OLD source snapshot (closure-loop requeue of a job pinned before claude/flow-hold-20261007):
the die-link hold term is carried once, by the sender's output min delay, so the receiver's input min loses its -50 ps.
Rewrites, in place, the Qwen die-master boundary SDCs (io_ref_skew.sdc, signoff/*.sdc) and dsrom_fh_safe/cl_route.sh,
exactly as commits 8ea9147d5 / 65c1e043e did on the branch.  Idempotent.   h1_patch.py <snapshot root>"""
import glob
import sys
from pathlib import Path

R = Path(sys.argv[1])
n = 0
QOLD = "set_input_delay [expr $qdm_lmin - $ot_hk] -min -clock core_clk [all_inputs -no_clocks]"
QNEW = ("set ot_hki [expr {[info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0}]\n"
        "set_input_delay [expr $qdm_lmin - $ot_hki] -min -clock core_clk [all_inputs -no_clocks]")
HOLD = "set_input_delay  [expr {$lmin - $ot_hk}]"
HNEW = "set_input_delay  [expr {$lmin - ([info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0)}]"
for f in glob.glob(str(R / "physical/qwen_die_masters/**/*.sdc"), recursive=True):
    p = Path(f); s = p.read_text()
    t = s.replace(QOLD, QNEW).replace(HOLD, HNEW)
    if t != s:
        p.write_text(t); n += 1
c = R / "physical/dsrom_fh_safe/cl_route.sh"
if c.is_file():
    s = c.read_text()
    t = (s.replace('IMIN=$(echo "($IFF-50)/1000" | bc -l)', 'IMIN=$(echo "($IFF-${IN_HOLD_SKEW:-0})/1000" | bc -l)')
          .replace('IMIN=$(echo "($ISS-50)/1000" | bc -l)', 'IMIN=$(echo "($ISS-${IN_HOLD_SKEW:-0})/1000" | bc -l)')
          .replace('set_input_delay -min $(echo "$IFF-50" | bc)', 'set_input_delay -min $(echo "$IFF-${IN_HOLD_SKEW:-0}" | bc)'))
    if t != s:
        c.write_text(t); n += 1
print(f"h1_patch: {n} files rewritten under {R}")
