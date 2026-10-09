#!/bin/bash
# hbm-indexer die bench: build tb_hfd_idx_die once (Verilator), run the base case and the five mutants in parallel.
# usage: run_bench.sh ROOT VEC OUT [LEG] [T] [FA] [KEYLEG] [LA] [CRED]
set -euo pipefail
ROOT=$1; VEC=$2; OUT=$3; LEG=${4:-24}; T=${5:-1}
FA=${6:-4}; KEYLEG=${7:-0}; LA=${8:-6}; CRED=${9:-64}
mkdir -p "$OUT"
R=$ROOT
SRC="$R/physical/hbm_accel_die_views/index/rtl/hfd_idx_lib.sv $R/physical/hbm_accel_die_views/index/rtl/hfd_idx_score.sv
 $R/physical/hbm_accel_die_views/index/rtl/hfd_idx_sel.sv
 $R/rtl/hbm_accel/index/ot_hbm_accel_index_query.sv $R/rtl/hbm_accel/index/ot_hbm_accel_index_candidate.sv
 $R/rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv $R/rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv $R/rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv
 $R/rtl/hdc/v41x/ot_hdc_v41x_sel.sv $R/rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv $R/rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv
 $R/rtl/hdc/v41x/ot_hdc_v41x_sel_cand.sv $R/rtl/hdc/v41/ot_hdc_actquant.sv $R/rtl/hdc/ot_hdc_delay.sv $R/rtl/hdc/ot_hdc_fastfp.sv
 $R/rtl/hdc/ot_hdc_fpu.sv $R/rtl/hdc/ot_hdc_fp32_mul_pipe.sv $R/rtl/proto/ot_fp32_add_rne_pipe.sv $R/rtl/hdc/ot_hdc_prefix.sv
 $R/rtl/hdc/ot_hdc_fp32_add_lat.sv $R/rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv
 $R/physical/hbm_accel_die_views/index/tb/tb_hfd_idx_die.sv"
( set +e; cd "$OUT" && /usr/bin/time -v verilator --binary --timing -O2 -j 32 --output-split 20000 --output-split-cfuncs 20000 \
    -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKANDNBLK -Wno-MULTIDRIVEN --top-module tb_hfd_idx_die -GLEG=$LEG -GT=$T -GFA=$FA -GKEYLEG=$KEYLEG -GLA=$LA -GCRED=$CRED \
    -Mdir obj $SRC > build.log 2> build.time; echo $? > build.exit )
[ "$(cat $OUT/build.exit)" = 0 ] || { echo BUILD FAILED; tail -30 $OUT/build.log; exit 1; }
for c in base MUT_LANE MUT_GID MUT_KEEP MUT_SVAL MUT_QORD; do
  mkdir -p "$OUT/$c"
  ( set +e; cd "$OUT/$c" && pa=""; [ $c != base ] && pa="+$c"; \
    /usr/bin/time -v ../obj/Vtb_hfd_idx_die +DIR=$VEC +SEED=7 +GAP=3 $pa > sim.log 2> time.log; echo $? > exit ) &
done
wait
echo ALL_DONE
