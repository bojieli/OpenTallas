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
# h1-audit 2026-10-08: the receiver-side hold term in the other block families (S81 BF / root_phase / hbglue / PQ,
# DS-ROM head ioreg / fh_quad / swiglu ireg, HBM attn_tile_r vclk, Qwen embedding parent).  Same rule, same idempotence.
AUDIT = [
    ("physical/s81_native_bf/margin/signoff_ref.sdc", "set_input_delay -min [expr {$bf_lmin - 50}]", "set_input_delay -min $bf_lmin"),
    ("physical/s81_bf_root_phase/signoff_ref.sdc", "set_input_delay -min [expr {$bf_lmin - 50}]", "set_input_delay -min $bf_lmin"),
    ("tools/s81/run_bf_native_physical.py", "'--core-input-delay-min-ns',io(ff-50)", "'--core-input-delay-min-ns',io(ff)"),
    ("tools/s81/run_bf_root_phase_physical.py", "'--core-input-delay-min-ns',io(ff-50)", "'--core-input-delay-min-ns',io(ff)"),
    ("physical/s81_die_views/hbglue/margin/route_cl.sh", 'IMIN=$(io "$FF-50")', 'IMIN=$(io "$FF")'),
    ("physical/s81_die_views/hbglue/margin/route_cl.sh", "print(round($FF-50))", "print(round($FF))"),
    ("physical/dsrom_fh_quad/route.sh", 'IMIN=$(echo "($IFF-50)/1000" | bc -l)', 'IMIN=$(echo "($IFF-${IN_HOLD_SKEW:-0})/1000" | bc -l)'),
    ("physical/dsrom_fh_quad/route.sh", 'set_input_delay -min $(echo "$IFF-50" | bc)', 'set_input_delay -min $(echo "$IFF-${IN_HOLD_SKEW:-0}" | bc)'),
    ("physical/dsrom_head_elem_ioreg/route.sh", 'IMIN=$(echo "($IFF-50)/1000" | bc -l)', 'IMIN=$(echo "($IFF-${IN_HOLD_SKEW:-0})/1000" | bc -l)'),
    ("physical/dsrom_head_elem_ioreg/route.sh", 'set_input_delay -min $(echo "$IFF-50" | bc)', 'set_input_delay -min $(echo "$IFF-${IN_HOLD_SKEW:-0}" | bc)'),
    ("physical/qwen_embedding_parent/io_ref_macro.sdc", "set_input_delay [expr {$lmin - 50}] -min", "set_input_delay $lmin -min"),
    ("physical/s81_pq_r128_expanded/signoff_r128.sdc", "set_input_delay  -50 -min", "set_input_delay  0 -min"),
    ("physical/s81_pq_return_delay/signoff.sdc", "set_input_delay  -50 -min", "set_input_delay  0 -min"),
    ("physical/s81_pq_r128_expanded/io_ref_post.tcl", "set_input_delay  -50 -min", "set_input_delay  0 -min"),
    ("physical/s81_pq_r128_expanded/io_ref_pre.tcl", "set_input_delay  -50 -min", "set_input_delay  0 -min"),
    ("physical/s81_pq_r128_expanded/io_budget_r128.sdc", "set_input_delay  -50 -min", "set_input_delay  0 -min"),
    ("physical/dsrom_su_swiglu_ireg/die_io_833_ff.sdc", "set_input_delay -min -50.0", "set_input_delay -min 0.0"),
    ("physical/dsrom_su_swiglu_ireg/die_io_833_ss.sdc", "set_input_delay -min -50.0", "set_input_delay -min 0.0"),
    ("physical/hbm_attn_tile_r/io_vclk.sdc", "set_input_delay -min -150", "set_input_delay -min 0"),
    ("physical/hbm_attn_tile_r/signoff_833.sdc", "set_input_delay -min -150", "set_input_delay -min 0"),
    # h1-reroute 2026-10-08: the five Qwen files edefa5bcb fixed in-tree but this patch did not carry (an old snapshot kept
    # the receiver -ot_hk), and the attn_tile_r quad-parent io_ref.sdc (input min DIN-150 -> DIN; output min sign fix).
    ("physical/qwen_stream4_cdc/io_skew.sdc", "set_input_delay  [expr {$lmin - $ot_hk}]", "set_input_delay  [expr {$lmin - IHK}]"),
    ("physical/qwen_core_ctx/io_ref_skew.sdc", "set_input_delay [expr 0 + $qcc_lmin - $ot_hk]", "set_input_delay [expr {0 + $qcc_lmin - IHK}]"),
    ("physical/qwen_slab_structural/io_lat_skew.sdc", "set_input_delay  [expr {$qss_amin - $ot_hk}]", "set_input_delay  [expr {$qss_amin - IHK}]"),
    ("physical/qwen_slab_structural/io_wc_skew.sdc", "set_input_delay  [expr {$qss_early - $qss_hx - $ot_hk}]", "set_input_delay  [expr {$qss_early - $qss_hx - IHK}]"),
    ("physical/qwen_slab_structural/io_refpin_skew_m3.sdc", "set_input_delay  [expr {-$ot_hk}]", "set_input_delay  [expr {-IHK}]"),
    ("physical/hbm_attn_tile_r/io_ref.sdc", "set_input_delay -min [expr {$ot_din - 150}]", "set_input_delay -min $ot_din"),
    ("physical/hbm_attn_tile_r/io_ref.sdc", "set_output_delay -min [expr {-($ot_qins - 150)}]", "set_output_delay -min [expr {-($ot_qins + 150)}]"),
]
IHK = "([info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0)"
AUDIT = [(f, a, b.replace("IHK", IHK)) for f, a, b in AUDIT]
for f, a, b in AUDIT:
    q = R / f
    if q.is_file():
        s = q.read_text()
        if a in s:
            q.write_text(s.replace(a, b)); n += 1
print(f"h1_patch: {n} files rewritten under {R}")
