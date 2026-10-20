#!/usr/bin/env bash
# S81-SHLK12 s10e: lockstep equivalence bench of ot_s81_ing_stream_n32 against ot_hdc_kv_ingest (QKV 0 / APIPE 10 /
# s10b+c+d).  Usage: run_n32_lockstep.sh OUTDIR "SEEDS" [MUT]   (MUT: BYP GOD WIN KIND FQS CQR -> -DOT_N32_MUT_<MUT>)
# Prints one "PASS LOCKSTEP ..." / "FAIL LOCKSTEP ..." (or a $fatal) line per seed, then LOCKSTEP_GATE PASS / FAIL.
set -u
R=$(cd "$(dirname "$0")/../../../.." && pwd)
O=$1; SEEDS=${2:-"1 2 3"}; M=${3:-}; mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
D=""; [ -n "$M" ] && D="-DOT_N32_MUT_$M"
$V --binary --timing -O2 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-UNOPTFLAT --top-module tb_s81_ing_n32_lockstep \
  -DOT_S81_SH_S10B -DOT_S81_SH_S10C -DOT_S81_SH_S10D $D -Mdir "$O/obj" --build-jobs 8 \
  $R/rtl/hdc/ingest/test/tb_s81_ing_n32_lockstep.sv $R/rtl/hdc/ingest/ot_hdc_kv_ingest.sv $R/rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv \
  $R/rtl/hdc/ingest/ot_s81_ing_stream_n32.sv \
  $R/physical/asap7_memory_macros_v2/ot_sram_1r1w2c_16x257_m1/ot_sram_1r1w2c_16x257_m1.v > "$O/build.log" 2>&1 \
  || { echo "BUILD_FAIL (see $O/build.log)"; echo "LOCKSTEP_GATE FAIL"; exit 2; }
bad=0
for s in $SEEDS; do
  "$O/obj/Vtb_s81_ing_n32_lockstep" +seed=$s +segs=${SEGS:-600} > "$O/run_$s.log" 2>&1
  grep -h -E "LOCKSTEP|%Fatal" "$O/run_$s.log" | head -2
  grep -q "^PASS LOCKSTEP" "$O/run_$s.log" || bad=1
done
[ $bad = 0 ] && echo "LOCKSTEP_GATE PASS" || echo "LOCKSTEP_GATE FAIL"
exit $bad
