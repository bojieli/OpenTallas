#!/bin/bash
set -euo pipefail
mkdir -p "$OUT"
"${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}" --binary --timing -O2 -j 4 -CFLAGS -O0 -Wno-fatal -Wno-TIMESCALEMOD --top-module tb_hgi_sfu_bank_native -GPHASE="${PHASE:-61}" --Mdir "$OUT/obj" rtl/hbm_accel/generic/peers/ot_hgi_sfu_bank_lifetime.sv rtl/test/hbm_accel/generic/tb_hgi_sfu_bank_native.sv rtl/hbm_accel/generic/adapters/native_b2/su_quadrant/ot_hbm_b2_lane_cdc.sv rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo_p2.sv rtl/hbm_accel/generic/vm/b2/ot_vms_bank.sv rtl/test/full_sm_service/sram_models.sv > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_hgi_sfu_bank_native" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
