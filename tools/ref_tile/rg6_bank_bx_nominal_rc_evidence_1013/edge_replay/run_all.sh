#!/bin/bash
set -euo pipefail
expected=$(cat /tmp/rg6-bank-bx-pair/runtime/image_id.txt)
actual=$(docker image inspect --format '{{.Id}}' openroad/orfs:latest)
test "$actual" = "$expected"
for c in tt ff ss; do
 docker run --rm -v /tmp/rg6-bank-bx-pair/edge_replay:/probe openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "/probe/probe_$c.tcl" > "/tmp/rg6-bank-bx-pair/edge_replay/probe_$c.receipt.log" 2>&1
 grep -q "PAIR_PASS $c" "/tmp/rg6-bank-bx-pair/edge_replay/probe_$c.receipt.log"
done
set +e
docker run --rm -v /tmp/rg6-bank-bx-pair/edge_replay:/probe openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /probe/mutant_zero_child_R.tcl > /tmp/rg6-bank-bx-pair/edge_replay/mutant.receipt.log 2>&1
rc=$?
set -e
test "$rc" != 0
grep -q 'entry compensation failure bank' /tmp/rg6-bank-bx-pair/edge_replay/mutant.receipt.log
