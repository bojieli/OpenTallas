#!/bin/bash
set -euo pipefail
cd "${1:?runtime}"
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
for bad in 0 1; do
 verilator --binary --timing -j 2 -Wno-fatal -Wno-lint -Wno-style --top-module tb_idxqroot_service -GBAD_RT=$bad --Mdir obj$bad -o tb *.sv *.v > build$bad.log 2>&1
 if ./obj$bad/tb > run$bad.log 2>&1; then
  test "$bad" = 0 || { echo ROOT_MUTANT_SURVIVED;exit 1; }
  grep IDXQ_ROOT_SERVICE_PASS run$bad.log
 else
  test "$bad" = 1 || { tail -10 run$bad.log;exit 1; }
  grep IDXQ_ROOT_SERVICE_FAIL run$bad.log
 fi
done
