#!/usr/bin/env bash
set -euo pipefail
R=$(git rev-parse --show-toplevel);O=${1:?output directory}
D=$R/rtl/dsrom_sys/s81_dv/svc_rs/rowx
P=$R/physical/asap7_memory_macros
VL=${VL:-$HOME/.local/opentallas-tools/bin/verilator}
mkdir -p "$O"
"$VL" --binary --timing -j "${J:-4}" -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD \
 --top-module tb_rowx_sram_miter -Mdir "$O/obj" \
 "$D/dsdv_rowx_lc.sv" "$D/dsdv_rowx_lc_sram.sv" "$D/dsdv_rowx_rp.sv" "$D/dsdv_rowx_rp_sram.sv" \
 "$P/ot_sram_1r1w_32x512_m1/ot_sram_1r1w_32x512_m1.v" \
 "$P/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v" \
 "$D/test/tb_rowx_sram_miter.sv" > "$O/build.log" 2>&1
"$O/obj/Vtb_rowx_sram_miter" | tee "$O/run.log"
