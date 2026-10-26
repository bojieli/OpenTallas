#!/bin/bash
# HEAD-CORE-LAT-R2 c3' trial (12.2a1 pushdown + 12.8b internal H-tree): synth -> patch 1_synth.odb (pushdown ft ports +
# island cells, patch_synth.tcl) -> floorplan .. CTS (GEOM-REVIEW-16: CTS-only, no GRT) -> 12.3 latency + pair gate TT/FF on placement RC.
set -uo pipefail
K=$(realpath "$1"); MEM=${2:-48}; NICK=$(sed -n 's/^export DESIGN_NICKNAME = //p' $K/config.mk)
N=hcl-$(basename $K)-$$
docker run --rm --name $N --cpus=16 --memory=${MEM}g --memory-swap=${MEM}g -v "$K":/work openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; cd /OpenROAD-flow-scripts/flow
M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16"
R=/work/run/results/asap7/'$NICK'/base
$M synth && ODB_IN=$R/1_synth.odb openroad -exit /work/patch_synth.tcl && cp /work/constraint_pd.sdc $R/1_synth.sdc && touch $R/1_synth.odb $R/1_synth.sdc && $M cts' > $K/trial.log 2>&1
rc=$?; echo "FLOW rc=$rc" >> $K/trial.log
ODB=$K/run/results/asap7/$NICK/base/4_cts.odb
[ -f "$ODB" ] || { echo "NO 4_cts"; exit $rc; }
for C in TT FF; do mkdir -p $K/gate_$C
docker run --rm --name $N-$C --cpus=4 --memory=16g --memory-swap=16g -v "$K":/work -v "$K/gate_$C":/out -e OT_CORNER=$C -e ODB=/work/run/results/asap7/$NICK/base/4_cts.odb openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; cd /OpenROAD-flow-scripts/flow; openroad -exit /work/clock_native.tcl' > $K/gate_$C/native.log 2>&1
grep -E "OT_POSTCTS_GATE|OT_PS " $K/gate_$C/native.log
done
exit $rc
