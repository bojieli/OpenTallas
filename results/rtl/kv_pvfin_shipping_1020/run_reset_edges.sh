#!/bin/bash
set -eu
o=$1;mkdir -p "$o"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
s=(rtl/lib/ot_rst_relay_bounded32.sv results/rtl/kv_pvfin_shipping_1020/tb_reset_edges.sv)
sha256sum "${s[@]}" >"$o/source.sha256"
"$v" --binary --timing -j 4 -Wno-fatal --top-module tb_reset_edges --Mdir "$o/obj" "${s[@]}" >"$o/build.log" 2>&1
"$o/obj/Vtb_reset_edges"
