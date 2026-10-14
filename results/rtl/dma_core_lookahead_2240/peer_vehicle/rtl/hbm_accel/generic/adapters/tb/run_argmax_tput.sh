#!/usr/bin/env bash
# hgi-1010/tput1-argmax: ARGMAX.LOCAL production-shape throughput bench (tb_hgi_argmax_tput).
# usage: run_argmax_tput.sh <qwen|ds> <outdir> [LPS 8|16] [MUT 0|1|2] [GAP]
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
M=$1; OUT=$(realpath -m "$2"); LPS=${3:-8}; MUT=${4:-0}; GAP=${5:-1}
VL=${VERILATOR:-$( [ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && echo "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" || echo verilator)}
mkdir -p "$OUT"; cd "$ROOT"
[ -f "$OUT/vec/at_case.mem" ] || python3 tools/hgi_unitrate/argmax_tput_vec.py --model "$M" --out "$OUT/vec" > "$OUT/gen.log"
SRC="rtl/hbm_accel/generic/adapters/ot_hgi_argmax_record.sv physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_m.sv
  physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_value_m.sv physical/hbm_mtp/rtl/ot_dshbm_argmax_m.sv rtl/hdc/ot_hdc_fastfp.sv
  rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/gpu/ot_gpu_fadd.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv
  rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v"
TAG=l${LPS}_m${MUT}
"$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN --top-module tb_hgi_argmax_tput \
  -I"$OUT/vec" -DLPS=$LPS -DMUT=$MUT -Mdir "$OUT/obj_$TAG" $SRC rtl/hbm_accel/generic/adapters/tb/tb_hgi_argmax_tput.sv -j ${J:-8} \
  > "$OUT/build_$TAG.log" 2>&1 || { tail -30 "$OUT/build_$TAG.log"; exit 2; }
"$OUT/obj_$TAG/Vtb_hgi_argmax_tput" +DIR="$OUT/vec" +GAP=$GAP | tee "$OUT/run_${TAG}_g${GAP}.log" | tail -16
