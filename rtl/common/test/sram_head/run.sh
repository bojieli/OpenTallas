#!/bin/bash
set -u
R=$(cd "$(dirname "$0")/../../../.." && pwd)
O=$1;M=${2:-0};mkdir -p "$O";O=$(realpath "$O")
verilator --cc --exe --build -j 4 -Wno-fatal -Wno-WIDTH -DMUT=$M --top-module tb_credit_sram --Mdir "$O/obj" \
 "$R/rtl/common/ot_link_credit.sv" "$R/rtl/common/ot_link_credit_rx_sram.sv" "$R/rtl/lib/ot_sram_showahead_1r1w.sv" \
 "$R/physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v" \
 "$R/rtl/common/test/sram_head/tb_credit_sram.sv" "$R/rtl/common/test/sram_head/tb_credit_sram.cpp" -CFLAGS -O1 > "$O/build.log" 2>&1 || { tail -n8 "$O/build.log";exit 2; }
"$O/obj/Vtb_credit_sram" | tee "$O/run.log"
grep -q '^CREDIT_SRAM_EQ PASS' "$O/run.log"
