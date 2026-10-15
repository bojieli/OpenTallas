#!/bin/bash
set -euo pipefail
mkdir -p "$OUT"
F=physical/ref_tile/sfu_lane_ring3_rt/src
mapfile -t sources < "$DATA/sources.f"
for i in "${!sources[@]}";do sources[$i]="$F/${sources[$i]}";done
sources+=(rtl/hbm_accel/generic/peers/ot_hgi_sfu_fused_glu_lane.sv rtl/hbm_accel/generic/peers/ot_hgi_sfu_fused_glu_store.sv rtl/hbm_accel/generic/peers/ot_hgi_sfu_fused_glu_array.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
"${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}" --lint-only --timing -Wno-fatal -Wno-TIMESCALEMOD --top-module ot_hgi_sfu_fused_glu_array "${sources[@]}" > "$OUT/lint.log" 2>&1
if grep -Eq '%(Error|Warning-(LATCH|MULTIDRIVEN|UNOPTFLAT))' "$OUT/lint.log";then cat "$OUT/lint.log";exit 1;fi
printf 'PASS actual256lane96SRAM array source elaboration; no physical/rate claim\n'
