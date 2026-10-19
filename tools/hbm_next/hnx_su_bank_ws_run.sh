#!/usr/bin/env bash
# Tile bench of ot_hnx_su_bank6_ws (hnx pinned SU store bank: d4g bank + split write phase + write mux), Verilator 5.050.
# Usage: hnx_su_bank_ws_run.sh OUT [wmut1|wmut2|wmut3]   (mutants must FAIL: HNX_SU_BANK_WS FAIL)
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1"); mut=${2:-}
wm=0; case "$mut" in wmut1) wm=1;; wmut2) wm=2;; wmut3) wm=3;; "") ;; *) echo "bad mutant $mut"; exit 2;; esac
mkdir -p "$out"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
S=rtl/hbm_accel/generic/adapters/static_su/data_store
"$vl" --binary --timing -O1 -j 2 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hnx_su_bank6_ws -GWMUT=$wm \
 --Mdir "$out/obj${mut:+_$mut}" rtl/hbm_next/su/tb/tb_hnx_su_bank6_ws.sv rtl/hbm_next/su/ot_hnx_su_bank6_ws.sv \
 rtl/hbm_next/su/ot_hnx_su_wsplit.sv $S/ot_hbm_su_static_pinned_bank.sv $S/ot_hbm_su_static_bank6_clock_physical.sv \
 $S/ot_hbm_su_static_data_store.sv rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > "$out/build${mut:+_$mut}.log" 2>&1
"$out/obj${mut:+_$mut}/Vtb_hnx_su_bank6_ws"
