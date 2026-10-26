#!/bin/bash
# Bench of the hardened wrapper ot_hbm_sm_vm_wr_q_t (H-SM 2026-10-16): descriptors through the real host ingress and the
# folded command calendar.  Positive + four mutants (wrong row, late phase, quad strap ignored, calendar one edge late).
set -uo pipefail
cd "$(dirname "$0")/../../../../.."
D=rtl/hbm_accel/generic/vm/static; H=rtl/hbm_accel/host_static_20261015; O=${1:-/tmp/sm_vm_wr_q_t_$$}; mkdir -p $O
SRC="$D/tb_hbm_sm_vm_wr_q_t.sv $D/ot_hbm_sm_vm_wr_q_t.sv $D/ot_hbm_sm_vm_wr_q.sv $D/ot_vms_bank_static.sv $H/ot_static_cmd_target.sv $H/ot_hbm_host_static_ingress.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
rc=0
for m in 0 1 2 3 4; do
  iverilog -g2012 -DMUT=$m -s tb_hbm_sm_vm_wr_q_t -o $O/tb$m $SRC || exit 2
  r=$(vvp -n $O/tb$m | tail -1); echo "$r"
  if [ $m = 0 ]; then [[ $r == *PASS* ]] || rc=1; else [[ $r == *FAIL* ]] || rc=1; fi
done
[ $rc = 0 ] && echo "SM_VM_WR_Q_T BENCH PASS (positive PASS, mutants 1/2/3/4 FAIL)" || echo "SM_VM_WR_Q_T BENCH FAIL"
exit $rc
