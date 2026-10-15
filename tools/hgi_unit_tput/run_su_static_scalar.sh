#!/bin/bash
set -euo pipefail
mkdir -p "$OUT"
F=physical/ref_tile/sfu_lane_ring3_rt/src
mapfile -t all_sources < "$DATA/sources.f"
sources=()
for p in "${all_sources[@]}";do
 if [[ "$p" != *vec_side_c12* ]];then sources+=("$F/$p");fi
done
for p in arithmetic/ot_hbm_su_static_lane.sv arithmetic/ot_hbm_su_static_ins.sv data_store/ot_hbm_su_static_data_store.sv data_store/ot_hbm_su_static_pinned_bank.sv;do
 sources+=("$DEPS/rtl/hbm_accel/generic/adapters/static_su/$p")
done
sources+=("$DEPS/rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv"
 rtl/hbm_accel/generic/adapters/static_su/arithmetic/ot_hbm_su_static_side.sv
 rtl/hbm_accel/generic/adapters/static_su/arithmetic/ot_hbm_su_static_scalar.sv
 rtl/test/hbm_accel/generic/tb_hbm_su_static_scalar.sv
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
"${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}" --binary --timing -O2 -j 4 -CFLAGS -O0 -Wno-fatal -Wno-TIMESCALEMOD --top-module tb_hbm_su_static_scalar --Mdir "$OUT/obj" "${sources[@]}" > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_hbm_su_static_scalar" +DATA="$DATA" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
for mutant in FN DIV;do
 set +e
 "$OUT/obj/Vtb_hbm_su_static_scalar" +DATA="$DATA" +MUT_"$mutant" > "$OUT/mutant_${mutant}.log" 2>&1
 mut_rc=$?
 set -e
 if [ "$mut_rc" = 0 ] || ! grep -q HEAD_WORD "$OUT/mutant_${mutant}.log";then cat "$OUT/mutant_${mutant}.log";exit 1;fi
 printf 'PASS actualHEAD loadedcontrol%s mutant rejected rc=%s\n' "$mutant" "$mut_rc"
done
