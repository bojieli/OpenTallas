#!/bin/bash
set -euo pipefail
mut=${MUT_PHASE:-0}
mkdir -p "$OUT"
defs=()
if [ "${MUT_PHASE:-0}" != 0 ];then defs+=(-DOT_SFU_PHASE_MUTANT);fi
mapfile -t sources < results/arch/hbm_native_1013/sfu_native_quarter/r2_sources.txt
"${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}" --binary --timing -O2 -j 8 -CFLAGS -O0 -Wno-fatal -Wno-TIMESCALEMOD "${defs[@]}" --top-module tb_hgi_sfu_quarter_phase -GMUT_PHASE="$mut" -GSPLIT_S_PIPE="${SPLIT_S_PIPE:-0}" --Mdir "$OUT/obj" "${sources[@]}" > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_hgi_sfu_quarter_phase" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
