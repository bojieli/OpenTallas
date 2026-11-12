#!/bin/bash
# HBM-CORES-B 11-12: lock-step bench ot_hbm_sm_pv_merge RDREG 1 vs RDREG 0 (+ RDMUT 1/2/3 negative controls) and the
# existing publication bench at RDREG 0/1. Run from the repo root; needs Verilator 5.x.
set -u
F="rtl/hbm_accel/sm/attn/ot_hbm_sm_pv_merge.sv rtl/gpu/ot_gpu_fadd.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
O=${O:-/tmp/pvm_rdreg_$$}; mkdir -p $O
V="verilator --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -DOT_FP_DATA_NORST"
for M in 0 1 2 3; do for MO in 0 1; do
  $V --top-module tb_hbm_sm_pv_rdreg -GRDMUT=$M -GMODE=$MO -Mdir $O/m${M}_o$MO $F rtl/test/hbm_accel/sm_attn/tb_hbm_sm_pv_rdreg.sv > $O/b_m${M}_o$MO.log 2>&1
  for S in 1 2 3; do $O/m${M}_o$MO/Vtb_hbm_sm_pv_rdreg +seed=$S +cycles=300000 2>&1 | grep RDREG_LOCKSTEP; done
done; done
for R in 0 1; do for M in 0 3 4; do
  $V --top-module tb_hbm_sm_pv_publish -GRDREG=$R -GMUT=$M -Mdir $O/p_r${R}_m$M $F rtl/test/hbm_accel/sm_attn/tb_hbm_sm_pv_publish.sv > $O/bp_r${R}_m$M.log 2>&1
  echo "publish RDREG=$R MUT=$M: $($O/p_r${R}_m$M/Vtb_hbm_sm_pv_publish 2>&1 | grep -E 'PASS|Fatal' | head -2 | tr '\n' ' ')"
done; done
