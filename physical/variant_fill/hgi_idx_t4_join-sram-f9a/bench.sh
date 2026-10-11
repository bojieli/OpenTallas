#!/bin/bash
# FILL-9 t4_join SRAM-queue variant gate: tb_hfd_idx_t4_join on MEM=1 (ot_fifo_sram_fwft on ot_sram_1r1w_128x256_m1_r2c2).
# usage: bench.sh OUT MODE   MODE = base | MUT_SWAP | MUT_DROP_CREDIT | flop (MEM=0 regression)
set -uo pipefail
R=$(cd "$(dirname "$0")/../../.." && pwd)
OUT=$1; MODE=$2; mkdir -p "$OUT/$MODE"; cd "$OUT/$MODE"
MEM=1; DEF=""; [ "$MODE" = flop ] && MEM=0; case $MODE in MUT_*) DEF="-D$MODE";; esac
iverilog -g2012 -o sim -P tb_hfd_idx_t4_join.MEM=$MEM $DEF -s tb_hfd_idx_t4_join \
  $R/physical/hbm_accel_die_views/index/rtl/hfd_idx_t4_join.sv $R/physical/hbm_accel_die_views/index/rtl/hfd_idx_lib.sv \
  $R/rtl/link/ot_fifo_sram_fwft.sv $R/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
  $R/physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v \
  $R/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v \
  $R/physical/hbm_accel_die_views/index/tb/tb_hfd_idx_t4_join.sv > build.log 2>&1 || { echo BUILD_FAILED; cat build.log; exit 2; }
vvp -n sim > sim.log 2>&1; rc=$?
cat sim.log | tail -3
grep -q "^PASS atomic T4 join" sim.log && [ $rc = 0 ] && { echo "T4J_${MODE}_PASS"; exit 0; }
echo "T4J_${MODE}_FAIL"; exit 1
