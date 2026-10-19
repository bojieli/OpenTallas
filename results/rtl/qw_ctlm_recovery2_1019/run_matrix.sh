#!/bin/bash
set +e
cd /srv/opentallas-scratch/claude/qw-ctlm-recovery2-1019
verilator --binary --top-module tb_ring_phase -Wno-fatal -j 2 tb_ring_phase.sv src/rtl/common/landed_parent/ot_pl_land.sv -Mdir ring_obj > ring_build.log 2>&1 || exit 1
for p in -6000 -4000 -2000 0 2000 4000 6000; do
 for r in 100000 102000; do
  ./ring_obj/Vtb_ring_phase +phase=$p +release=$r > ring_${p}_${r}.log 2>&1
 done
done
for s in 1 17 131; do
 ./reference4_initial/obj0/Vtb_qfd_tt_ctlm_dv_lpf_lp +verilator+rand+reset+2 +verilator+seed+$s > reference4_initial/random_seed$s.log 2>&1
 ./first20_out/obj0/Vtb_qfd_tt_ctlm_dv_lpf_lp +verilator+rand+reset+2 +verilator+seed+$s > first20_out/random_seed$s.log 2>&1
done
