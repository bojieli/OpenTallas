#!/bin/bash
# QC-SU-BTAB-R5: btab_m0_r5 DRT + fill + finish (ORFS RCX 6_final.spef) after CTS+GRT measured in band; clock-latency measurement only
# (no hold repair stage, no clock edits).  Same image as CTS.
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd)
docker run --rm --name btr5-rt-$(basename $K)-$$ --cpus=8 --memory=24g --memory-swap=24g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; rc=0; for t in do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc do-6_1_fill do-6_1_fill.sdc do-6_report; do make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 $t || { rc=$?; echo STAGE_FAIL $t rc $rc; break; }; done; exit $rc' > "$K/route_r5.log" 2>&1
rc=$?
docker run --rm -v "$K":/work openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /work/run
exit $rc
