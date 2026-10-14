#!/bin/bash
set -euo pipefail
expected=$(cat /tmp/rg6-bank-bx-pair/runtime/image_id.txt)
actual=$(docker image inspect --format '{{.Id}}' openroad/orfs:latest)
test "$actual" = "$expected"
for corner in ff ss; do
 docker run --rm -v /tmp/rg6-bank-bx-pair:/probe openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "/probe/probe_$corner.tcl" > "/tmp/rg6-bank-bx-pair/probe_$corner.receipt.log" 2>&1
 grep -q "PAIR_PASS $corner" "/tmp/rg6-bank-bx-pair/probe_$corner.receipt.log"
done
