#!/bin/bash
set -euo pipefail
out=$(realpath -m "${1:?out}");mut=${2:-0};mkdir -p "$out"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
src=(rtl/test/hbm_idx_static/tb_idx_glue_reset_f32.sv rtl/hdc/v41x/ot_hbm_idx_chunk_rt_c.sv rtl/lib/ot_rst_relay_l.sv)
sha256sum "${src[@]}" > "$out/sources.sha256"
"$V" --binary --timing -j 2 -O1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_idx_glue_reset_f32 -GMUT="$mut" -Mdir "$out/obj" "${src[@]}" > "$out/build.log" 2>&1
"$out/obj/Vtb_idx_glue_reset_f32" > "$out/run.log" 2>&1
cat "$out/run.log"
