#!/bin/bash
set -euo pipefail
out=${1:?};mode=${2:-pos};mkdir -p "$out"
python3 tools/prepare_fp32_fan32_models.py --out "$out/cells.v"
mapfile -t src < results/arch/hbm_col8_parent_1021/residual_sources.txt
src+=(rtl/test/hbm_idx_static/fixtures_col8/chunk_reference.sv rtl/test/hbm_idx_static/fixtures_col8/leaf_reference.sv rtl/test/hbm_idx_static/fixtures_col8/quarter_reference.sv rtl/test/hbm_idx_static/tb_col8_residual_equiv.sv physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v "$out/cells.v")
def=();[ "$mode" = pos ] || def=(-DRESID_MUT_KEEP)
sha256sum "${src[@]}" > "$out/sources.sha256"
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -j 4 -O1 -Wno-fatal --top-module tb_col8_residual_equiv "${def[@]}" --Mdir "$out/obj" "${src[@]}" > "$out/build.log" 2>&1 || { tail -30 "$out/build.log";exit 2; }
set +e;"$out/obj/Vtb_col8_residual_equiv" > "$out/run.log" 2>&1;rc=$?;set -e
cat "$out/run.log";exit "$rc"
