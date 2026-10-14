#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
OUT=$(realpath -m "${1:?output directory required}")
MODE=${2:-exact}
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$OUT/obj"
cd "$ROOT"
DEFINES=()
if [ "$MODE" = mutant ]; then DEFINES=(-DLINK_ASSOC_MUT); fi
"$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH --top-module tb_hgi_hc_quarter_link6 "${DEFINES[@]}" \
 -Mdir "$OUT/obj" rtl/lib/ot_rst_relay.sv rtl/hbm_accel/generic/peers/ot_hgi_hc_quarter_link6.sv \
 rtl/hbm_accel/generic/peers/tb_hgi_hc_quarter_link6.sv -j "${J:-4}" > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_hgi_hc_quarter_link6" > "$OUT/run.log"
cat "$OUT/run.log"
grep -q '^HC_QUARTER_LINK PASS' "$OUT/run.log"
