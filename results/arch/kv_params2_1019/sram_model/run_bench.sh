#!/bin/bash
# usage: run_bench.sh SRC_ROOT OUT MUT   (Verilator 5.050)
set -u
S=$1; O=$2; M=$3; mkdir -p $O; H=$(cd "$(dirname "$0")" && pwd)
sed 's/module ot_sram_1r1w_32x128_m1 (/module ot_sram_formal_dut (/' $H/ot_sram_1r1w_32x128_m1_formal.v > $O/dut.v
[ "$M" = 1 ] && sed -i 's/(arr\[w_addr_in\] & ~w_mask_in) | (wd_in & w_mask_in)/wd_in/' $O/dut.v
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version
$V --binary -Wno-fatal -Wno-lint -Wno-style --timing -DOT_MEM_NO_INIT --top-module tb -Mdir $O/obj $H/tb_sram_model.sv $O/dut.v \
  $S/physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v > $O/build.log 2>&1 || { tail -20 $O/build.log; exit 2; }
$O/obj/Vtb
