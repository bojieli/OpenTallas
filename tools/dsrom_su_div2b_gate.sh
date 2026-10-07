#!/bin/bash
# Run from a clean, source-pinned tree, under the host admission guard.
set -euo pipefail
OUT=${1:?output directory}
mkdir -p "$OUT"
VL=${OPENTALLAS_TOOLS_ROOT:-$HOME/.local/opentallas-tools}/verilator-5.050/bin/verilator
"$VL" --binary -O2 -Wno-fatal -Wno-WIDTH --top-module tb_dsrom_su_fdiv_f12_eq -GNR=2 -Mdir "$OUT/obj" -j 8 \
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/test/sim_hdc_prefix_beh.sv \
 rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_f12.sv \
 rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv \
 rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv \
 rtl/hdc/v41x/ot_dsrom_su_fdiv_f12.sv rtl/test/tb_dsrom_su_fdiv_f12_eq.sv > "$OUT/build.log" 2>&1
for seed in 1 2 3 4; do
 "$OUT/obj/Vtb_dsrom_su_fdiv_f12_eq" +N=2500000 +SEED="$seed" > "$OUT/seed_$seed.log" 2>&1
 grep -q 'FDIVEQ n=2500000 compared=2500000 reference=2500000 mismatches=0' "$OUT/seed_$seed.log"
done
for negative in INJECT_MISMATCH SHORT_DRAIN; do
 if "$OUT/obj/Vtb_dsrom_su_fdiv_f12_eq" +N=128 +SEED=1 +"$negative" > "$OUT/negative_$negative.log" 2>&1; then
  echo "FAIL negative unexpectedly passed: $negative" >&2
  exit 1
 fi
 grep -q 'FDIVEQ incomplete or mismatching stream' "$OUT/negative_$negative.log"
done
printf 'PASS_DIV2B_10M_FULL_DRAIN\n' > "$OUT/verdict.txt"
