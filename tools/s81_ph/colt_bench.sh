#!/bin/bash
# CLAUDE S81-PH tiled collector bench (redesign pass 2026-10-06): tb_s81ph_col (transaction scoreboard: frames bit-exact,
# whole, per-stack order, DONE after a job's frames, pace >= 2; fault modes fail closed) on dsfd_bk_collector TILED 1
# (ot_s81ph_col_t: 4 x dsfd_colt_lane + dsfd_colt_mrg, HOPS stations).
# usage (from the source root): tools/s81_ph/colt_bench.sh <out> <tag> "<runs>" [defines...]
#   runs: gold<seed> | fault<mode>; verdict line "COLT_BENCH PASS|FAIL" (exit 0 = all RESULT PASS)
set -u
OUT=$1; TAG=$2; RUNS=$3; shift 3
d=''; for x in "$@"; do d="$d +define+$x"; done
mkdir -p $OUT
timeout 3600 verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_s81ph_col $d -Mdir $OUT/obj_$TAG \
  rtl/common/ot_fwd_link_stage.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v \
  rtl/link/ot_fifo_sram_fwft.sv rtl/dsrom_sys/s81_ph/ot_s81ph_col.sv rtl/dsrom_sys/s81_ph/ot_s81ph_col_tile.sv \
  rtl/dsrom_sys/s81_ph/dsfd_bk_collector.sv rtl/dsrom_sys/s81_ph/test/tb_s81ph_col.sv > $OUT/build_$TAG.log 2>&1 \
  || { echo "COLT_BENCH FAIL build"; exit 1; }
for r in $RUNS; do
  case $r in gold*) pa="+seed=${r#gold}";; fault*) pa="+mode=${r#fault}";; esac
  timeout 3600 $OUT/obj_$TAG/Vtb_s81ph_col $pa > $OUT/run_${TAG}_$r.log 2>&1 &
done
wait
for r in $RUNS; do echo "$TAG $r: $(grep -h '^RESULT' $OUT/run_${TAG}_$r.log | tail -1)"; done > $OUT/summary_$TAG.txt
cat $OUT/summary_$TAG.txt
if grep -v 'RESULT PASS' $OUT/summary_$TAG.txt | grep -q .; then echo "COLT_BENCH FAIL" | tee -a $OUT/summary_$TAG.txt; exit 1; fi
echo "COLT_BENCH PASS" | tee -a $OUT/summary_$TAG.txt
