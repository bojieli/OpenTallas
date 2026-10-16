#!/usr/bin/env bash
set -euo pipefail
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$ROOT"
D=rtl/hbm_accel/generic/vm/static
OUT=${1:?output}; mkdir -p "$OUT"
ONLY_SID=${2:-all}
M=physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
for shape in 0:5:2 1:4:2 2:5:3 3:5:3;do
 IFS=: read -r sid rg wg <<< "$shape"
 [[ $ONLY_SID == all || $ONLY_SID == $sid ]] || continue
 for mut in 0 1 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17;do
  stem=q${sid}_m${mut}
  iverilog -g2012 -s tb_hbm_vm_face_literal -Ptb_hbm_vm_face_literal.SID=$sid -Ptb_hbm_vm_face_literal.RG=$rg -Ptb_hbm_vm_face_literal.WG=$wg -Ptb_hbm_vm_face_literal.MUT=$mut -o "$OUT/$stem.vvp" "$D/ot_vms_ce_counter_pipe.sv" "$D/ot_vms_bank_static_face_roots.sv" "$D/ot_vms_bank_face_physical.sv" "$D"/physical/hfd_vms_bank_face_q*.sv "$M" "$D/native_abi_1016/tb_hbm_vm_face_literal.sv" > "$OUT/$stem.compile.log" 2>&1
  set +e; vvp "$OUT/$stem.vvp" > "$OUT/$stem.log" 2>&1; rc=$?; set -e
  if [[ $mut == 0 ]];then test $rc = 0 && grep -q 'VM_LOCAL_LITERAL PASS' "$OUT/$stem.log";else test $rc != 0 && grep -q 'FATAL' "$OUT/$stem.log";fi
  cat "$OUT/$stem.log"
 done
done
echo "VM_FACE_LITERAL_ALL_PASS selected_sid=$ONLY_SID actual8banks24SRAMs; permutation/identity/3macro+12localclockdrop mutants rejected"
