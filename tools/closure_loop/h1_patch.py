#!/usr/bin/env python3
"""FLOW-HOLD rule H1 for an OLD source snapshot (closure-loop requeue of a job pinned before claude/flow-hold-20261007):
the die-link hold term is carried once, by the sender's output min delay, so the receiver's input min loses its -50 ps.
Rewrites, in place, the Qwen die-master boundary SDCs (io_ref_skew.sdc, signoff/*.sdc) and dsrom_fh_safe/cl_route.sh,
exactly as commits 8ea9147d5 / 65c1e043e did on the branch.  Idempotent.   h1_patch.py <snapshot root> [extra generated FF SDC files, e.g. {run}/cl/budget_ff.sdc]"""
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
    # h1-verify 2026-10-08: the five families edefa5bcb left "probably single-count".  The corner-true FF recipe
    # (vclk_corner_true / make_io_vclk_ff / make_block_sdc ff / stn_margin / window columns / pq_root_cam) timed outputs at
    # the EARLIEST capture (FF min leaf) and inputs at the LATEST launch (FF max leaf) with the 50 ps on both: sign error on
    # both ends + double count.  Now: outputs vs the FF max + 50 (sender), inputs launch at the FF mean, 25 (receiver).
    ("physical/hbm_accel_die_views/common/vclk_corner_true.sdc", "    set_clock_latency $ot_lo [get_clocks vclk]\n", "    set_clock_latency $ot_hi [get_clocks vclk]\n"),
    ("physical/hbm_accel_die_views/common/vclk_corner_true.sdc", "set_input_delay -min [expr {$ot_hi - $ot_lo}] -clock vclk", "set_input_delay -min [expr {($ot_lo + $ot_hi) / 2.0 - $ot_hi}] -clock vclk"),
    ("physical/hbm_accel_die_views/common/vclk_corner_true.sdc", "set_clock_uncertainty -hold 50 -from [get_clocks vclk] -to [get_clocks core_clk]", "set_clock_uncertainty -hold 25 -from [get_clocks vclk] -to [get_clocks core_clk]"),
    ("physical/hbm_accel_die_views/common/spine_io_min.py", "set_input_delay -min [expr {{$ot_hi - $ot_lo + ", "set_input_delay -min [expr {{($ot_lo + $ot_hi) / 2.0 - $ot_hi + "),
    ("physical/hbm_accel_die_views/common/make_io_vclk_ff.sh", "set_clock_latency $LMIN [get_clocks vclk]", "set_clock_latency $LMAX [get_clocks vclk]"),
    ("physical/hbm_accel_die_views/common/make_io_vclk_ff.sh", "set_clock_latency $LMAX [get_clocks vclki]", "set_clock_latency $(echo \"($LMIN + $LMAX) / 2\" | bc -l | sed 's/0*$//;s/\\.$//') [get_clocks vclki]"),
    ("physical/hbm_accel_die_views/common/make_io_vclk_ff.sh", "set_clock_uncertainty -hold 50 -from [get_clocks vclki] -to [get_clocks $C]", "set_clock_uncertainty -hold 25 -from [get_clocks vclki] -to [get_clocks $C]"),
    ("physical/hbm_accel_die_views/stations/bench/stn_margin_sdc.py", "mn = (Lmax - L - 25) if m.group(1) == 'set_input_delay' else (L - Lmin - 25)", "mn = ((Lmin + Lmax) / 2 - L) if m.group(1) == 'set_input_delay' else (L - Lmax - 25)"),
    ("tools/budgets/make_block_sdc.py", "f'set_clock_latency {lmin:g} [get_clocks vclk]',", "f'set_clock_latency {lmax:g} [get_clocks vclk]',"),
    ("tools/budgets/make_block_sdc.py", "f'set_clock_latency {lmax:g} [get_clocks vclki]']", "f'set_clock_latency {ins[\"ff\"]:g} [get_clocks vclki]']"),
    ("tools/budgets/make_block_sdc.py", "out += [f'set_clock_uncertainty -hold {h:g} -from [get_clocks vclki]", "out += [f'set_clock_uncertainty -hold {sh[\"skew\"].get(\"hold_uncertainty_ps\", 25):g} -from [get_clocks vclki]"),
    ("tools/hbm_accel_smh_physical.py", '"set_input_delay -min [expr 833 * 0.2 - $hold_io] -clock nbr_clk $elem_in"', '"set_input_delay -min [expr 833 * 0.2] -clock nbr_clk $elem_in"'),
    ("tools/hbm_accel_smh_physical.py", '"set_input_delay -min [expr 30 - $hold_io] -clock core_clk -reference_pin $refpin $nbr_in"', '"set_input_delay -min 30 -clock core_clk -reference_pin $refpin $nbr_in"'),
    ("tools/hbm_accel_smh_physical.py", '"set_input_delay -min [expr 30 - $hold_io] -clock nbr_clk $nbr_in"', '"set_input_delay -min 30 -clock nbr_clk $nbr_in"'),
    ("physical/dsrom_su_softmax_r5/io_budget.tcl", "set_input_delay -min [expr $L - $S + 50] -clock core_clk $ins", "set_input_delay -min [expr $L + 20] -clock core_clk $ins"),
    ("physical/dsrom_su_softmax_r5/boundary_io.sdc", "set_input_delay -min -30 -clock io_clk $ins", "set_input_delay -min 20 -clock io_clk $ins"),
    ("physical/dsrom_su_softmax_r5/boundary_io_vclk.sdc", "set_input_delay -min [expr {-30 - ($ot_lss - $ot_lff)}]", "set_input_delay -min [expr {20 - ($ot_lss - $ot_lff)}]"),
]
for f in ("physical/dsrom_window_columns/m6/route_col.sh", "physical/dsrom_window_columns/halfwrite/route.sh",
          "physical/dsrom_window_columns/halfwrite_distributed/route.sh", "physical/s81_pq_root_cam/route.sh"):
    AUDIT += [
        (f, "FMAX=${CK_FF_MAX:-170}\n", 'FMAX=${CK_FF_MAX:-170}; FMID=${CK_FF_MEAN:-$(awk "BEGIN{print ($FMIN+$FMAX)/2}")}\n'),
        (f, "FMAX=${CK_FF_MAX:-0}\n", 'FMAX=${CK_FF_MAX:-0}; FMID=${CK_FF_MEAN:-$(awk "BEGIN{print ($FMIN+$FMAX)/2}")}\n'),
        (f, "set_input_delay -min [expr {$FMAX - $L - 25}] -clock vclk", "set_input_delay -min [expr {$FMID - $L}] -clock vclk"),
        (f, "set_output_delay -min [expr {$FMIN - $L + 25}] -clock vclk", "set_output_delay -min [expr {$L - $FMAX - 25}] -clock vclk"),
        (f, "set_input_delay -min [expr {$FMAX - $L + 32.2 - 50}] -clock vclk", "set_input_delay -min [expr {$FMID - $L + 32.2}] -clock vclk"),
        (f, "set_output_delay -min [expr {$L - $FMIN - 10}] -clock vclk", "set_output_delay -min [expr {$L - $FMAX - 10}] -clock vclk"),
        (f, "set_clock_latency $FMIN [get_clocks vclk]", "set_clock_latency $FMAX [get_clocks vclk]"),
        (f, "set_clock_latency $FMAX [get_clocks vclki]", "set_clock_latency $FMID [get_clocks vclki]"),
        (f, "set_clock_uncertainty -hold 50 -from [get_clocks vclki] -to [get_clocks core_clk]", "set_clock_uncertainty -hold 25 -from [get_clocks vclki] -to [get_clocks core_clk]"),
    ]
IHK = "([info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0)"
AUDIT = [(f, a, b.replace("IHK", IHK)) for f, a, b in AUDIT]
# H1_SDC_ONLY=1 (live snapshots, h1-verify): never rewrite a script a running stage may be executing (bash reads its script
# incrementally); only the timing-constraint files the remaining stages read.
import os
if os.environ.get("H1_SDC_ONLY") == "1":
    AUDIT = [x for x in AUDIT if x[0].endswith((".sdc", ".tcl"))]
for f, a, b in AUDIT:
    q = R / f
    if q.is_file():
        s = q.read_text()
        if a in s:
            q.write_text(s.replace(a, b)); n += 1
# h1-verify: GENERATED corner-true FF files (make_io_vclk_ff.sh / make_block_sdc.py ff / route-script signoff_ff_guarded
# outputs, budget_ff*.sdc) in the snapshot, plus any extra files named on the command line ({run}/cl/budget_ff.sdc):
# vclk A / vclki B / vclki->clk hold 50  ->  vclk B (latest capture) / vclki (A+B)/2 / vclki->clk hold 25.
import re
VCK = re.compile(r"^set_clock_latency ([0-9.]+) \[get_clocks vclk\]$", re.M)
VCKI = re.compile(r"^set_clock_latency ([0-9.]+) \[get_clocks vclki\]$", re.M)
VH = re.compile(r"^set_clock_uncertainty -hold 50 -from \[get_clocks vclki\] -to (\[get_clocks [^\]]+\])$", re.M)


def gen_ff(q):
    s = q.read_text()
    a, b = VCK.findall(s), VCKI.findall(s)
    if not VH.search(s) or len(a) != 1 or len(b) != 1:
        return 0
    lo, hi = float(a[0]), float(b[0])
    t = VCK.sub(f"set_clock_latency {hi:g} [get_clocks vclk]", s)
    t = VCKI.sub(f"set_clock_latency {(lo + hi) / 2:g} [get_clocks vclki]", t)
    t = VH.sub(r"set_clock_uncertainty -hold 25 -from [get_clocks vclki] -to \1", t)
    q.write_text("# RULE H1 (h1_patch): outputs vs the latest FF leaf + 50, inputs launch at the mean FF leaf, 25\n" + t)
    return 1


for f in list(glob.glob(str(R / "physical/**/*.sdc"), recursive=True)) + sys.argv[2:]:
    q = Path(f)
    if q.is_file() and "vclki" in q.read_text():
        n += gen_ff(q)
for f in glob.glob(str(R / "physical/hbm_accel_die_views/common/io_min/io_min_*.sdc")):
    q = Path(f); s = q.read_text()
    t = s.replace("[expr {$ot_hi - $ot_lo + ", "[expr {($ot_lo + $ot_hi) / 2.0 - $ot_hi + ")
    if t != s:
        q.write_text(t); n += 1
print(f"h1_patch: {n} files rewritten under {R}")
