#!/usr/bin/env bash
# hgi-adapters: ot_hgi_su_record bench (Verilator).  usage: [UNIT=sfu] run_su.sh <outdir> [MUT_ISTRIDE|MUT_EARLY]
# UNIT=sfu: ot_hgi_sfu_record (SFU.GLU) on the same bench; MUT_ISTRIDE is then the SFU operand-swap mutant
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "${1:-/tmp/hgi_su_run}"); MUT=${2:-}
VL=${VERILATOR:-$( [ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && echo "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" || echo verilator)}
mkdir -p "$OUT"
python3 "$ROOT/tools/hgi_adapters/su_bench.py" --unit "${UNIT:-su}" --out "$OUT/vec"
L="rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv
   rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv
   rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv
   rtl/hdc/v41/ot_hdc_softplus.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_vec_lane.sv
   rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv rtl/hdc/v41x/ot_hdc_v41x_vec_red.sv rtl/hdc/v41x/ot_hdc_v41x_vec.sv
   rtl/hbm_accel/generic/adapters/ot_hgi_su_record.sv rtl/hbm_accel/generic/adapters/ot_hgi_sfu_record.sv
   rtl/hbm_accel/generic/adapters/tb/tb_hgi_su_record.sv"
D=""; [ -n "$MUT" ] && D="-D$MUT"; [ "${UNIT:-su}" = sfu ] && D="$D -DUNIT_SFU"
cd "$ROOT"
"$VL" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN \
  --top-module tb_hgi_su_record -I"$OUT/vec" $D -Mdir "$OUT/obj${MUT:+_$MUT}" $L -j 24 > "$OUT/build${MUT:+_$MUT}.log" 2>&1 \
  || { tail -30 "$OUT/build${MUT:+_$MUT}.log"; exit 2; }
"$OUT/obj${MUT:+_$MUT}/Vtb_hgi_su_record" +DIR="$OUT/vec" | tee "$OUT/run${MUT:+_$MUT}.log" | grep -v '^DATA' | tail -25
