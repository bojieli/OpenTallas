#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "$1"); shift
mkdir -p "$OUT"
cd "$ROOT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
P=rtl/hbm_accel/generic/collective/p2p
"$V" --binary --timing -j "${JOBS:-4}" -Wno-fatal -Wno-WIDTH --top-module tb_hgi_coll_qslots --Mdir "$OUT/obj" "$@" "$P/tb_hgi_coll_qslots.sv" "$P/ot_hgi_coll_qslots.sv" > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_hgi_coll_qslots" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
grep -q '^QSLOTS PASS' "$OUT/run.log"
