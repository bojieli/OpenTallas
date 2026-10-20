#!/bin/bash
set -eu
O=$1;mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
S=(rtl/hdc/ot_qkd_pvfin_calendar_value.sv rtl/test/qwen_split/tb_pvfin_calendar.sv)
sha256sum "${S[@]}" "$0" > "$O/source.sha256"
"$V" --binary --timing -j 4 -O2 -Wno-fatal --top-module tb_pvfin_calendar --Mdir "$O/obj" "${S[@]}" > "$O/build.log" 2>&1
"$O/obj/Vtb_pvfin_calendar"
