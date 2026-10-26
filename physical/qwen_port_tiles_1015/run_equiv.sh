#!/bin/bash
# usage: bash physical/qwen_port_tiles_1015/run_equiv.sh <OLD_REV> [cycles]  (from the repo root)
set -e
OLD=${1:?old git rev}; CYC=${2:-3000}; O=${OUT:-/tmp/q15pt_equiv}; mkdir -p $O
[ -f $O/old_word.sv ] || git show $OLD:rtl/qwen_split/qfd_slab_word_half.sv | sed "s/module qfd_slab_word_half/module qfd_slab_word_half_old/" > $O/old_word.sv
[ -f $O/old_result.sv ] || git show $OLD:rtl/qwen_split/qfd_slab_result_half.sv | sed "s/module qfd_slab_result_half/module qfd_slab_result_half_old/" > $O/old_result.sv
awk '/^module ot_qwen_slab_pg_rcopy/,/^endmodule/; /^module ot_qwen_slab_pg_lanes/,/^endmodule/' rtl/physical/ot_qwen_slab_port_group.sv > $O/lanes.sv
SRC="rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_qwen_w12_arith.sv rtl/hdc/ot_qwen_w12_matvec.sv rtl/hdc/ot_qwen_me_spine_h_w12.sv $O/lanes.sv physical/qwen_port_tiles_1015/col_stub_sim.sv rtl/qwen_split/qfd_slab_pair_add.sv rtl/qwen_split/qfd_slab_port_leaf.sv rtl/qwen_split/qfd_slab_word_half.sv rtl/qwen_split/qfd_slab_result_half.sv $O/old_word.sv $O/old_result.sv physical/qwen_port_tiles_1015/tb_halves_equiv.sv"
for M in 0 1 2; do
  verilator --binary -j 8 --top-module tb_halves_equiv -GMUT=$M -GCYC=$CYC -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --Mdir $O/obj$M $SRC > $O/build$M.log 2>&1 || { tail -20 $O/build$M.log; exit 2; }
  $O/obj$M/Vtb_halves_equiv > $O/run$M.log; grep -E "EQUIV|MISMATCH" $O/run$M.log | head -4
done
