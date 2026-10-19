#!/usr/bin/env bash
# S81U-SVC4: build tb_dsdv_svc_pfeed (the D = 32 engine share alone) and sweep the static p-feed offset P0 per T:
# prints, per T, the smallest P0 with 0 refused steps (the engine's p-accept bound for the compiled PO rule).
# Usage (repo root): tools/s81_dv/svc_rs/pfeed_probe.sh OUTDIR [T ...]
set -euo pipefail
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
O=$1; shift; TS=${*:-"1 2 3 4 31 32 33 46 64 100 128 300 428 512 640"}
mkdir -p "$O"
if [ ! -x "$O/obj/Vtb_dsdv_svc_pfeed" ]; then
  "$VL" --binary --top-module tb_dsdv_svc_pfeed -Mdir "$O/obj" -j 16 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -fno-inline --unroll-count 16 --unroll-limit 131072 -MAKEFLAGS OPT_SLOW=-O0 -CFLAGS -O1 \
    rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv rtl/hdc/v41x/ot_hdc_v41x_kreg.sv \
    rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/v41x/ot_hdc_v41x_attn.sv \
    rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv \
    physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v \
    rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv \
    rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv \
    rtl/dsrom_sys/s81_dv/svc_rs/test/tb_dsdv_svc_pfeed.sv > "$O/build.log" 2>&1 || { tail -30 "$O/build.log"; exit 1; }
fi
for T in $TS; do
  best=-1
  for P0 in $(seq 0 1 900); do
    l=$("$O/obj/Vtb_dsdv_svc_pfeed" +t=$T +p0=$P0 | grep '^PFEED')
    if echo "$l" | grep -q ' refused=0 '; then best=$P0; echo "MIN $l"; break; fi
  done
  [ $best -ge 0 ] || echo "MIN T=$T none"
  "$O/obj/Vtb_dsdv_svc_pfeed" +t=$T +p0=$((best + 200)) | grep '^PFEED' | sed 's/^/LATE /'
done
