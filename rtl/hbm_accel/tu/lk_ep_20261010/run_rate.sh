#!/bin/bash
# [link] 2026-10-10 full link credit-loop rate bench (tb_lk_rate), run in the source root:  run_rate.sh <outdir> [N] [defines...]
set -u; O=$1; N=${2:-6000}; shift $(( $# < 2 ? $# : 2 )); DEFS="$*"
mkdir -p $O; D=rtl/hbm_accel/tu
S="rtl/common/ot_secded.sv rtl/common/ot_secded_dec_dp.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
   $D/link_retry_sram_20261008/ot_hbm_replay_sram_dp.sv $D/link_retry_pipeline_20261009/ot_hbm_link_retry_pipeline_cl.sv
   rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv $D/lk_ep_20261010/ot_crc_par.sv $D/lk_ep_20261010/ot_hbm_lk_ep.sv $D/lk_ep_20261010/ot_lkep_sub.sv
   $D/ot_hcoll_sram_prims.sv rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv $D/ot_hcoll_port.sv $D/lk_ep_20261010/tb_lk_rate.sv"
verilator --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Irtl/common --top-module tb_lk_rate $DEFS \
  --Mdir $O/obj -j ${JOBS:-8} -o sim $S > $O/build.log 2>&1 || { grep -m5 "%Error" $O/build.log; echo "LKRATE FAIL (build)"; exit 1; }
$O/obj/sim +N=$N > $O/sim.log 2>&1
grep -h "LKRATE\|Fatal\|mismatch\|fault" $O/sim.log | head -3
grep -q "LKRATE PASS" $O/sim.log && ! grep -q "LKRATE BELOW" $O/sim.log || { echo "LKRATE FAIL"; exit 1; }
