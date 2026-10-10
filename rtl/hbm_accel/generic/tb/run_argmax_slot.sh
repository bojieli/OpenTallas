#!/usr/bin/env bash
# mtp-lead 2026-10-09: bench of ot_hgi_argmax_slot (R25G MTP slot ARGMAX unit = ot_hgi_argmax_record + ot_hgi_argmax18_m
# behind the 683 / 3 dispatch bus) on the hgi-adapters argmax vectors, the real engine and the real HGI VM.
#   usage: run_argmax_slot.sh <outdir> [MUT_RANK]      prints HGI_ARGMAX PASS / FAIL (MUT_RANK must FAIL)
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd)
OUT=$(realpath -m "${1:-/tmp/hgi_argmax_slot}"); MUT=${2:-}
VL=${VERILATOR:-$( [ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && echo "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" || echo verilator)}
mkdir -p "$OUT"; cd "$ROOT"
python3 tools/hgi_adapters/argmax_bench.py --out "$OUT/vec" > "$OUT/gen.log"
SRC="rtl/hbm_accel/generic/ot_hgi_argmax_slot.sv rtl/hbm_accel/generic/adapters/ot_hgi_argmax_record.sv
  physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_m.sv physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_value_m.sv
  physical/hbm_mtp/rtl/ot_dshbm_argmax_m.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
  rtl/gpu/ot_gpu_fadd.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv
  physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v"
D=""; [ -n "$MUT" ] && D="-D$MUT"
"$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT --top-module tb_hgi_argmax_slot \
  -I"$OUT/vec" $D -Mdir "$OUT/obj${MUT:+_$MUT}" $SRC rtl/hbm_accel/generic/tb/tb_hgi_argmax_slot.sv -j 8 \
  > "$OUT/build${MUT:+_$MUT}.log" 2>&1 || { tail -30 "$OUT/build${MUT:+_$MUT}.log"; echo "BUILD_FAIL"; exit 2; }
"$OUT/obj${MUT:+_$MUT}/Vtb_hgi_argmax_slot" +DIR="$OUT/vec" | tee "$OUT/run${MUT:+_$MUT}.log" | tail -8
