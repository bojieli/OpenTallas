#!/bin/bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$root"
out=$(realpath -m "${1:?out}")
mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/bin/verilator
[ -x "$vl" ] || vl=verilator
src=(rtl/test/hbm_idx_static/tb_hcol_regional_equiv.sv rtl/hdc/v41x/ot_hbm_idx_hcol_regional.sv results/hbm_hcol_regional_1101/native_selected_C/ot_hbm_idx_chunk_rt_h.sv results/hbm_hcol_regional_1101/native_selected_C/ot_hdc_delay.sv results/hbm_hcol_regional_1101/native_selected_C/ot_hdc_fastfp.sv results/hbm_hcol_regional_1101/native_selected_C/ot_hdc_fp32_add_lat.sv results/hbm_hcol_regional_1101/native_selected_C/ot_hdc_prefix.sv results/hbm_hcol_regional_1101/native_selected_C/ot_hdc_v41x_idx_arith.sv results/hbm_hcol_regional_1101/native_selected_C/ot_hdc_v41x_idx_arith_lat.sv results/hbm_hcol_regional_1101/native_selected_C/ot_hnx_idx_hcol_plan.sv results/hbm_hcol_regional_1101/native_selected_C/ot_rst_delivered3.sv results/hbm_hcol_regional_1101/native_selected_C/ot_rst_relay.sv)
sha256sum "${src[@]}" > "$out/sources.sha256"
"$vl" --binary --timing -j "${JOBS:-4}" -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_hcol_regional_equiv --Mdir "$out/obj" "${src[@]}" > "$out/build.log" 2>&1
"$out/obj/Vtb_hcol_regional_equiv" +MUT=0 > "$out/positive.log" 2>&1
set +e
"$out/obj/Vtb_hcol_regional_equiv" +MUT=1 > "$out/mutant.log" 2>&1
rc=$?
set -e
test "$rc" -ne 0
grep 'HCOL_REGIONAL_EQ PASS' "$out/positive.log"
grep 'HCOL_REGIONAL_EQ FAIL' "$out/mutant.log"
