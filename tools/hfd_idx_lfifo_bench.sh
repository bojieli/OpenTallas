#!/bin/bash
# el1011-hbm-idx: selector landing FIFO swap equivalence (flop hfd_idx_fifo vs SRAM ot_fifo_sram_fwft); usage: <out> [+MUT]
set -u
O=$1; P=${2:-}; mkdir -p $O
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x $VL ] || VL=verilator
M=physical/asap7_memory_macros
if [ ! -x $O/obj/Vtb_hfd_idx_lfifo_eq ]; then
 $VL --binary --timing -O2 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-TIMESCALEMOD --top-module tb_hfd_idx_lfifo_eq -Mdir $O/obj \
  physical/hbm_accel_die_views/index/tb/tb_hfd_idx_lfifo_eq.sv physical/hbm_accel_die_views/index/rtl/hfd_idx_lib.sv rtl/link/ot_fifo_sram_fwft.sv \
  $M/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v $M/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v \
  $M/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v -j 8 > $O/build.log 2>&1 || { tail -5 $O/build.log; echo HFD_IDX_LFIFO_EQ BUILD_FAIL; exit 2; }
fi
$O/obj/Vtb_hfd_idx_lfifo_eq $P > $O/run$P.log 2>&1; grep -h "summary\|HFD_IDX_LFIFO_EQ" $O/run$P.log
grep -q "HFD_IDX_LFIFO_EQ PASS" $O/run$P.log
