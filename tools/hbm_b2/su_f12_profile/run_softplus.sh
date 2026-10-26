#!/usr/bin/env bash
# Smallest arithmetic profile vehicle; run under ot-run, no physical qualification.
set -euo pipefail
ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
OUT=$(realpath -m "${1:?fresh output directory}")
test ! -e "$OUT"
mkdir -p "$OUT"
python3 "$ROOT/tools/hbm_b2/su_f12_profile.py" --full-qid 2 --out "$OUT/source"
SRC=(rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat_c12.sv rtl/hdc/ot_hdc_fp32_f12.sv
 rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv
 rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_fsqrt.sv
 rtl/hbm_accel/generic/adapters/static_su/arithmetic/ot_hbm_su_static_side.sv)
for k in "${!SRC[@]}";do SRC[$k]="$ROOT/${SRC[$k]}";done
verilator --binary --timing -Wno-fatal -j "${CPUS:-4}" --top-module tb_su_f12_softplus \
 --Mdir "$OUT/obj" "${SRC[@]}" "$OUT/source/ot_hbm_su_static_side.sv" \
 "$ROOT/tools/hbm_b2/su_f12_profile/tb_softplus.sv" >"$OUT/build.log" 2>&1
"$OUT/obj/Vtb_su_f12_softplus" >"$OUT/run.log" 2>&1
set +e
"$OUT/obj/Vtb_su_f12_softplus" +MUT >"$OUT/mutant.log" 2>&1
mut_rc=$?
set -e
test "$mut_rc" != 0
cat "$OUT/run.log"
echo 'SU_F12_SOFTPLUS_GATE PASS (arithmetic only; retimed36, mutant caught)'
