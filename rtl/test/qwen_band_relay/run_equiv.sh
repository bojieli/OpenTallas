#!/usr/bin/env bash
# run_equiv.sh <outdir> [MUT]   Verilator 5.050, exact BAND relay equivalence (see tb header)
set -euo pipefail
OUT=${1:?outdir}; MUT=${2:-0}
VER=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
cd "$(dirname "$0")/../../.."
SRCS="rtl/test/qwen_lane_band/tb_qfd_band_lanes.sv rtl/qwen_sys/lane_band_20261008/ot_qfd_band_lanes.sv rtl/physical/ot_qwen_tt_up4_cluster.sv
 rtl/physical/ot_qwen_band_lanes_slots.sv rtl/physical/ot_qwen_spine_lane.sv rtl/hdc/ot_qwen_me_spine_h_w12.sv
 rtl/hdc/ot_qwen_w12_matvec.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_add_lat_nr.sv
 physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
 rtl/qwen_sys/band_fault_tree_20261015/ot_qfd_band_fault_tree3.sv rtl/qwen_sys/band_relay_20261015/ot_qfd_band_relay.sv"
mkdir -p "$OUT"
"$VER" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINMISSING -Wno-TIMESCALEMOD -Wno-LATCH -Wno-MULTIDRIVEN \
  -Wno-BLKSEQ -Wno-UNOPTFLAT --x-assign 0 --x-initial 0 -j "${JOBS:-8}" -DOT_QFD_BAND_RELAY_NOWRAP --top-module tb_qfd_band_relay_equiv \
  -GMUT=$MUT --Mdir "$OUT/obj" rtl/test/qwen_band_relay/tb_qfd_band_relay_equiv.sv $SRCS > "$OUT/build.log" 2>&1 || { tail -30 "$OUT/build.log"; exit 1; }
"$OUT/obj/Vtb_qfd_band_relay_equiv" > "$OUT/run.log" 2>&1 || true
grep -E "BAND_RELAY_EQUIV|PASS qfd_band|FAIL qfd_band|MISMATCH" "$OUT/run.log" | head -20
grep -q "BAND_RELAY_EQUIV PASS" "$OUT/run.log"
