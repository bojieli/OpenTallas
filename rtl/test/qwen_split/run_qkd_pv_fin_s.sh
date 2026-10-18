#!/bin/bash
# KV-PLAN-FIN 2026-10-17: qkd_pv_fin_s lockstep vs ot_qwen_tp8_pv256_finalize_static_cal (+ mutants + negative controls)
set -e
cd "$(dirname "$0")/../../.."
O=${OUT:-/tmp/qkd_pv_fin_s_bench}; mkdir -p $O
SRC="rtl/qwen_sys/split_20261014/qkd_pv_fin_s.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv256_finalize_static_cal_gen.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv
 rtl/test/qwen_split/tb_qkd_pv_fin_s.sv"
for M in 0 1 2; do
  iverilog -g2012 -o $O/m$M -s tb_qkd_pv_fin_s -Ptb_qkd_pv_fin_s.MUT=$M $SRC &
done
wait
vvp -n $O/m0 +SEED=${SEED:-7} +N=${N:-40} | tail -3
for M in 1 2; do echo "MUT $M:"; vvp -n $O/m$M +SEED=11 +N=4 | tail -1; done
for G in 1 2 3; do vvp -n $O/m0 +SEED=5 +N=6 +NEG=$G | tail -1; done
