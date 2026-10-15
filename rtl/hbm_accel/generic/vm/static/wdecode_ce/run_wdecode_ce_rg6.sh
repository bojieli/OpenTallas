#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
OUT=$(realpath -m "${1:?output}")
mkdir -p "$OUT"
CORE=../ot_vms_bank_static_wdecode_ce.sv
MACRO=../../../../../../physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
for shape in 6:2; do
 rg=${shape%:*};wg=${shape#*:}
 for mut in 0 2 3; do
  stem=allowners-$rg-$wg-$mut
  /usr/bin/time -v -o "$OUT/$stem.compile.time" iverilog -g2012 -s tb_bank_wdecode_ce_allowners -Ptb_bank_wdecode_ce_allowners.RG=$rg -Ptb_bank_wdecode_ce_allowners.WG=$wg -Ptb_bank_wdecode_ce_allowners.MUT=$mut -o "$OUT/$stem.vvp" "$CORE" "$MACRO" tb_bank_wdecode_ce_allowners.sv > "$OUT/$stem.compile.log" 2>&1
  set +e
  /usr/bin/time -v -o "$OUT/$stem.sim.time" vvp "$OUT/$stem.vvp" > "$OUT/$stem.log" 2>&1
  rc=$?
  set -e
  if [[ $mut == 0 ]]; then test $rc = 0; elif [[ $mut == 2 ]]; then test $rc != 0;grep 'read payload' "$OUT/$stem.log";else test $rc != 0;grep 'last-word CE population mismatch' "$OUT/$stem.log";fi
  cat "$OUT/$stem.log"
  rm "$OUT/$stem.vvp"
 done
done

for shape in 6:2; do
 rg=${shape%:*};wg=${shape#*:}
 for mut in 0 1 2; do
  stem=groups-$rg-$wg-$mut
  /usr/bin/time -v -o "$OUT/$stem.compile.time" iverilog -g2012 -s tb_hbm_vm_allgroups_wdecode_ce -Ptb_hbm_vm_allgroups_wdecode_ce.RG=$rg -Ptb_hbm_vm_allgroups_wdecode_ce.WG=$wg -Ptb_hbm_vm_allgroups_wdecode_ce.MUT=$mut -o "$OUT/$stem.vvp" "$CORE" "$MACRO" tb_hbm_vm_allgroups_wdecode_ce.sv > "$OUT/$stem.compile.log" 2>&1
  set +e
  /usr/bin/time -v -o "$OUT/$stem.sim.time" vvp "$OUT/$stem.vvp" > "$OUT/$stem.log" 2>&1
  rc=$?
  set -e
  if [[ $mut == 0 ]]; then test $rc = 0; elif [[ $mut == 1 ]]; then test $rc != 0;grep 'actual bank response group mismatch' "$OUT/$stem.log"; else test $rc != 0;grep 'actual SRAM readback mismatch' "$OUT/$stem.log";fi
  cat "$OUT/$stem.log"
  rm "$OUT/$stem.vvp"
 done
done

