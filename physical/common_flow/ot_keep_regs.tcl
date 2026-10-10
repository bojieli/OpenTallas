# FLOW-FIX-0410 2026-10-09: replicated registers survive synthesis.  ORFS SYNTH_CANONICALIZE_TCL hook (sourced by
# scripts/synth_canonicalize.tcl right after `hierarchy -check -top`, before the canonical RTLIL is written).
#
# A register declared (* keep *) / (* keep = 1 *) / (* keep = "true" *) puts the attribute on the WIRE only.  The flip-flop
# cell that drives it carries no keep, so the opt_merge inside `synth` folds identical copies into one flop and the kept
# wires all hang off it: the "replicated fanout" a block was designed with is a single high-fanout flop again.
# Measured with the ORFS yosys 0.68 (`make synth`): ot_sc_pfifo with plain keep copies 22 -> 9 control flops (16 copies
# -> 4); a kept array reg [3:0] cp[0:3] + c2[0:1][0:1] 32 -> 6 flops; ot_gpu_router_topk_f v_r/vf_r/f_r (16 identical bits
# each) 1 flop each.  With this hook: 16/16 copies, 32/32, 16/16 per vector (+45 flops).
#
# Fix: elaborate processes (`proc`; synth runs it again as a no-op) and set keep on every flip-flop / latch cell that
# drives a keep wire.  opt_merge / opt_dff leave keep cells alone, so every declared copy stays a flop.  Function is
# unchanged (identical copies of the same register); only the folding is undone.  keep_hierarchy leaf modules
# (ot_sc_rep_ff, ot_qwen_lrst_ff, ...) were the RTL-side workaround and remain valid.  Opt out: OT_KEEP_REGS=0 in the
# route environment (run_abi3_physical.py / hbm_accel_smh_physical.py then omit SYNTH_CANONICALIZE_TCL).
yosys proc
yosys select -set ot_kw {*}{w:* a:keep %i}
yosys select -set ot_kc {*}{@ot_kw %ci1 t:$*dff* t:$*dlatch* %u %i}
# a vector register is ONE multi-bit cell; techmap later splits it into per-bit cells WITHOUT the keep attribute and the
# fine opt_merge folds identical bits (ot_gpu_router_topk_f: v_r <= {P{in_valid}} 16 bits -> 1 flop even with keep on
# the vector cell).  Map the kept cells to per-bit gate-level flip-flops first (techmap of the selection only; splitcells
# is not enough: it splits by output use, and a vector used whole stays one cell), then mark every bit cell.
yosys techmap {*}{@ot_kc}
yosys select -set ot_kc {*}{@ot_kw %ci1 t:$*dff* t:$*dlatch* t:$_*DFF* t:$_*LATCH* %u %u %u %i}
yosys setattr -set keep 1 {*}{@ot_kc}
set ot_kr_n [llength [split [string trim [yosys tee -q -s result.string select -list {*}{@ot_kc}]] "\n"]]
puts "OT_KEEP_REGS: keep set on $ot_kr_n register cells driving keep wires"
yosys select -clear
