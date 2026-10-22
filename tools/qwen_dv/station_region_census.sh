#!/bin/bash
# QW-SLICE 10-19: one station region (qfd_dv_redstn2_region, PIN_IN=1, no OT_ASSERT) -> generic stat + ASAP7 RVT TT
# mapped std-cell area (kit outline basis).  args: SRC_ROOT OUT_DIR LIB(combined asap7 liberty)
set -euo pipefail
src=$1; out=$2; LIB=$3; mkdir -p $out; cd $src
yosys -Q -p "read_verilog -lib -sv physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1_bb.v; \
read_verilog -sv -D SYNTHESIS rtl/qwen_dv/qfd_dv_redstn2_gsafe.sv rtl/qwen_dv/qfd_dv_redstn2_regional.sv rtl/qwen_dv/qfd_dv_station_math_g.sv \
 rtl/qwen_dv/qfd_dv_ring_delay.sv rtl/qwen_dv/qfd_dv_reset_tree.sv rtl/common/landed_parent/ot_pl_land.sv rtl/common/landed_parent/ot_pl_land_physical.sv \
 rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv; \
hierarchy -top qfd_dv_redstn2_region; proc; opt -purge; memory; opt -purge; tee -o $out/generic_stat.txt stat; \
flatten; opt -purge; tee -o $out/generic_flat_stat.txt stat; \
techmap; opt -fast; dfflegalize -cell \$_DFF_P_ 01 -cell \$_DFF_PN0_ 01 -cell \$_DFF_PN1_ 01; dfflibmap -liberty $LIB; abc -liberty $LIB; opt_clean; \
tee -o $out/mapped_stat.txt stat -liberty $LIB" > $out/yosys.log 2>&1
grep -E "Chip area for top|sequential" $out/mapped_stat.txt | tail -2 || true
grep -E "^\s+[0-9]+\s+\\\$_(DFF|SDFF|DFFE|SDFFE|ALDFF|DFFSR|ADFF)" $out/generic_flat_stat.txt | awk '{s+=$1} END{print "generic_flat_ff_cells", s}' || true
grep -E "ot_sram_1r1w_32x64_m1" $out/generic_flat_stat.txt | tail -1 || true
