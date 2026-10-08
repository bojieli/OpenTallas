#!/usr/bin/env bash
# qwen-lane-band: tb_qfd_band_lanes under Verilator.  run_band_lanes.sh <outdir> [-GNAME=VALUE ...]
set -euo pipefail
OUT=${1:?outdir}; shift
VER=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
cd "$(dirname "$0")/../../.."
SRCS="rtl/qwen_sys/lane_band_20261008/ot_qfd_band_lanes.sv rtl/physical/ot_qwen_spine_lane.sv rtl/hdc/ot_qwen_me_spine_h_w12.sv
 rtl/hdc/ot_qwen_w12_matvec.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv"
mkdir -p "$OUT"
"$VER" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINMISSING -Wno-TIMESCALEMOD -Wno-LATCH -Wno-MULTIDRIVEN \
  -Wno-BLKSEQ -Wno-UNOPTFLAT -j "${JOBS:-4}" --top-module tb_qfd_band_lanes "$@" --Mdir "$OUT/obj" \
  rtl/test/qwen_lane_band/tb_qfd_band_lanes.sv $SRCS > "$OUT/build.log" 2>&1 || { tail -30 "$OUT/build.log"; exit 1; }
"$OUT/obj/Vtb_qfd_band_lanes" | tee "$OUT/run.log"
