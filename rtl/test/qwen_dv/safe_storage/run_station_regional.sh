#!/bin/bash
# QW-SLICE 10-19: regional station vs monolith (Verilator 5.050, as the closure daemon).  args: work MUT RMUT [defines]
set -euo pipefail
work=$1;mut=${2:-0};rmut=${3:-0};defs=${4:-}
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
tag=p${PIN:-0}m${mut}r${rmut}${defs//[^A-Za-z0-9]/}
mkdir -p "$work"
verilator --binary --timing -j 8 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_station_regional -GMUT="$mut" -GRMUT="$rmut" -GPIN="${PIN:-0}" $defs --Mdir "$work/obj_$tag" \
 rtl/test/qwen_dv/safe_storage/tb_station_regional.sv rtl/qwen_dv/qfd_dv_redstn2_gsafe.sv rtl/qwen_dv/qfd_dv_redstn2_regional.sv rtl/qwen_dv/qfd_dv_station_math_g.sv \
 rtl/qwen_dv/qfd_dv_ring_delay.sv rtl/qwen_dv/qfd_dv_reset_tree.sv rtl/common/landed_parent/ot_pl_land.sv rtl/common/landed_parent/ot_pl_land_physical.sv \
 rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v > "$work/build_$tag.log" 2>&1
"$work/obj_$tag/Vtb_station_regional"
