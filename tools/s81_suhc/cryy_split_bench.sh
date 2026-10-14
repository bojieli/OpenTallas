#!/bin/bash
# Lockstep bench of the y slice leaves: cryy_split_bench.sh OUTDIR [MUT] [C]   (MUT 0 exact, 1 / 2 negative controls)
# prints "CRYY_SPLIT PASS" / "CRYY_SPLIT FAIL" (rtl/dsrom_sys/s81_suhc/test/tb_s81_hc_cryy_split.sv)
set -e
O=$1; M=${2:-0}; C=${3:-0}; R=$(cd "$(dirname "$0")/../.." && pwd)
[ -x "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" ] && export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
mkdir -p "$O"
D=""; [ "$M" != 0 ] && D="-DOT_S81_HC_CRYYS_MUT$M"
verilator --binary --timing -O2 -Wno-fatal -Wno-WIDTH -Wno-MODMISSING --top-module tb_s81_hc_cryy_split -GC=$C $D -Mdir "$O/obj_m${M}_c$C" -j 4 \
    "$R/rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_crooty.sv" "$R/rtl/link/ot_fifo_sram_fwft.sv" \
    "$R/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v" \
    "$R/rtl/dsrom_sys/s81_suhc/test/tb_s81_hc_cryy_split.sv" > "$O/build_m${M}_c$C.log" 2>&1 || { tail -30 "$O/build_m${M}_c$C.log"; exit 2; }
"$O/obj_m${M}_c$C/Vtb_s81_hc_cryy_split"
