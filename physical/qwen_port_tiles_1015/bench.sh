#!/bin/bash
# q15 port-tiles closure benches (run from the repo root).  usage: bench.sh <equiv|reg512> <outdir> <MUT>
#   equiv : (args 4/5 = BAND HALF strap, default 1 1) old inline word/result halves (reference/, frozen from main 194bc6a03) vs the new leaf hierarchy, 3000 edges
#           -> prints "EQUIV MUT=<m> ... PASS|FAIL" (MUT 0 must PASS; 1 pair order, 2 pt_id strap must FAIL)
#   reg512: qfd_slab_reg512 one-edge bank -> "REG512 MUT=<m> ... PASS|FAIL" (1 bypass, 2 bit-0 inversion must FAIL)
set -e
K=${1:?}; O=${2:?}; M=${3:-0}; BP=${4:-1}; HP=${5:-1}; mkdir -p $O
if [ $K = reg512 ]; then
  iverilog -g2012 -P tb_reg512.MUT=$M -o $O/r.vvp rtl/qwen_split/qfd_slab_reg512.sv physical/qwen_port_tiles_1015/tb_reg512.sv
  vvp -n $O/r.vvp | grep REG512 | tee $O/verdict.txt; grep -q " PASS$" $O/verdict.txt
  exit 0
fi
awk '/^module ot_qwen_slab_pg_rcopy/,/^endmodule/; /^module ot_qwen_slab_pg_lanes/,/^endmodule/' rtl/physical/ot_qwen_slab_port_group.sv > $O/lanes.sv
SRC="rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_qwen_w12_arith.sv rtl/hdc/ot_qwen_w12_matvec.sv rtl/hdc/ot_qwen_me_spine_h_w12.sv $O/lanes.sv physical/qwen_port_tiles_1015/col_stub_sim.sv rtl/qwen_split/qfd_slab_pair_add.sv rtl/qwen_split/qfd_slab_port_leaf.sv rtl/qwen_split/qfd_slab_word_half.sv rtl/qwen_split/qfd_slab_result_half.sv physical/qwen_port_tiles_1015/reference/qfd_slab_word_half_old.sv physical/qwen_port_tiles_1015/reference/qfd_slab_result_half_old.sv physical/qwen_port_tiles_1015/tb_halves_equiv.sv"
verilator --binary -j 4 --top-module tb_halves_equiv -GMUT=$M -GCYC=3000 -GBANDP=$BP -GHALFP=$HP -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --Mdir $O/obj $SRC > $O/build.log 2>&1 || { tail -20 $O/build.log; exit 2; }
$O/obj/Vtb_halves_equiv > $O/run.log; grep -E "EQUIV|MISMATCH" $O/run.log | head -4
grep -q "^EQUIV .* PASS$" $O/run.log
