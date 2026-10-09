#!/bin/bash
# Full-width output FIFO differential proof. The original shift-buffer implementation
# is the cycle oracle; the mutant offsets every ring write by one slot.
set -eu
mode=$1
out=$2
mkdir -p "$out"
define=()
if [[ $mode == mut ]]; then define=(-DOT_S81PH_COLT_MUT_RING); fi
iverilog -g2012 "${define[@]}" -s tb_ring -o "$out/bench" \
 rtl/dsrom_sys/s81_ph/test/tb_colt_ring.sv \
 rtl/dsrom_sys/s81_ph/ot_s81ph_col_tile.sv \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
vvp "$out/bench"
