#!/bin/bash
# fe-push-hgi-1010 t4_join FE=1 gate: tb_hfd_idx_t4_join (342 beats under tap skew + 500-cycle downstream credit stall).
# usage: bench.sh OUT MODE
#   base      MEM=1 FE=1 (the routed form)          fe_flop  MEM=0 FE=1
#   legacy    MEM=1 FE=0 (pre-FE SRAM form)          flop     MEM=0 FE=0
#   MUT_SWAP / MUT_DROP_CREDIT / MUT_FE_CNZ           mutants on MEM=1 FE=1 (must FAIL)
set -uo pipefail
R=$(cd "$(dirname "$0")/../../.." && pwd)
OUT=$1; MODE=$2; mkdir -p "$OUT/$MODE"; cd "$OUT/$MODE"
MEM=1; FE=1; DEF=""
case $MODE in fe_flop) MEM=0;; legacy) FE=0;; flop) MEM=0; FE=0;; MUT_*) DEF="-D$MODE";; esac
iverilog -g2012 -o sim -P tb_hfd_idx_t4_join.MEM=$MEM -P tb_hfd_idx_t4_join.FE=$FE $DEF -s tb_hfd_idx_t4_join \
  $R/physical/hbm_accel_die_views/index/rtl/hfd_idx_t4_join.sv $R/physical/hbm_accel_die_views/index/rtl/hfd_idx_lib.sv \
  $R/rtl/lib/ot_rst_relay.sv $R/rtl/link/ot_fifo_sram_fwft.sv \
  $R/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
  $R/physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v \
  $R/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v \
  $R/physical/hbm_accel_die_views/index/tb/tb_hfd_idx_t4_join.sv > build.log 2>&1 || { echo BUILD_FAILED; cat build.log; exit 2; }
vvp -n sim > sim.log 2>&1; rc=$?
tail -3 sim.log
grep -q "^PASS atomic T4 join" sim.log && [ $rc = 0 ] && { echo "T4J_${MODE}_PASS"; exit 0; }
echo "T4J_${MODE}_FAIL"; exit 1
