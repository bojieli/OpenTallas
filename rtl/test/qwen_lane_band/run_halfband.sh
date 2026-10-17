#!/usr/bin/env bash
# Q-PORTMAP b2: tb_qfd_halfband under Verilator.  run_halfband.sh <outdir> [-GNAME=VALUE ...]
set -euo pipefail
OUT=${1:?outdir}; shift
VER=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
cd "$(dirname "$0")/../../.."
SRCS="rtl/qwen_sys/lane_band_20261008/ot_qfd_band_lanes.sv rtl/physical/ot_qwen_spine_lane.sv rtl/physical/ot_qwen_halfband_lanes_slots.sv rtl/qwen_split/qfd_band_upper_b2.sv rtl/qwen_split/qfd_band_upper_b2_l2.sv rtl/qwen_split/qfd_band_upper_b2_l2_s4.sv rtl/physical/ot_qwen_halfband_lanes_slots_b2_l2.sv rtl/hdc/ot_qwen_me_spine_h_w12.sv
 rtl/hdc/ot_qwen_w12_matvec.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_add_lat_nr.sv
 physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
mkdir -p "$OUT"
"$VER" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINMISSING -Wno-TIMESCALEMOD -Wno-LATCH -Wno-MULTIDRIVEN \
  -Wno-BLKSEQ -Wno-UNOPTFLAT -j "${JOBS:-8}" --top-module tb_qfd_halfband ${VDEF:-} "$@" --Mdir "$OUT/obj" \
  rtl/test/qwen_lane_band/tb_qfd_halfband.sv $SRCS > "$OUT/build.log" 2>&1 || { tail -30 "$OUT/build.log"; exit 1; }
"$OUT/obj/Vtb_qfd_halfband" | tee "$OUT/run.log"
