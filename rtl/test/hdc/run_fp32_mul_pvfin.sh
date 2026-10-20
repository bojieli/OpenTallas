#!/bin/bash
set -eu
O=$1
mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
S=(rtl/test/hdc/tb_fp32_mul_pvfin.sv rtl/hdc/ot_hdc_fp32_mul_lat_pvfin.sv rtl/hdc/ot_hdc_fp32_mul_lat_ncr.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/lib/ot_rst_relay_bounded32.sv)
sha256sum "${S[@]}" "$0" > "$O/source.sha256"
"$V" --binary --timing -j 4 -O2 --x-initial unique --x-assign unique -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_fp32_mul_pvfin --Mdir "$O/obj" "${S[@]}" > "$O/build.log" 2>&1
for s in 1 29 53; do "$O/obj/Vtb_fp32_mul_pvfin" +verilator+rand+reset+2 +verilator+seed+$s +SEED=$s; done
