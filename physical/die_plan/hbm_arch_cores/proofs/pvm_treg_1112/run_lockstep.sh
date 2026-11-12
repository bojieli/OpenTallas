#!/bin/bash
# HBM-CORES-B 11-12: lock-step bench ot_hbm_sm_pv_merge TREG (registered turn decode) vs reference RDREG 0 / TREG 0.
# DUT forms: RDREG1+TREG1 (event form), RDREG0+TREG1, RDREG1+TREG0 (baseline) and the TRMUT 1 negative control (must FAIL).
# Plus the publication bench at RDREG 1 with TREG 1. Run from the repo root; needs Verilator 5.x.
set -u
F="rtl/hbm_accel/sm/attn/ot_hbm_sm_pv_merge.sv rtl/gpu/ot_gpu_fadd.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
O=${O:-/tmp/pvm_treg_$$}; mkdir -p $O
V="verilator --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -DOT_FP_DATA_NORST"
for C in "1 1 0" "0 1 0" "0 0 0" "1 0 0" "1 1 1"; do set -- $C; for MO in 0 1; do
  D=$O/d$1_t$2_m$3_o$MO
  $V --top-module tb_hbm_sm_pv_rdreg -GDREG=$1 -GTREG=$2 -GTRMUT=$3 -GMODE=$MO -Mdir $D $F rtl/test/hbm_accel/sm_attn/tb_hbm_sm_pv_rdreg.sv > $D.build.log 2>&1 || { echo "BUILD FAIL $C"; tail -5 $D.build.log; }
  for S in 1 2 3; do $D/Vtb_hbm_sm_pv_rdreg +seed=$S +cycles=300000 2>&1 | grep RDREG_LOCKSTEP; done
done; done
