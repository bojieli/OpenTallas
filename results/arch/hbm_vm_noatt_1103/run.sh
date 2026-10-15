#!/bin/bash
set -eu
cd "$(dirname "$0")"
for m in 0 1; do
  /usr/bin/time -v -o compile$m.time iverilog -g2012 -s tb_hbm_vm_allgroups_static -Ptb_hbm_vm_allgroups_static.RG=5 -Ptb_hbm_vm_allgroups_static.WG=2 -Ptb_hbm_vm_allgroups_static.MUT=$m -o gate$m.vvp *.sv *.v >compile$m.log 2>&1
  set +e
  /usr/bin/time -v -o sim$m.time vvp gate$m.vvp >sim$m.log 2>&1
  rc=$?
  set -e
  cat sim$m.log
  if [ "$m" = 0 ]; then test "$rc" = 0; else test "$rc" != 0; fi
  rm gate$m.vvp
done
