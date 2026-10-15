#!/bin/bash
set -eu
cd "$(dirname "$0")"
for q in SW SE NW NE; do
 /usr/bin/time -v -o "elab-$q.time" iverilog -g2012 -Wall -s "hfd_hgi_vms_static_$q" -o "elab-$q.vvp" hfd_hgi_vms_static.sv ot_vms_*.sv ot_sram*.v >"elab-$q.log" 2>&1
 rm "elab-$q.vvp"
 echo "ACTUAL_FT_HIERARCHY_PASS $q"
done
for shape in 5:1 4:1 6:3 5:2; do
 rg=${shape%:*}; wg=${shape#*:}
 for top in tb_hbm_vm_allgroups_wdecode_ft tb_bank_wdecode_ft_allowners; do
  if [ "$top" = tb_hbm_vm_allgroups_wdecode_ft ]; then muts='0 1 2'; else muts='0 2 3'; fi
  for m in $muts; do
   stem=$top-$rg-$wg-$m
   /usr/bin/time -v -o "$stem.compile.time" iverilog -g2012 -s "$top" -P"$top.RG=$rg" -P"$top.WG=$wg" -P"$top.MUT=$m" -o "$stem.vvp" ot_vms_bank_static_wdecode_ft.sv ot_sram*.v "$top.sv" >"$stem.compile.log" 2>&1
   set +e
   /usr/bin/time -v -o "$stem.sim.time" vvp "$stem.vvp" >"$stem.log" 2>&1
   rc=$?
   set -e
   cat "$stem.log"
   if [ "$m" = 0 ]; then test "$rc" = 0; else test "$rc" != 0; fi
   rm "$stem.vvp"
  done
 done
done
