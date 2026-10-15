#!/bin/bash
set -euo pipefail
mkdir -p "$OUT"
mapfile -t sources < <(python3 -c 'import json; print("\n".join(json.load(open("tools/ref_tile/specs_hbmsfu_native/hbm_sfu_side_native6r2.json"))["sources"]))')
verilator=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$verilator" --binary --timing -O2 -j 4 -CFLAGS -O0 -Wno-fatal -Wno-TIMESCALEMOD --top-module tb_hbm_su_static_side_native6r2 --Mdir "$OUT/obj" "${sources[@]}" rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv rtl/test/hbm_accel/generic/tb_hbm_su_static_side_native6r2.sv > "$OUT/build.log" 2>&1
rows=$(python3 -c 'import json; print(json.load(open("results/rtl/hbm_sfu_native6_1015/manifest.json"))["rows"])')
"$OUT/obj/Vtb_hbm_su_static_side_native6r2" +DATA=results/rtl/hbm_sfu_native6_1015 +ROWS="$rows" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
for mutant in FN EG CLOCK; do
 set +e
 "$OUT/obj/Vtb_hbm_su_static_side_native6r2" +DATA=results/rtl/hbm_sfu_native6_1015 +ROWS="$rows" +MUT_"$mutant" > "$OUT/mutant_$mutant.log" 2>&1
 status=$?
 set -e
 if [[ $status == 0 ]] || ! grep -Eq 'SIDE_(WORD|FN_MUTANT|EG_MUTANT|FAULT_EQUIV)' "$OUT/mutant_$mutant.log"; then cat "$OUT/mutant_$mutant.log"; exit 1; fi
 echo "PASS native6r2 $mutant mutant rejected"
done
