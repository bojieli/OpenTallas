#!/bin/bash
# run_cts.sh T : ORFS floorplan->place->cts on the 1-ck parent trial kit, then per-corner insertion measurement
set -uo pipefail
R=$(cd "$(dirname "$0")" && pwd); T=$1; K=$R/$T; N=a0_${T}_1ck
B=/work/run/results/asap7/$N/base
docker run --rm --name qca0k3-$T-cts-$$ --cpus=8 --memory=24g --memory-swap=24g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
 make DESIGN_CONFIG=/work/config_pnr.mk WORK_HOME=/work/run NUM_CORES=8 cts; rc=\$?; \
 if [ -f $B/4_cts.odb ]; then for c in TT FF; do CORNER=\$c ODB=$B/4_cts.odb OUT=/work/ins_\$c.txt openroad -exit /work/measure.tcl > /work/measure_\$c.log 2>&1; done; fi; \
 chown -R $(id -u):$(id -g) /work; exit \$rc" > "$K/cts.log" 2>&1
echo "rc $?" >> "$K/cts.log"
