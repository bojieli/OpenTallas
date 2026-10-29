#!/bin/bash
set -euo pipefail
cd "${1:?runtime}"
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
for extra in 0 1; do
 verilator --binary --timing --build-jobs 2 -j 2 -Wno-fatal -Wno-lint -Wno-style --top-module tb_ring_local_delta -GEXTRA=$extra --Mdir obj$extra -o tb *.sv > build$extra.log 2>&1
 ./obj$extra/tb > run$extra.log 2>&1 || { tail -15 run$extra.log;exit 1; }
 grep RING_DELTA_PASS run$extra.log
done
if ./obj1/tb +STALE_SLOT > stale_slot.log 2>&1; then echo STALE_SLOT_SURVIVED;exit 1;fi
grep RING_DELTA_FAIL stale_slot.log
