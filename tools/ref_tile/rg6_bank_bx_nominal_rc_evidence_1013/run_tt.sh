#!/bin/bash
set -euo pipefail
mkdir -p /tmp/rg6-bank-bx-pair/runtime
docker image inspect --format '{{.Id}}' openroad/orfs:latest > /tmp/rg6-bank-bx-pair/runtime/image_id.txt
docker run --rm -v /tmp/rg6-bank-bx-pair:/probe --entrypoint bash openroad/orfs:latest -c 'cp /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl /probe/runtime/setRC.tcl; cp /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef /probe/runtime/tech.lef'
docker run --rm -v /tmp/rg6-bank-bx-pair:/probe openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /probe/probe_tt.tcl > /tmp/rg6-bank-bx-pair/probe_tt.receipt.log 2>&1
grep -q 'PAIR_PASS tt' /tmp/rg6-bank-bx-pair/probe_tt.receipt.log
