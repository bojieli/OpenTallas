#!/bin/bash
set -euo pipefail
mkdir -p "$OUT"
F=physical/ref_tile/sfu_lane_ring3_rt/src
mapfile -t names < "$DATA/sources.f"
sources=()
for p in "${names[@]}";do sources+=("$F/$p");done
sources+=("$DEPS/rtl/hbm_accel/generic/peers/static_activation/ot_hbm_sm_aq_static.sv"
 rtl/hbm_accel/generic/peers/ot_hgi_sfu_fused_glu_split.sv rtl/hbm_accel/generic/peers/ot_hgi_sfu_glu_quant_inline.sv
 rtl/test/hbm_accel/generic/tb_hgi_sfu_glu_quant_inline.sv
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v)
for mut in 0 1 2;do
 "${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}" --binary --timing -O2 -j 4 -CFLAGS -O0 -Wno-fatal -Wno-TIMESCALEMOD -GMUT=$mut --top-module tb_hgi_sfu_glu_quant_inline --Mdir "$OUT/obj$mut" "${sources[@]}" > "$OUT/build$mut.log" 2>&1
 set +e
 "$OUT/obj$mut/Vtb_hgi_sfu_glu_quant_inline" +DATA="$DATA" > "$OUT/run$mut.log" 2>&1
 rc=$?
 set -e
 if [ "$mut" = 0 ];then cat "$OUT/run$mut.log";[ "$rc" = 0 ];
 else
  marker=INLINE_XWRITE;if [ "$mut" = 2 ];then marker=INLINE_AQ_WORD;fi
  if [ "$rc" = 0 ] || ! grep -q "$marker" "$OUT/run$mut.log";then cat "$OUT/run$mut.log";exit 1;fi
  printf 'PASS inline actualRTL mutant%s rejected rc=%s marker=%s\n' "$mut" "$rc" "$marker"
 fi
done
