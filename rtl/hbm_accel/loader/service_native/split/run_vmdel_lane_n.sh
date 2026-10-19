#!/bin/bash
# HBM-B-RTL1 2026-10-17: bench of ot_hbm_svc_vmdel_lane_n (plan (b) NPC 2 lane) -- lockstep vs the d4f lane + NPC 4 copy
# equivalence.  MUT 0 PASS; MUT 1 (slot swap) / 2 (missing fill) / 3 (NPC 4 copy fill drop) FAIL.
set -uo pipefail
cd "$(dirname "$0")/../../../../.."
D=rtl/hbm_accel/loader/service_native/split; O=${1:-/tmp/vmdel_n_$$}; mkdir -p $O; rc=0
for m in 0 1 2 3; do
  iverilog -g2012 -DMUT=$m -s tb_hbm_svc_vmdel_lane_n_lockstep -o $O/t$m $D/tb_hbm_svc_vmdel_lane_n_lockstep.sv $D/ot_hbm_svc_vmdel_lane_n.sv \
    $D/ot_hbm_svc_static_vm_delivery_split.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v || exit 2
  vvp -n $O/t$m > $O/t$m.log 2>&1; grep -E "^(NPC4 equivalence edges|d4f beats|VMDEL_N_LOCKSTEP)" $O/t$m.log
  grep -qx "VMDEL_N_LOCKSTEP $([ $m = 0 ] && echo PASS || echo FAIL) MUT=$m.*" $O/t$m.log || grep -q "^VMDEL_N_LOCKSTEP $([ $m = 0 ] && echo PASS || echo FAIL) MUT=$m" $O/t$m.log || { echo "MUT=$m UNEXPECTED"; rc=1; }
done
[ $rc = 0 ] && echo "VMDEL_N BENCH PASS (NPC2 lockstep + NPC4 equivalence PASS; mutants 1/2/3 FAIL)" || echo "VMDEL_N BENCH FAIL"
exit $rc
