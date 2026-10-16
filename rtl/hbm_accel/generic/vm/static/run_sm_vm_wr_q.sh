#!/bin/bash
# Bench of ot_hbm_sm_vm_wr_q (H-NETLIST/smvm 0030): positive + three mutants (wrong row, late phase, quad strap ignored) that must FAIL.
set -uo pipefail
cd "$(dirname "$0")/../../../../.."
D=rtl/hbm_accel/generic/vm/static; O=${1:-/tmp/sm_vm_wr_q_$$}; mkdir -p $O
SRC="$D/tb_hbm_sm_vm_wr_q.sv $D/ot_hbm_sm_vm_wr_q.sv $D/ot_vms_bank_static.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v"
rc=0
for m in 0 1 2 3; do
  iverilog -g2012 -DMUT=$m -o $O/tb$m $SRC || exit 2
  r=$(vvp -n $O/tb$m | tail -1); echo "$r"
  if [ $m = 0 ]; then [[ $r == *PASS* ]] || rc=1; else [[ $r == *FAIL* ]] || rc=1; fi
done
[ $rc = 0 ] && echo "SM_VM_WR_Q BENCH PASS (positive PASS, mutants 1/2/3 FAIL)" || echo "SM_VM_WR_Q BENCH FAIL"
exit $rc
