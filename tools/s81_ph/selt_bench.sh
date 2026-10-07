#!/bin/bash
# CLAUDE S81-PH tiled selector bench (redesign pass 2026-10-06): tb_s81ph_sel (every IDX beat, count, replays and fault
# bits vs the native ot_hdc_v41x_sel; 8 directed + 24 random segments + 3 fail-closed cases) on dsfd_bk_selector
# TILED 1 (ot_s81ph_sel_t: 4 x dsfd_selt_q + dsfd_selt_c).  usage (from the source root):
#   tools/s81_ph/selt_bench.sh <out> <tag> [defines...]     verdict line "SELT_BENCH PASS|FAIL"
set -u
OUT=$1; TAG=$2; shift 2
d=''; for x in "$@"; do d="$d +define+$x"; done
mkdir -p $OUT/b_$TAG
timeout 7200 verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style --top-module tb_s81ph_sel $d -Mdir $OUT/b_$TAG/obj \
  rtl/common/ot_fwd_link_stage.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v \
  rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv rtl/hdc/v41x/ot_hdc_v41x_sel.sv \
  rtl/dsrom_sys/s81_ph/ot_s81ph_sel.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_tile.sv rtl/dsrom_sys/s81_ph/dsfd_bk_selector.sv \
  rtl/dsrom_sys/s81_ph/test/tb_s81ph_sel.sv > $OUT/b_$TAG/build.log 2>&1 || { echo "SELT_BENCH FAIL build"; exit 1; }
timeout 3000 $OUT/b_$TAG/obj/Vtb_s81ph_sel > $OUT/b_$TAG/run.log 2>&1
r=$(grep -h '^RESULT' $OUT/b_$TAG/run.log | tail -1)
echo "$TAG: ${r:-NO RESULT (timeout/hang)}" | tee $OUT/b_$TAG/summary.txt
echo "$r" | grep -q 'RESULT PASS' && { echo "SELT_BENCH PASS" | tee -a $OUT/b_$TAG/summary.txt; exit 0; }
echo "SELT_BENCH FAIL" | tee -a $OUT/b_$TAG/summary.txt; exit 1
