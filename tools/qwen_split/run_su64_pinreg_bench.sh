#!/usr/bin/env bash
# Q-ELEM-SUC 2026-10-16: qfd_sp_su64_sfu PINREG differential bench (rtl/test/qwen_split/tb_qfd_su64_pinreg.sv).
#   run_su64_pinreg_bench.sh OUTDIR MODE PRMUT [SEED]   -> prints PASS/FAIL qfd_su64_pinreg ...
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?out dir}; mode=${2:-0}; mut=${3:-0}; seed=${4:-11}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$out"
srcs=(
  "$root/rtl/qwen_split/qfd_sp_su64_sfu.sv"
  "$root/rtl/qwen_sys/static_schedule_20261014/ot_qfd_sp_su64_static_entries.sv"
  "$root/rtl/hdc/ot_hdc_delay.sv"
  "$root/rtl/qwen_sys/static_schedule_20261014/ot_hdc_vstream_static_entries.sv"
  "$root/rtl/physical/ot_hdc_vred_pending_guard.sv"
  "$root/rtl/physical/ot_hdc_vreduce_entries64.sv"
  "$root/rtl/hdc/ot_hdc_sfu.sv"
  "$root/rtl/hdc/ot_hdc_fp32_add_lat.sv"
  "$root/rtl/hdc/ot_hdc_prefix.sv"
  "$root/rtl/hdc/ot_hdc_fastfp.sv"
  "$root/rtl/hdc/ot_hdc_fp32_mul_lat.sv"
  "$root/rtl/hdc/ot_hdc_vreduce.sv"
  "$root/rtl/physical/ot_hdc_vstream_lane_clock_entries_candidate.sv"
  "$root/rtl/hdc/ot_hdc_vstream_sfu_t.sv"
  "$root/rtl/hdc/ot_hdc_sfu_q.sv"
  "$root/rtl/hdc/ot_hdc_vstream_lane_t.sv"
  "$root/rtl/hdc/ot_hdc_vstream_lane.sv"
  "$root/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
  "$root/rtl/physical/ot_qfd_su_align_entries64.sv"
  "$root/rtl/qwen_sys/static_embedding_20261014/ot_qfd_su_embed_static.sv"
  "$root/rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv"
  "$root/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
  "$root/rtl/qwen_sys/missing_masters_20261007/ot_qfd_spine_masters.sv"
  "$root/rtl/qwen_split/qfd_su_static_copy.sv"
  "$root/rtl/qwen_split/qfd_su_vm_pack.sv"
  "$root/rtl/test/qwen_split/tb_qfd_su64_pinreg.sv"
)
"$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINMISSING -Wno-TIMESCALEMOD -Wno-LATCH \
  -Wno-MULTIDRIVEN -Wno-BLKSEQ -Wno-UNOPTFLAT -j "${BENCH_JOBS:-8}" --top-module tb_qfd_su64_pinreg \
  -GMODE="$mode" -GPRMUT="$mut" -GSEED="$seed" --Mdir "$out/obj" "${srcs[@]}" > "$out/build.log" 2>&1
"$out/obj/Vtb_qfd_su64_pinreg" | tee "$out/run.log"
