#!/usr/bin/env bash
set -euo pipefail
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$ROOT"
D=rtl/hbm_accel/generic/vm/static
OUT=${1:?output}; mkdir -p "$OUT"
M=physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
for shape in 0:5:2 1:4:2 2:5:3 3:4:2;do
 IFS=: read -r sid rg wg <<< "$shape"
 for mut in 0 1 3 4;do
  stem=q${sid}_m${mut}
  iverilog -g2012 -s tb_hbm_vm_native_abi -Ptb_hbm_vm_native_abi.SID=$sid -Ptb_hbm_vm_native_abi.RG=$rg -Ptb_hbm_vm_native_abi.WG=$wg -Ptb_hbm_vm_native_abi.MUT=$mut -o "$OUT/$stem.vvp" "$D/ot_vms_ce_counter_pipe.sv" "$D/ot_vms_bank_static_strap.sv" "$D/ot_vms_bank_native_physical.sv" "$D"/physical/hfd_vms_bank_native_q*.sv "$M" "$D/native_abi_1016/tb_hbm_vm_native_abi.sv" > "$OUT/$stem.compile.log" 2>&1
  set +e; vvp "$OUT/$stem.vvp" > "$OUT/$stem.log" 2>&1; rc=$?; set -e
  if [[ $mut == 0 ]];then test $rc = 0 && grep -q 'VM_NATIVE_ABI PASS' "$OUT/$stem.log";else test $rc != 0 && grep -q 'FATAL' "$OUT/$stem.log";fi
  cat "$OUT/$stem.log"
 done
done
echo 'VM_NATIVE_ABI_ALL_PASS 4 actual shapes x8 banks x24SRAMs; read permutation/bank identity/slice identity mutants rejected'
