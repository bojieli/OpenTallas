#!/bin/bash
set -euo pipefail
OUT=$(mkdir -p "$1" && realpath "$1")
MUT=${2:-0}
SRC=(rtl/physical/ot_qwen_tile_operand.sv rtl/physical/ot_qwen_tile_rqr_half.sv rtl/test/tb_qwen_region_glue.sv)
V=${VERILATOR:-verilator}
HASH=$({ sha256sum "${SRC[@]}" "$0"; "$V" --version; } | sha256sum | cut -d' ' -f1)
if [[ ! -f "$OUT/build.sha256" || $(cat "$OUT/build.sha256") != "$HASH" ]]; then
 "$V" --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_qwen_region_glue -Mdir "$OUT/obj" "${SRC[@]}" > "$OUT/build.log" 2>&1
 printf '%s\n' "$HASH" > "$OUT/build.sha256"
 sha256sum "${SRC[@]}" "$0" > "$OUT/sources.sha256"
fi
"$OUT/obj/Vtb_qwen_region_glue" +MUT="$MUT" | tee "$OUT/run_$MUT.log"
grep -q '^REGION_GLUE_PASS checks=512' "$OUT/run_$MUT.log"
! grep -q 'REGION_GLUE_FAIL\|REGION_GLUE_MISMATCH\|%Error' "$OUT/run_$MUT.log"
