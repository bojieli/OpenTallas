#!/bin/bash
# [link] 2026-10-10 hfd_lk_ep bench (run in the source root):  run_bench.sh <outdir> [NS] [N] [ERRP] [SEED] [extra defines...]
# Prints LKEP_BENCH PASS / FAIL.  Verilator (iverilog fallback with SIM=iverilog).
set -u; O=$1; NS=${2:-3}; N=${3:-3000}; E=${4:-0}; SD=${5:-1}; shift $(( $# < 5 ? $# : 5 )); DEFS="$*"
mkdir -p $O; D=rtl/hbm_accel/tu
S="rtl/common/ot_secded.sv rtl/common/ot_secded_dec_dp.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
   $D/link_retry_sram_20261008/ot_hbm_replay_sram_dp.sv $D/link_retry_pipeline_20261009/ot_hbm_link_retry_pipeline_cl.sv
   rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv $D/lk_ep_20261010/ot_crc_par.sv $D/lk_ep_20261010/ot_hbm_lk_ep.sv $D/lk_ep_20261010/ot_lkep_sub.sv $D/lk_ep_20261010/tb_hfd_lk_ep.sv"
if [ "${SIM:-verilator}" = verilator ]; then
  verilator --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Irtl/common --top-module tb_hfd_lk_ep -GNS=$NS $DEFS \
    --Mdir $O/obj -j ${JOBS:-8} -o sim $S > $O/build.log 2>&1 || { tail -20 $O/build.log; echo "LKEP_BENCH FAIL (build)"; exit 1; }
  $O/obj/sim +N=$N +ERRP=$E +SEED=$SD +MAXCYC=${MAXCYC:-0} +LOSTRP=${LOSTRP:-0} > $O/sim.log 2>&1
else
  iverilog -g2012 -Irtl/common -s tb_hfd_lk_ep -Ptb_hfd_lk_ep.NS=$NS $DEFS -o $O/sim $S > $O/build.log 2>&1 || { tail -20 $O/build.log; echo "LKEP_BENCH FAIL (build)"; exit 1; }
  vvp -n $O/sim +N=$N +ERRP=$E +SEED=$SD +MAXCYC=${MAXCYC:-0} +LOSTRP=${LOSTRP:-0} > $O/sim.log 2>&1
fi
grep -h "LKEP_BENCH\|Fatal\|mismatch" $O/sim.log | head -3
grep -q "LKEP_BENCH PASS" $O/sim.log || { echo "LKEP_BENCH FAIL"; exit 1; }
