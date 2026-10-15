#!/bin/bash
set -euo pipefail
mkdir -p "$OUT"
F=physical/ref_tile/sfu_lane_ring3_rt/src
mapfile -t sources < "$DATA/sources.f"
for i in "${!sources[@]}";do sources[$i]="$F/${sources[$i]}";done
sources+=(rtl/hbm_accel/generic/peers/ot_hgi_sfu_fused_glu_lane.sv rtl/test/hbm_accel/generic/tb_hgi_sfu_fused_glu.sv)
"${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}" --binary --timing -O2 -j 4 -CFLAGS -O0 -Wno-fatal -Wno-TIMESCALEMOD --top-module tb_hgi_sfu_fused_glu --Mdir "$OUT/obj" "${sources[@]}" > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_hgi_sfu_fused_glu" +DATA="$DATA" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
set +e
"$OUT/obj/Vtb_hgi_sfu_fused_glu" +DATA="$DATA" +MUTANT > "$OUT/mutant.log" 2>&1
mut_rc=$?
set -e
if [ "$mut_rc" = 0 ] || ! grep -q FUSED_MUTANT_WORD "$OUT/mutant.log";then cat "$OUT/mutant.log";exit 1;fi
printf 'PASS actual second-FMUL operand mutant rejected rc=%s\n' "$mut_rc"
