#!/bin/bash
# QC-PLAN-F4A escape probe: DRT (5_2_route) on the kit's 5_1_grt.odb, to prove the detailed escape of the column-SRAM M5
# pins that share their GCell column with an M5 PG strap (escape_check.py OPEN (DRT)).  Diagnostic: no edits to the DB.
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd)
rc=0; docker run --rm --name qcf4a-drt-$(basename $K)-$$ --cpus=16 --memory=40g --memory-swap=40g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16 do-5_2_route' > "$K/drt.log" 2>&1 || rc=$?
docker run --rm -v "$K":/work openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /work/run
exit $rc
