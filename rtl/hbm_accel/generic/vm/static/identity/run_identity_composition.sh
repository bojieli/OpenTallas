#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
OUT=$(realpath -m "${1:?output}")
mkdir -p "$OUT"
ONLY_SID=${2:-all}
MACRO=../../../../../../physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
for shape in 0:5:1 1:4:1 2:6:3 3:6:3;do
 IFS=: read -r sid rg wg <<< "$shape"
 if [[ $ONLY_SID != all && $sid != "$ONLY_SID" ]];then continue;fi
 for mut in 0 1;do
  stem=composition-$sid-$rg-$wg-$mut
  iverilog -g2012 -s tb_hbm_vm_identity_slice -Ptb_hbm_vm_identity_slice.SID=$sid -Ptb_hbm_vm_identity_slice.RG=$rg -Ptb_hbm_vm_identity_slice.WG=$wg -Ptb_hbm_vm_identity_slice.MUT=$mut -o "$OUT/$stem.vvp" ../ot_vms_ce_counter_pipe.sv ../ot_vms_bank_static_identity.sv ../physical/hfd_vms_bank_identity_q*_b*.sv ../hfd_hgi_vms_identity.sv ../ot_vms_slice_static_identity.sv ../ot_vms_hub_static.sv ../ot_vms_rstop_static.sv ../ot_vms_rcl_static.sv ../ot_vms_status_static.sv "$MACRO" tb_hbm_vm_identity_slice.sv > "$OUT/$stem.compile.log" 2>&1
  set +e
  vvp "$OUT/$stem.vvp" > "$OUT/$stem.log" 2>&1
  rc=$?
  set -e
  if [[ $mut == 0 ]];then test $rc = 0;else test $rc != 0;fi
  cat "$OUT/$stem.log"
 done
done
