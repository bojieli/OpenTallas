#!/bin/bash
set -euo pipefail
work=$1;mut=${2:-0}
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
mkdir -p "$work"
station=rtl/qwen_dv/qfd_dv_redstn2_csafe.sv
extra=()
if [ "${DV2_SAFE_STATION_MATH:-0}" = 1 ]; then
 station=rtl/qwen_dv/qfd_dv_redstn2_gsafe.sv
 extra=(rtl/qwen_dv/qfd_dv_station_math_g.sv rtl/qwen_dv/qfd_dv_ring_delay.sv rtl/common/landed_parent/ot_pl_land.sv)
fi
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_station_cfg -GMUT="$mut" --Mdir "$work/obj$mut" \
 rtl/test/qwen_dv/safe_storage/tb_station_cfg.sv "$station" "${extra[@]}" \
 rtl/qwen_dv/qfd_dv_reset_tree.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v \
 rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv \
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_sfu_q.sv > "$work/build$mut.log" 2>&1
"$work/obj$mut/Vtb_station_cfg"
