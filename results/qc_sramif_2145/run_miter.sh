#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
for v in nominal mutant; do
  src=source.sv
  if [ "$v" = mutant ]; then
    sed 's/\.ID(7450 + 4\*bk)) u_lw (\.ck(ck), \.d(ptw_w)/.ID(7450 + 4*bk)) u_lw (.ck(ck), .d(~ptw_w)/' source.sv > mutant.sv
    src=mutant.sv
  fi
  verilator --binary --timing -j 8 --top-module tb --Mdir obj_$v -Wno-fatal "$src" tb_row.sv macro128.v macro256.v > build_$v.log 2>&1
  set +e
  ./obj_$v/Vtb +seed=3 > sim_$v.log 2>&1
  rc=$?
  set -e
  cat sim_$v.log
  if [ "$v" = nominal ]; then test $rc = 0; else test $rc != 0; fi
 done
