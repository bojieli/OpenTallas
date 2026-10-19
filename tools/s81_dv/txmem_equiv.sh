#!/bin/bash
set -eu
O=$(realpath -m "$1");M=${2:-0};mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version
verilator --binary --timing -j4 -Wno-fatal -Wno-WIDTH --top-module tb_s81sl_txmem -GMUT=$M --Mdir "$O/obj" \
 rtl/lib/ot_sram_oldread_wreg.sv rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v \
 rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_txmem.sv > "$O/build.log" 2>&1
"$O/obj/Vtb_s81sl_txmem" > "$O/run.log"
cat "$O/run.log"
grep -q '^TXMEM_EQ PASS' "$O/run.log"
