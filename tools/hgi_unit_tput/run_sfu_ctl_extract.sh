#!/bin/bash
set -euo pipefail
mut=${MUT_PHASE:-0}
mkdir -p "$OUT"
mapfile -t sources < results/arch/hbm_native_1013/sfu_native_quarter/sources.txt
"${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}" --binary --timing -O2 -j 8 -CFLAGS -O0 -Wno-fatal -Wno-TIMESCALEMOD --top-module tb_hgi_sfu_ctl_extract -GMUT_PHASE="$mut" --Mdir "$OUT/obj" "${sources[@]}" > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_hgi_sfu_ctl_extract" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
