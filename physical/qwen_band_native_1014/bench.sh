#!/bin/bash
set -eu
out=$1; bl=$2
mkdir -p "$out"
verilator --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINMISSING -Wno-TIMESCALEMOD -Wno-LATCH -Wno-MULTIDRIVEN -Wno-BLKSEQ -Wno-UNOPTFLAT -j 8 --top-module tb_qfd_band_lanes -GNL=16 -GNBP=3 -GSEED=3 -GRDMEM=1 -GBANR=1 -GNOPS=2000 -GLNK=1 -GBL="$bl" --Mdir "$out/obj" rtl/test/qwen_lane_band/tb_qfd_band_lanes.sv rtl/qwen_sys/lane_band_20261008/ot_qfd_band_lanes.sv rtl/physical/ot_qwen_tt_up4_cluster.sv rtl/physical/ot_qwen_band_lanes_slots.sv rtl/physical/ot_qwen_spine_lane.sv rtl/hdc/ot_qwen_me_spine_h_w12.sv rtl/hdc/ot_qwen_w12_matvec.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_add_lat_nr.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > "$out/build.log" 2>&1
set +e
"$out/obj/Vtb_qfd_band_lanes" > "$out/run.log" 2>&1
rc=$?
set -e
cat "$out/run.log"
exit "$rc"
