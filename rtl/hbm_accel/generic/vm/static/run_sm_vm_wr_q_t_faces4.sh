#!/bin/bash
# Bench of the hardened wrapper ot_hbm_sm_vm_wr_q_t_faces4 (H-SM 2026-10-16): descriptors through the real host ingress and the
# folded command calendar.  Positive + four mutants (wrong row, late phase, quad strap ignored, calendar one edge late).
set -uo pipefail
cd "$(dirname "$0")/../../../../.."
D=rtl/hbm_accel/generic/vm/static; H=rtl/hbm_accel/host_static_20261015; O=${1:-/tmp/sm_vm_wr_q_t_$$}; mkdir -p $O
SRC="$D/tb_hbm_sm_vm_wr_q_t_faces4.sv $D/ot_hbm_sm_vm_wr_q_t_faces4.sv $D/ot_hbm_sm_vm_wr_q_faces4.sv $D/ot_vms_bank_static.sv $H/ot_static_cmd_target.sv $H/ot_hbm_host_static_ingress.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
rc=0
# Icarus can print a $finish location after the testbench verdict. Preserve the
# full transcript and accept exactly one explicit verdict, with a clean exit.
run_case() {
  local binary=$1 expected=$2 log="$1.log" result
  if ! vvp -n "$binary" > "$log" 2>&1; then
    cat "$log"
    return 1
  fi
  cat "$log"
  result=$(grep -E '^TB_HBM_SM_VM_WR_Q_T (PASS MUT=[0-4]|FAIL MUT=[0-4] mismatches[+]faults=[0-9]+)$' "$log")
  [[ $(printf '%s\n' "$result" | wc -l) = 1 ]] || return 1
  [[ "$result" == "TB_HBM_SM_VM_WR_Q_T $expected MUT="* ]]
}
for m in 0 1 2 3 4; do
  iverilog -g2012 -DMUT=$m -s tb_hbm_sm_vm_wr_q_t_faces4 -o $O/tb$m $SRC || exit 2
  if [ $m = 0 ]; then expected=PASS; else expected=FAIL; fi
  run_case "$O/tb$m" "$expected" || rc=1
done
# nat2 VM banks (+1 input edge on every bank input): VM_LAT=1 positive PASS, NAT2_MUT=1 (wq late, slot not) FAIL
for v in "1 0" "1 1"; do set -- $v
  iverilog -g2012 -DMUT=0 -DVM_LAT=$1 -DNAT2_MUT=$2 -s tb_hbm_sm_vm_wr_q_t_faces4 -o $O/tbn$1$2 $SRC || exit 2
  echo "VM_LAT=$1 NAT2_MUT=$2"
  if [ $2 = 0 ]; then expected=PASS; else expected=FAIL; fi
  run_case "$O/tbn$1$2" "$expected" || rc=1
done
# Each upper half has a genuine independent clock. Dropping either one must
# lose real memory results, so a missing clock cannot pass a source-only check.
for c in 1 2;do
  iverilog -g2012 -DMUT=0 -DFACE_CLOCK_MUT=$c -s tb_hbm_sm_vm_wr_q_t_faces4 -o $O/tbc$c $SRC || exit 2
  echo "FACE_CLOCK_MUT=$c"
  run_case "$O/tbc$c" FAIL || rc=1
done
[ $rc = 0 ] && echo "SM_VM_WR_Q_T BENCH PASS (positive PASS, mutants 1/2/3/4 FAIL)" || echo "SM_VM_WR_Q_T BENCH FAIL"
exit $rc
