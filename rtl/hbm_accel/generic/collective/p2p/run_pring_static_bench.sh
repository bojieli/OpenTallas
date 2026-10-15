#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "$1"); shift; mkdir -p "$OUT"; cd "$ROOT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
P=rtl/hbm_accel/generic/collective/p2p
"$V" --binary --timing -O2 -j "${JOBS:-8}" -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ --top-module tb_hgi_coll_pring_static --Mdir "$OUT/obj" "$@" \
 "$P/tb_hgi_coll_pring_static.sv" "$P/ot_hgi_coll_pring_static.sv" "$P/f32add.c" rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv > "$OUT/build.log" 2>&1 || { tail -30 "$OUT/build.log";exit 2; }
"$OUT/obj/Vtb_hgi_coll_pring_static" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
grep -q '^STATIC_RING PASS ' "$OUT/run.log"
for scenario in 1 2 3 4 5 6 7 8 10 11 12; do
 "$OUT/obj/Vtb_hgi_coll_pring_static" +fault="$scenario" > "$OUT/fault-$scenario.log" 2>&1
 grep -q '^STATIC_RING FAULT PASS ' "$OUT/fault-$scenario.log"
 cat "$OUT/fault-$scenario.log"
done
