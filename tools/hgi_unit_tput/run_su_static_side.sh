#!/bin/bash
set -euo pipefail
mkdir -p "$OUT"
F=physical/ref_tile/sfu_lane_ring3_rt/src
mapfile -t all_sources < "$DATA/sources.f"
sources=()
for p in "${all_sources[@]}";do
 if [[ "$p" != *vec_side_c12* ]];then sources+=("$F/$p");fi
done
sources+=(rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv rtl/hbm_accel/generic/adapters/static_su/arithmetic/ot_hbm_su_static_side.sv rtl/test/hbm_accel/generic/tb_hbm_su_static_side.sv)
"${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}" --binary --timing -O2 -j 4 -CFLAGS -O0 -Wno-fatal -Wno-TIMESCALEMOD --top-module tb_hbm_su_static_side --Mdir "$OUT/obj" "${sources[@]}" > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_hbm_su_static_side" +DATA="$DATA" +ROWS="$ROWS" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
for mutant in FN EG;do
 set +e
 "$OUT/obj/Vtb_hbm_su_static_side" +DATA="$DATA" +ROWS="$ROWS" +MUT_"$mutant" > "$OUT/mutant_${mutant}.log" 2>&1
 mut_rc=$?
 set -e
 if [ "$mut_rc" = 0 ] || ! grep -q "SIDE_${mutant}_MUTANT" "$OUT/mutant_${mutant}.log";then cat "$OUT/mutant_${mutant}.log";exit 1;fi
 printf 'PASS actualSIDE%s mutant rejected rc=%s\n' "$mutant" "$mut_rc"
done
