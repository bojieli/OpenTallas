#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
out=$(realpath -m "${1:?}");mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$vl" -DLAND_K="${2:-2}" --binary --timing -j 4 -O1 -Wno-fatal --top-module tb_col8_land --Mdir "$out/obj" rtl/test/hbm_idx_static/tb_col8_sram_face.sv rtl/hdc/v41x/ot_hbm_idx_col8_landed.sv rtl/hdc/v41x/ot_hbm_idx_col8_sram_landed.sv rtl/hdc/v41x/ot_hbm_idx_col8_sram_face.sv physical/asap7_memory_macros/ot_sram_1r1w2c_64x516_m1/ot_sram_1r1w2c_64x516_m1.v rtl/hdc/v41x/ot_hbm_idx_chunk_rt_c.sv rtl/common/landed_parent/ot_pl_land_physical.sv > "$out/build.log" 2>&1
set +e
"$out/obj/Vtb_col8_land" > "$out/run.log" 2>&1
rc=$?
set -e
cat "$out/run.log"
exit "$rc"
