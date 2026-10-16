#!/usr/bin/env bash
# Strap-identity VM banks (H-SM 2026-10-15): core bench (all 4 quadrant shapes, 8 banks each, identity from straps)
# with mutants 3 (wrong bank strap) and 4 (wrong slice strap) that must FATAL, plus the 4 quadrant masters x 8
# instances (literal-ABI wrappers, straps per instance) with the same two strap mutants.
set -euo pipefail
cd "$(dirname "$0")"
OUT=$(realpath -m "${1:?output}"); mkdir -p "$OUT"
ONLY_SID=${2:-all}
MACRO=../../../../../../physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
for shape in 0:5:1 1:4:1 2:6:3 3:6:3;do
 IFS=: read -r sid rg wg <<< "$shape"
 if [[ $ONLY_SID != all && $sid != "$ONLY_SID" ]];then continue;fi
 for tb in tb_hbm_vm_strap tb_hbm_vm_strap_wrappers; do
  for mut in 0 3 4;do
   stem=$tb-$sid-$rg-$wg-$mut
   srcs=(../ot_vms_ce_counter_pipe.sv ../ot_vms_bank_static_strap.sv "$MACRO" $tb.sv)
   [[ $tb == tb_hbm_vm_strap_wrappers ]] && srcs+=(../physical/hfd_vms_bank_strap_q$sid.sv)
   iverilog -g2012 -s $tb -P$tb.SID=$sid -P$tb.RG=$rg -P$tb.WG=$wg -P$tb.MUT=$mut -o "$OUT/$stem.vvp" "${srcs[@]}" > "$OUT/$stem.compile.log" 2>&1
   set +e; vvp "$OUT/$stem.vvp" > "$OUT/$stem.log" 2>&1; rc=$?; set -e
   if [[ $mut == 0 ]];then test $rc = 0 || { tail -5 "$OUT/$stem.log"; exit 1; }
   else test $rc != 0 || { echo "mutant $stem survived"; exit 1; }; grep -q "FATAL\|bank fault\|mismatch\|fatal" "$OUT/$stem.log" || { echo "mutant $stem failed for no checked reason"; exit 1; }; fi
   echo "$stem rc=$rc $(grep -m1 -h "PASS\|FATAL\|fault\|mismatch" "$OUT/$stem.log")"
  done
 done
done
echo "PASS VM_STRAP_IDENTITY core + 4 quadrant masters x 8 strapped instances; strap mutants 3 (bank) 4 (slice) FATAL"
