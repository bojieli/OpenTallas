#!/usr/bin/env bash
set -euo pipefail
OUT=$(realpath -m "${1:?outdir}");ROOT=$(cd "$(dirname "$0")/../../../.." && pwd)
cd "$ROOT";mkdir -p "$OUT"
VL=${VERILATOR:-verilator}
"$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH ${XDEF:-} --top-module tb_hgi_hc_chunk_store32 -Mdir "$OUT/obj" -j "${J:-8}" rtl/lib/ot_rst_relay.sv rtl/hbm_accel/generic/peers/ot_hgi_hc_chunk_store32.sv rtl/hbm_accel/generic/peers/tb_hgi_hc_chunk_store32.sv > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_hgi_hc_chunk_store32" | tee "$OUT/run.log"
grep -q '^HC_CHUNK_STORE PASS' "$OUT/run.log"
