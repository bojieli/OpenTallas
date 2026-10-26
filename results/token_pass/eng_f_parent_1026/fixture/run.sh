#!/bin/bash
set -euo pipefail
FIXTURE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$FIXTURE/../../../../" && pwd)
OUT=$(realpath -m "${1:?pass an owned scratch output directory}")
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$OUT"
"$VL" --binary --top-module tb --timing -Wno-fatal -j 4 --Mdir "$OUT/obj" "$FIXTURE/tb.sv" "$FIXTURE/base.sv" "$FIXTURE/trial.sv" "$FIXTURE/mut.sv" "$FIXTURE/cfg.sv" "$FIXTURE/arith_stubs.sv" "$FIXTURE/bind_cells.sv" "$REPO/rtl/lib/ot_rst_relay.sv" > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb" | tee "$OUT/run.log"
