#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
OUT=$(realpath -m "${1:?output}")
mkdir -p "$OUT"
CORE=../ot_vms_bank_static_wdecode_local_status.sv
MACRO=../../../../../../physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
iverilog -g2012 -s tb_bank_wdecode_local_status -o "$OUT/dynamic.vvp" ../ot_vms_ce_counter_pipe.sv "$CORE" "$MACRO" tb_bank_wdecode_local_status.sv > "$OUT/dynamic.compile.log" 2>&1
vvp "$OUT/dynamic.vvp" > "$OUT/dynamic.log"
cat "$OUT/dynamic.log"
for shape in 6:3 5:1 4:1;do
 rg=${shape%:*};wg=${shape#*:}
 for mut in 0 1 2;do
  stem=groups-$rg-$wg-$mut
  iverilog -g2012 -s tb_hbm_vm_allgroups_wdecode_local_status -Ptb_hbm_vm_allgroups_wdecode_local_status.RG=$rg -Ptb_hbm_vm_allgroups_wdecode_local_status.WG=$wg -Ptb_hbm_vm_allgroups_wdecode_local_status.MUT=$mut -o "$OUT/$stem.vvp" ../ot_vms_ce_counter_pipe.sv "$CORE" "$MACRO" tb_hbm_vm_allgroups_wdecode_local_status.sv > "$OUT/$stem.compile.log" 2>&1
  set +e
  vvp "$OUT/$stem.vvp" > "$OUT/$stem.log" 2>&1
  rc=$?
  set -e
  if [[ $mut == 0 ]];then test $rc = 0;else test $rc != 0;fi
  cat "$OUT/$stem.log"
 done
done
bash ./run_wdecode_local_status_allowners.sh "$OUT"
