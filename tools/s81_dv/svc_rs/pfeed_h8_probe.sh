#!/usr/bin/env bash
# S81U-SVC4: build tb_dsdv_svc_pfeed_h8 (the D = 32 engine share alone) and sweep the static p-feed offset P0 per T:
# prints, per T, the smallest P0 with 0 refused steps (the engine's p-accept bound for the compiled PO rule).
# Usage (repo root): tools/s81_dv/svc_rs/pfeed_probe.sh OUTDIR [T ...]
set -euo pipefail
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
O=$1; shift; TS=${*:-"128 640"}
mkdir -p "$O"
if [ ! -x "$O/obj/Vtb_dsdv_svc_pfeed_h8" ]; then
  "$VL" -DOT_SVC_H8 --binary --top-module tb_dsdv_svc_pfeed_h8 -Mdir "$O/obj" -j 16 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -fno-inline --unroll-count 16 --unroll-limit 131072 -MAKEFLAGS OPT_SLOW=-O0 -CFLAGS -O1 \
    rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv rtl/hdc/v41x/ot_hdc_v41x_kreg.sv \
    rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/v41x/ot_hdc_v41x_attn.sv \
    rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv \
    physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v \
    rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv \
    rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/v41x/ot_dsrom_su_f12.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv \
    rtl/dsrom_sys/s81_dv/svc_rs/test/tb_dsdv_svc_pfeed_h8.sv > "$O/build.log" 2>&1 || { tail -30 "$O/build.log"; exit 1; }
fi
# Late static feed isolates sustained loader/issue throughput from QK startup.
# Stride1 is the measured failing control at T640; stride2 is the H8 candidate.
for T in $TS; do
 for stride in 1 2; do
  "$O/obj/Vtb_dsdv_svc_pfeed_h8" +t=$T +p0=${P0:-800} +pstride=$stride +trace=1 > "$O/t${T}_stride${stride}.log" 2>&1
  grep '^PFEED' "$O/t${T}_stride${stride}.log"
  grep '^PVEDGE' "$O/t${T}_stride${stride}.log" || true
 done
done
