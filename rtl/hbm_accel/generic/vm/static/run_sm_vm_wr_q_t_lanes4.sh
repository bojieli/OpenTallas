#!/bin/bash
# HBM-B-RTL1 2026-10-17: lockstep bench of the plan (b) quadrant writers ot_hbm_sm_vm_wr_q_t_lanes4 (lbase 0 / 1) against
# the d4f stack writer ot_hbm_sm_vm_wr_q_t_lanes (tb_hbm_sm_vm_wr_q_t_lanes4_lockstep.sv).  Positive must PASS; mutants of
# the E writer 1 (row) / 2 (phase) / 3 (quad strap) / 4 (calendar late) / 6 (bank base) must FAIL.
set -uo pipefail
cd "$(dirname "$0")/../../../../.."
D=rtl/hbm_accel/generic/vm/static; H=rtl/hbm_accel/host_static_20261015; O=${1:-/tmp/wrq4_$$}; mkdir -p $O
SRC="$D/tb_hbm_sm_vm_wr_q_t_lanes4_lockstep.sv $D/ot_hbm_sm_vm_wr_q_t_lanes4.sv $D/ot_hbm_sm_vm_wr_q_lanes_n.sv $D/ot_hbm_sm_vm_wr_q_t_lanes.sv $D/ot_hbm_sm_vm_wr_q_lanes.sv $H/ot_static_cmd_target.sv $H/ot_hbm_host_static_ingress.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
rc=0
for m in 0 1 2 3 4 6; do
  iverilog -g2012 -DMUT=$m -s tb_hbm_sm_vm_wr_q_t_lanes4_lockstep -o $O/tb$m $SRC || exit 2
  vvp -n $O/tb$m > $O/tb$m.log 2>&1; grep -E "^(lockstep lane-edges|TB_WRQ4_LOCKSTEP)" $O/tb$m.log
  r=$(grep -cE "^TB_WRQ4_LOCKSTEP $([ $m = 0 ] && echo PASS || echo FAIL) MUT=$m" $O/tb$m.log)
  [ "$r" = 1 ] || { echo "case MUT=$m UNEXPECTED"; rc=1; }
done
[ $rc = 0 ] && echo "WRQ4_LOCKSTEP BENCH PASS (positive PASS; E-writer mutants 1/2/3/4/6 FAIL)" || echo "WRQ4_LOCKSTEP BENCH FAIL"
exit $rc
