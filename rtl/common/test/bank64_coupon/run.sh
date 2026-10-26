#!/bin/bash
set -u
R=$(cd "$(dirname "$0")/../../../.." && pwd)
O=$1;M=${2:-0};mkdir -p "$O";O=$(realpath "$O")
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version
verilator --cc --exe --build -j 4 -Wno-fatal -Wno-WIDTH -DMUT=$M -DLOCAL_HIT=${LOCAL_HIT:-1} --top-module tb_credit_bank64_coupon --Mdir "$O/obj" \
 "$R/rtl/common/ot_link_credit.sv" "$R/rtl/common/ot_link_credit_rx_bank64_coupon.sv" "$R/rtl/lib/ot_sram_showahead_bank64_coupon.sv" \
 "$R/physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v" \
 "$R/rtl/common/test/bank64_coupon/tb_credit_bank64_coupon.sv" "$R/rtl/common/test/bank64_coupon/tb_credit_bank64_coupon.cpp" -CFLAGS -O1 > "$O/build.log" 2>&1 || { tail -n8 "$O/build.log";exit 2; }
"$O/obj/Vtb_credit_bank64_coupon" | tee "$O/run.log"
grep -q '^CREDIT_SRAM_EQ PASS' "$O/run.log"
