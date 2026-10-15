#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
OUT=$(realpath -m "${1:?output}")
mkdir -p "$OUT"
CORE="../ot_vms_bank_static_wdecode_ft.sv"
MACRO=../../../../../../physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
for mut in 0 1 2 3; do
 /usr/bin/time -v -o "$OUT/owner-$mut.compile.time" iverilog -g2012 -s tb_bank_wdecode_ft -Ptb_bank_wdecode_ft.MUT=$mut -o "$OUT/owner-$mut.vvp" $CORE "$MACRO" tb_bank_wdecode_ft.sv > "$OUT/owner-$mut.compile.log" 2>&1
 set +e
 /usr/bin/time -v -o "$OUT/owner-$mut.sim.time" vvp "$OUT/owner-$mut.vvp" > "$OUT/owner-$mut.log" 2>&1
 rc=$?
 set -e
 if [[ $mut == 0 ]]; then test $rc = 0; else test $rc != 0; fi
 cat "$OUT/owner-$mut.log"
 rm "$OUT/owner-$mut.vvp"
done
for shape in 7:3 5:1; do
 rg=${shape%:*};wg=${shape#*:}
 for mut in 0 1 2; do
  stem=groups-$rg-$wg-$mut
  /usr/bin/time -v -o "$OUT/$stem.compile.time" iverilog -g2012 -s tb_hbm_vm_allgroups_wdecode_ft -Ptb_hbm_vm_allgroups_wdecode_ft.RG=$rg -Ptb_hbm_vm_allgroups_wdecode_ft.WG=$wg -Ptb_hbm_vm_allgroups_wdecode_ft.MUT=$mut -o "$OUT/$stem.vvp" $CORE "$MACRO" tb_hbm_vm_allgroups_wdecode_ft.sv > "$OUT/$stem.compile.log" 2>&1
  set +e
  /usr/bin/time -v -o "$OUT/$stem.sim.time" vvp "$OUT/$stem.vvp" > "$OUT/$stem.log" 2>&1
  rc=$?
  set -e
  if [[ $mut == 0 ]]; then test $rc = 0; elif [[ $mut == 1 ]]; then test $rc != 0;grep 'actual bank response group mismatch' "$OUT/$stem.log"; else test $rc != 0;grep 'actual SRAM readback mismatch' "$OUT/$stem.log";fi
  cat "$OUT/$stem.log"
  rm "$OUT/$stem.vvp"
 done
done

bash ./run_wdecode_ft_allowners.sh "$OUT"

bash ./run_ce_arithmetic.sh "$OUT"
