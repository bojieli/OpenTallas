#!/usr/bin/env bash
# H-ELEM-A 2026-10-15: exact bench of ot_hbm_accel_smh_pvacc vs the att_pv golden order; usage run_pvacc.sh <out> [MUT] [seed]
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/../../../.." && pwd); OUT=$(realpath -m "$1"); MUT=${2:-0}; SEED=${3:-7}
mkdir -p "$OUT"; python3 "$HERE/pvacc_golden.py" gen "$OUT" "$SEED"
iverilog -g2012 -DDIR="\"$OUT\"" -Ptb_pvacc.MUT=$MUT -o "$OUT/sim.vvp" "$HERE/tb_pvacc.sv" "$HERE/ot_hbm_accel_smh_pvacc.sv" \
  "$ROOT/rtl/hdc/ot_hdc_fp32_add_lat.sv" "$ROOT/rtl/hdc/ot_hdc_fp32_mul_lat.sv" "$ROOT/rtl/hdc/ot_hdc_fastfp.sv" "$ROOT/rtl/hdc/ot_hdc_prefix.sv"
vvp -n "$OUT/sim.vvp" > "$OUT/sim.log"
python3 "$HERE/pvacc_golden.py" check "$OUT"
