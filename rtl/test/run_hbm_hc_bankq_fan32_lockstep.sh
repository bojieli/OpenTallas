#!/bin/bash
# STEWARD-HBMe/HC 10-23 FAN32 lockstep bench (Verilator 5.050).  Usage: VAR=0|1|2 MUTB=0|2 [NCYC=n] OUT=dir bash $0
set -euo pipefail
for d in "$HOME/.local/opentallas-tools/verilator-5.050/bin" /opt/verilator-5.050/bin; do [ -x "$d/verilator" ] && export PATH="$d:$PATH" && break; done
VAR=${VAR:-0}; MUTB=${MUTB:-0}; NCYC=${NCYC:-20000}; OUT=${OUT:-/tmp/hcb_fan32_$VAR_$MUTB}
mkdir -p "$OUT"; verilator --version
P=rtl/hbm_accel/generic/peers/static_hc
verilator --binary --timing -j 16 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
  +define+VAR=$VAR +define+MUTB=$MUTB +define+NCYC=$NCYC --top-module tb_hbm_hc_bankq_fan32_lockstep \
  --Mdir "$OUT/obj" -o tb rtl/test/tb_hbm_hc_bankq_fan32_lockstep.sv \
  $P/ot_hbm_hc_bankq_static.sv $P/ot_hbm_hc_bank_static.sv $P/ot_hbm_hc_bankrc_static.sv \
  rtl/hdc/v41x/ot_hdc_v41x_hcp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv \
  rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_delay.sv rtl/lib/ot_rst_relay.sv \
  physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
  physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > "$OUT/build.log" 2>&1
"$OUT/obj/tb" | tee "$OUT/run.log"
