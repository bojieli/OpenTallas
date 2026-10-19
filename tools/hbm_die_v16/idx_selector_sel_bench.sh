#!/bin/bash
# L2H-GEN2E 10-19: Verilator 5.050 benches of ot_hbm_idx_selector_static_sel (die SELECTED-ONLY IDX selector).
#   idx_selector_sel_bench.sh link SMUT  : canonical full-shape gold bench (tools/hbm_idx_static_selector_vectors.py, 3 frames,
#                                          selector core -> topk link, every selected record vs gold) with the _sel core.
#   idx_selector_sel_bench.sh eq SMUT    : _sel vs canonical shell, every cycle selected_v/selected_line/fault; op 8 -> sticky fault.
# Run from the source root.  SMUT 0 must PASS both; SMUT 1 (threshold mutant) must FAIL link; SMUT 3 (op 8 not faulted) must FAIL eq.
set -o pipefail
MODE=${1:-link}; M=${2:-0}; V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version
if [ "$MODE" = link ]; then
  O=$PWD/obj_sel_link_m$M; rm -rf $O; mkdir -p $O
  python3 tools/hbm_idx_static_selector_vectors.py $O/vec > $O.vec.log 2>&1 || { tail $O.vec.log; echo VEC_FAIL; exit 2; }
  SRCS="rtl/hbm_accel/index/ot_hbm_idx_selector_static_sel.sv rtl/hbm_accel/index/ot_hbm_idx_topk_link_static.sv
  rtl/test/hbm_idx_static/tb_selector_sel_link_static.sv physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
  physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
  $V --binary -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_selector_sel_link_static -GSMUT=$M -Mdir $O/obj $SRCS > $O.build.log 2>&1 || { tail -30 $O.build.log; echo BUILD_FAIL; exit 2; }
  cd $O/vec && $O/obj/Vtb_selector_sel_link_static
else
  O=obj_sel_eq_m$M; rm -rf $O
  SRCS="physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
  rtl/hbm_accel/index/ot_hbm_idx_selector_static.sv rtl/hbm_accel/index/ot_hbm_idx_selector_static_sel.sv
  rtl/hbm_accel/index/tb/tb_hbm_idx_selector_sel_eq.sv"
  $V --binary -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_hbm_idx_selector_sel_eq -GSMUT=$M -Mdir $O $SRCS > $O.build.log 2>&1 || { tail -30 $O.build.log; echo BUILD_FAIL; exit 2; }
  ./$O/Vtb_hbm_idx_selector_sel_eq | grep -v -E '^PRE t='
fi
