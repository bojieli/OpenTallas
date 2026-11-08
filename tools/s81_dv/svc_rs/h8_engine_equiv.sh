#!/usr/bin/env bash
# S81U-SVC4: build tb_svc_h8_engine (the D = 32 engine share alone) and sweep the static p-feed offset P0 per T:
# prints, per T, the smallest P0 with 0 refused steps (the engine's p-accept bound for the compiled PO rule).
# Usage (repo root): tools/s81_dv/svc_rs/pfeed_probe.sh OUTDIR [T ...]
set -euo pipefail
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
O=$1; shift; TS=${*:-"1 2 3 4 31 32 33 46 64 100 128 300 428 512 640"}
mkdir -p "$O"
if [ ! -x "$O/obj/Vtb_svc_h8_engine" ]; then
  "$VL" --binary --top-module tb_svc_h8_engine -Mdir "$O/obj" -j 16 --output-split 20000 --output-split-cfuncs 2000 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -fno-inline --unroll-count 16 --unroll-limit 131072 -MAKEFLAGS OPT_SLOW=-O0 -CFLAGS -O1 \
    rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv rtl/hdc/v41x/ot_hdc_v41x_kreg.sv \
    rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/v41x/ot_hdc_v41x_attn.sv \
    rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv \
    physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v \
    rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv \
    rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/v41x/ot_dsrom_su_f12.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv \
    rtl/dsrom_sys/s81_dv/svc_rs/test/tb_svc_h8_engine.sv > "$O/build.log" 2>&1 || { tail -30 "$O/build.log"; exit 1; }
fi
for m in 0 1 2 3; do
 "$O/obj/Vtb_svc_h8_engine" +mut=$m > "$O/run_mut$m.log" 2>&1
 grep '^H8_ENGINE' "$O/run_mut$m.log"
done
grep -q '^H8_ENGINE PASS$' "$O/run_mut0.log"
for m in 1 2 3;do grep -q '^H8_ENGINE FAIL$' "$O/run_mut$m.log";done
