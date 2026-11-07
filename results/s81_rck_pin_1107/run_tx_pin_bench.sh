#!/usr/bin/env bash
set -euo pipefail
cd /
D=${1:?payload directory}; OUT=${2:?output directory}
mkdir -p "$OUT"
verilator --binary --timing -j 4 -Wno-fatal -Wno-WIDTH -Wno-UNOPTFLAT -Wno-MULTITOP \
  +define+OT_S81_SERDES_COL_PIN +incdir+"$D" --top-module tb_serdes_col_tx_pin \
  --Mdir "$OUT/obj" -o tx_pin \
  "$D/ot_s81_kp4_common.sv" "$D/ot_s81_kp4_enc.sv" "$D/ot_pl_land.sv" \
  "$D/ot_pdie_serdes_col.sv" "$D/tb_serdes_col_tx_pin.sv" > "$OUT/build.log" 2>&1
"$OUT/obj/tx_pin" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
