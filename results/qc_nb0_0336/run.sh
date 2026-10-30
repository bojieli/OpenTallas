#!/bin/bash
set -eu
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
W=$(git rev-parse --show-toplevel)
B=${1:?use a scratch output directory}
mkdir -p "$B"
cp "$W/results/qc_nb0_0336/old_nb0.sv" "$W/results/qc_nb0_0336/tb.sv" "$B/"
cd "$W"
F=("$B/tb.sv" "$B/old_nb0.sv" rtl/qwen_dv/s5/s8/qfd_dv_s8_ce.sv rtl/qwen_dv/qfd_dv_redstn2_gsafe.sv rtl/qwen_dv/qfd_dv_station_math_g.sv rtl/qwen_dv/s5/s8/qfd_dv_s8_station_safe.sv rtl/qwen_dv/s5/s8/qfd_dv_s8_station_math_g.sv rtl/common/landed_parent/ot_pl_land_n32.sv rtl/qwen_dv/qfd_dv_ring_delay.sv rtl/qwen_dv/qfd_dv_reset_tree.sv rtl/common/landed_parent/ot_pl_land.sv rtl/common/landed_parent/ot_pl_land_physical.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v)
iverilog -g2012 -s tb -o "$B/test.vvp" "${F[@]}" > "$B/build.log" 2>&1
vvp "$B/test.vvp" > "$B/lockstep.log" 2>&1
iverilog -g2012 -s tb -Ptb.MUT=1 -o "$B/mut.vvp" "${F[@]}" > "$B/build_mut.log" 2>&1
if vvp "$B/mut.vvp" > "$B/mutant.log" 2>&1; then echo MUTANT_NOT_CAUGHT;exit 2;fi
echo PASS_MUTANT_CAUGHT
