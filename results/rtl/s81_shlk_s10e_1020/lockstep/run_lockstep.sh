#!/bin/bash
# usage: run_lockstep.sh OUTDIR "seeds" [extra verilator defines]
set -u
OUT=$1; SEEDS=$2; shift 2; EXTRA="$*"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
SRC=$(cd "$(dirname "$0")/.." && pwd)/src
mkdir -p $OUT && cd $OUT
$V --version > verilator_version.txt
$V --binary --timing -O2 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-UNOPTFLAT --top-module tb_s81_ing_n32_lockstep \
  -DOT_S81_SH_S10B -DOT_S81_SH_S10C -DOT_S81_SH_S10D $EXTRA -Mdir obj --build-jobs 8 \
  $SRC/rtl/hdc/ingest/test/tb_s81_ing_n32_lockstep.sv $SRC/rtl/hdc/ingest/ot_hdc_kv_ingest.sv $SRC/rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv \
  $SRC/rtl/hdc/ingest/ot_s81_ing_stream_n32.sv \
  $SRC/physical/asap7_memory_macros_v2/ot_sram_1r1w2c_16x257_m1/ot_sram_1r1w2c_16x257_m1.v > build.log 2>&1 || { echo BUILD_FAIL; tail -30 build.log; exit 2; }
for s in $SEEDS; do obj/Vtb_s81_ing_n32_lockstep +seed=$s +segs=${SEGS:-300} > run_$s.log 2>&1; tail -2 run_$s.log; done
