#!/usr/bin/env bash
set -euo pipefail
OUT=$(realpath -m "$1"); MUT=${2:-0}; mkdir -p "$OUT"
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --version
verilator --binary --timing -j 4 -GMUT="$MUT" -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_smb_l15 --Mdir "$OUT/obj" \
 rtl/test/hbm_accel/smb_l15/tb_smb_l15.sv \
 rtl/hbm_accel/host_static_20261015/ot_static_run_target.sv \
 rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_issuer_rel.sv \
 rtl/hbm_accel/sm/static/ot_smh_calendar_static_x.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_smb_l15" | tee "$OUT/run.log"
