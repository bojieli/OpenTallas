#!/bin/bash
# RBH-SFUS 10-18: lockstep bench of the sfus hard tile vs today's sfustore. Usage: OUT=<dir> run_sfustore_hw.sh <MUT> [SEED] [QID]
set -uo pipefail
cd "$(dirname "$0")/../../../../../.."
OUT=${OUT:?set OUT to a scratch directory}; mkdir -p "$OUT"
M=${1:-0}; SEED=${2:-1}; QID=${3:-1}
S=rtl/hbm_accel/generic/adapters/static_su
SRC=("$S/collport/tb_hbm_su_sfustore_hw.sv" "$S/collport/ot_hbm_su_static_sfustore_hw.sv" "$S/collport/ot_hbm_su_static_sfustore.sv" "$S/data_store/ot_hbm_su_static_pinned_bank.sv" "$S/data_store/ot_hbm_su_static_data_store.sv" rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
sha256sum "${SRC[@]}" > "$OUT/q${QID}source_mut$M.sha256"
iverilog -g2012 -s tb_hbm_su_sfustore_hw -Ptb_hbm_su_sfustore_hw.MUT="$M" -Ptb_hbm_su_sfustore_hw.QID="$QID" -o "$OUT/q${QID}mut$M.vvp" "${SRC[@]}" > "$OUT/q${QID}build$M.log" 2>&1 || { cat "$OUT/q${QID}build$M.log"; echo "SFUSTORE_HW BUILD FAIL"; exit 2; }
vvp "$OUT/q${QID}mut$M.vvp" +SEED="$SEED" 2>&1 | tee "$OUT/q${QID}mut$M.log"
rc=${PIPESTATUS[0]}
grep -q "SFUSTORE_HW LOCKSTEP PASS" "$OUT/q${QID}mut$M.log" && [ "$rc" = 0 ] && { echo "SFUSTORE_HW_GATE PASS MUT=$M"; exit 0; }
echo "SFUSTORE_HW_GATE FAIL MUT=$M rc=$rc"; exit 1
