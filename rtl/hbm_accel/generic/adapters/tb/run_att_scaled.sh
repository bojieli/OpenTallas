#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "${1:-/tmp/hgi_att_scaled}")
FMT=${2:-fp4}; MUT=${3:-}
mkdir -p "$OUT"
cd "$ROOT"
GEN=(); DEF=()
if [ "$FMT" = fp8 ]; then GEN+=(--fp8); DEF+=(-DWINDOW_FP8); fi
if [ -n "$MUT" ]; then DEF+=(-D"$MUT"); fi
python3 tools/hgi_adapters/att_scaled_bench.py --out "$OUT" "${GEN[@]}" > "$OUT/generate.log"
iverilog -g2012 -s tb_hgi_att_scaled "${DEF[@]}" -I"$OUT" -o "$OUT/test" \
 rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv rtl/hbm_accel/generic/peers/ot_hgi_att_fp8_provenance.sv \
 rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv \
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv \
 rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hbm_accel/generic/adapters/tb/tb_hgi_att_scaled.sv
cd "$OUT"
vvp test > run.log
grep -q 'ATT_SCALED PASS' run.log
