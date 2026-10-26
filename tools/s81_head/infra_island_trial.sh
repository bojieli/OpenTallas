#!/bin/bash
# HEAD-CORE-LAT 10-26 trial: floorplan -> place -> CTS -> GRT (no DRT), then intrinsic-latency gate TT/FF on GRT RC.
set -uo pipefail
K=$(realpath "$1"); MEM=${2:-48}; NICK=$(sed -n 's/^export DESIGN_NICKNAME = //p' $K/config.mk)
N=hcl-$(basename $K)-$$
docker run --rm --name $N --cpus=16 --memory=${MEM}g --memory-swap=${MEM}g -v "$K":/work openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; cd /OpenROAD-flow-scripts/flow
M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16"
$M cts && $M do-grt' > $K/trial.log 2>&1
rc=$?; echo "FLOW rc=$rc" >> $K/trial.log
ODB=$K/run/results/asap7/$NICK/base/5_1_grt.odb
[ -f "$ODB" ] || { echo "NO 5_1_grt"; exit $rc; }
for C in TT FF; do mkdir -p $K/gate_$C
docker run --rm --name $N-$C --cpus=4 --memory=16g --memory-swap=16g -v "$K":/work -v "$K/gate_$C":/out -e OT_POSTCTS_GRT=1 -e OT_CORNER=$C -e ODB=/work/run/results/asap7/$NICK/base/5_1_grt.odb openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; cd /OpenROAD-flow-scripts/flow; openroad -exit /work/clock_native.tcl' > $K/gate_$C/native.log 2>&1
grep -E "OT_POSTCTS_GATE|OT_PS " $K/gate_$C/native.log
done
exit $rc
