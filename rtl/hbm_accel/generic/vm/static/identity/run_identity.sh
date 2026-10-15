#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
OUT=$(realpath -m "${1:?output}")
mkdir -p "$OUT"
CORE=../ot_vms_bank_static_identity.sv
MACRO=../../../../../../physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
for shape in 0:5:1 1:4:1 2:6:3 3:6:3;do
 IFS=: read -r sid rg wg <<< "$shape"
 for mut in 0 3 4;do
  stem=identity-$sid-$rg-$wg-$mut
  iverilog -g2012 -s tb_hbm_vm_identity -Ptb_hbm_vm_identity.SID=$sid -Ptb_hbm_vm_identity.RG=$rg -Ptb_hbm_vm_identity.WG=$wg -Ptb_hbm_vm_identity.MUT=$mut -o "$OUT/$stem.vvp" ../ot_vms_ce_counter_pipe.sv "$CORE" "$MACRO" tb_hbm_vm_identity.sv > "$OUT/$stem.compile.log" 2>&1
  set +e
  vvp "$OUT/$stem.vvp" > "$OUT/$stem.log" 2>&1
  rc=$?
  set -e
  if [[ $mut == 0 ]];then test $rc = 0;else test $rc != 0;fi
  cat "$OUT/$stem.log"
 done
done
