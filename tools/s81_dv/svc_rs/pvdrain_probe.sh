#!/usr/bin/env bash
# SVC-PV 2026-10-18: build tb_dsdv_svc_pvdrain (D = 32 engine share + dsdv_svc_att's exact owner P.V drain) and sweep the
# drain-to-feed distance W = DS - P0 per T, with and without the pv_cr return: prints per T the window of W with
# f15 = f19 = 0 (the static PO / PVO rule the compiler must honour per owner).
# Usage (repo root): PVC=8 tools/s81_dv/svc_rs/pvdrain_probe.sh OUTDIR P0X "T ..." "W ..."
#   P0 = ceil(5 T / 4) + P0X (the p feed after the last score, as the compiled PO); PVC = PV_CRED / pvq depth (default 4)
set -euo pipefail
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
O=$1; P0X=$2; TS=$3; WS=$4; PVC=${PVC:-4}
mkdir -p "$O"
if [ ! -x "$O/obj/Vtb_dsdv_svc_pvdrain" ]; then
  # -GPVC baked in: one OUTDIR per PVC
  "$VL" --binary --top-module tb_dsdv_svc_pvdrain -GPVC=$PVC -Mdir "$O/obj" -j ${JOBS:-8} -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -fno-inline --unroll-count 16 --unroll-limit 131072 -MAKEFLAGS OPT_SLOW=-O0 -CFLAGS -O1 \
    rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv rtl/hdc/v41x/ot_hdc_v41x_kreg.sv \
    rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/v41x/ot_hdc_v41x_attn.sv \
    rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv \
    physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v \
    rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv \
    rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv \
    rtl/dsrom_sys/s81_dv/svc_rs/test/tb_dsdv_svc_pvdrain.sv > "$O/build.log" 2>&1 || { tail -30 "$O/build.log"; exit 1; }
fi
for T in $TS; do
  P0=$(( (5 * T + 3) / 4 + P0X ))
  for W in $WS; do
    for C in "" "+nocr"; do
      "$O/obj/Vtb_dsdv_svc_pvdrain" +t=$T +p0=$P0 +ds=$((P0 + W)) +rcend=$((P0 + W + 400)) $C > "$O/run_t${T}_w${W}${C:+_nocr}.log"
      echo "W=$W $(grep -h '^PVDRAIN' "$O/run_t${T}_w${W}${C:+_nocr}.log")"
    done
  done
done
