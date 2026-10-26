#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
out=$(mkdir -p "$1" && cd "$1" && pwd)
vl=${VERILATOR:-$HOME/.local/opentallas-tools/bin/verilator}
col=$root/rtl/hbm_accel/generic/adapters/static_su/collport
"$vl" --binary --timing -j "${JOBS:-2}" -Wno-fatal --top-module tb_sfustore_if --Mdir "$out/obj" \
 "$root/tools/hbm_b2/sfustore_if/tb_sfustore_if.sv" \
 "$col/ot_hbm_su_static_sfustore_hw.sv" "$col/ot_hbm_su_sfustore_hw_bank_if.sv" \
 "$root/rtl/hbm_accel/generic/adapters/static_su/data_store/ot_hbm_su_static_data_store.sv" \
 "$root/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v" \
 > "$out/build.log" 2>&1
"$out/obj/Vtb_sfustore_if" > "$out/sim.log" 2>&1
cat "$out/sim.log"
