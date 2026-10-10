#!/bin/bash
# hgi-takeover: IDX.INDEX record -> ot_hgi_idx_unit / ot_hgi_idx_index -> hfd_idx_sel + 4 hfd_idx_score (tb_hgi_idx_index),
# vectors from tools/hbm_idx_die_bench.py prepare; base + mutants MUT=2 (head weight of the next head), MUT=3 (R lane).
# usage: run_index_bench.sh ROOT VEC OUT     -> OUT/<case>/verdict.json (compare), OUT/SUMMARY
set -uo pipefail
R=$1; VEC=$2; OUT=$3; mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
I=$R/physical/hbm_accel_die_views/index
SRC="$I/rtl/hfd_idx_lib.sv $I/rtl/hfd_idx_score.sv $I/rtl/hfd_idx_sel.sv
 $R/rtl/hbm_accel/index/ot_hbm_accel_index_query.sv $R/rtl/hbm_accel/index/ot_hbm_accel_index_candidate.sv
 $R/rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv $R/rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv $R/rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv
 $R/rtl/hdc/v41x/ot_hdc_v41x_sel.sv $R/rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv $R/rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv
 $R/rtl/hdc/v41x/ot_hdc_v41x_sel_cand.sv $R/rtl/hdc/v41/ot_hdc_actquant.sv $R/rtl/hdc/ot_hdc_delay.sv $R/rtl/hdc/ot_hdc_fastfp.sv
 $R/rtl/hdc/ot_hdc_fpu.sv $R/rtl/hdc/ot_hdc_fp32_mul_pipe.sv $R/rtl/proto/ot_fp32_add_rne_pipe.sv $R/rtl/hdc/ot_hdc_prefix.sv
 $R/rtl/hdc/ot_hdc_fp32_add_lat.sv $R/rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv
 $R/rtl/hbm_accel/generic_20261009/ot_hgi_idx_topk.sv $R/rtl/hbm_accel/generic_20261009/ot_hgi_idx_topk_registered.sv
 $R/rtl/hbm_accel/generic/idx/ot_hgi_idx_merge.sv $R/rtl/hbm_accel/generic/idx/ot_hgi_idx_index.sv $R/rtl/hbm_accel/generic/idx/ot_hgi_idx_unit.sv
 $R/rtl/hbm_accel/generic/idx/tb_hgi_idx_index.sv"
for m in 0 2 3; do
  ( mkdir -p $OUT/b$m && cd $OUT/b$m && $V --binary --timing -O2 -j 8 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKANDNBLK \
      -Wno-MULTIDRIVEN --top-module tb_hgi_idx_index -GMUT=$m -Mdir obj $SRC > build.log 2>&1; echo $? > build.exit )
done
for m in 0 2 3; do
  ( cd $OUT/b$m && [ "$(cat build.exit)" = 0 ] && stdbuf -oL ./obj/Vtb_hgi_idx_index +DIR=$VEC +ODIR=. +SEED=7 +GAP=3 > sim.log 2>&1;
    cd $R && python3 tools/hbm_idx_die_bench.py compare --work $VEC --run $OUT/b$m > $OUT/b$m/compare.log 2>&1;
    echo "MUT=$m $(grep -o '"verdict": "[A-Z]*"' $OUT/b$m/verdict.json 2>/dev/null) $(grep HGIIDX_FRAME $OUT/b$m/sim.log | tr '\n' ' ')" > $OUT/b$m/line ) &
done
wait
cat $OUT/b*/line > $OUT/SUMMARY
