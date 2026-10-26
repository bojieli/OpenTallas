#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
for v in nominal mutant; do
 src=source.sv
 if [ "$v" = mutant ]; then
  sed '/begin : g_rdhalf/,/end else begin : g_rdfull/s/qfd_dv_s8x_kffn/qfd_dv_s8x_kff/g' source.sv > mutant.sv
  src=mutant.sv
 fi
 verilator --binary --timing -j 8 --top-module tb --Mdir obj_$v -Wno-fatal "$src" tb_readhalf.sv macro128.v macro256.v > build_$v.log 2>&1
 set +e
 ./obj_$v/Vtb +seed=3 > sim_$v.log 2>&1
 rc=$?
 set -e
 cat sim_$v.log
 if [ "$v" = nominal ]; then test $rc = 0; else test $rc != 0; fi
done
