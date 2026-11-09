#!/usr/bin/env bash
# One compiled SX master reused across16tiles, keeping C++ shape small.
set -euo pipefail
O=$(realpath -m "$1");mkdir -p "$O"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=rtl/dsrom_sys/s81_dv/svc_rs
SRC=(rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/dsrom_sys/s81_glue/ot_s81_rly.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv)
COMMON=(-DOT_SVC_H8 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -I$D --output-split 20000 --output-split-cfuncs 2000 -fno-inline --unroll-count 16 --unroll-limit 131072 -MAKEFLAGS OPT_SLOW=-O0 -CFLAGS -O0)
# Explicitly separate protect-lib and main source compilation.
"$VL" --cc --build -j 4 --protect-lib dsdv_svc_sx_pl --top-module dsdv_svc_sx -GH=8 -Mdir "$O/pl" "${COMMON[@]}" "${SRC[@]}" $D/dsdv_svc_sx_hrow.sv $D/dsdv_svc_sx.sv > "$O/build_lib.log" 2>&1
"$VL" --binary --top-module tb_dsdv_svc_sx -j 4 -Mdir "$O/obj" "${COMMON[@]}" -DSX_PL -DSX_SMALL "${SRC[@]}" "$O/pl/dsdv_svc_sx_pl.sv" $D/test/tb_dsdv_svc_sx.sv "$O/pl/libdsdv_svc_sx_pl.a" > "$O/build_tb.log" 2>&1
for m in 0 1;do "$O/obj/Vtb_dsdv_svc_sx" +seed=1 +order=$m > "$O/run_order$m.log" 2>&1;grep -E '^SX_EDGE|^SX root|^SX_BENCH' "$O/run_order$m.log";done
grep -q '^SX_BENCH PASS$' "$O/run_order0.log"
grep -q '^SX_BENCH FAIL$' "$O/run_order1.log"
