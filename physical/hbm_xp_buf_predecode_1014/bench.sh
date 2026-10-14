#!/usr/bin/env bash
set -euo pipefail
out=${1:?}; mut=${2:-0}
mkdir -p "$out"
verilator --binary --timing -j 4 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb -GMUT="$mut" --Mdir "$out/obj" physical/hbm_xp_buf_predecode_1014/tb_buf_predecode.sv physical/hbm_xp_buf_predecode_1014/ot_hbm_xp_buf_predecode.sv rtl/hbm_accel/generic/xp/ot_hgi_xp_tiles.sv > "$out/build.log" 2>&1
"$out/obj/Vtb" > "$out/run.log" 2>&1
cat "$out/run.log"
