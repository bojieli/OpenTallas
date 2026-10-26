#!/bin/bash
# CTS only. Separate sessions retain each quadrant's plan-computed cluster size.
set -euo pipefail
K=$(realpath "$1")
MEM=${2:-48}
N=hcl-v4q-$$
docker run --rm --name "$N" --cpus=16 --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work openroad/orfs:asap7lock bash -lc '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /OpenROAD-flow-scripts/flow
M=(make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16)
NICK=$(sed -n "s/^export DESIGN_NICKNAME = //p" /work/config.mk)
R=/work/run/results/asap7/$NICK/base
"${M[@]}" synth
ODB_IN=$R/1_synth.odb openroad -exit /work/patch_synth.tcl
cp /work/constraint_pd.sdc "$R/1_synth.sdc"
touch "$R/1_synth.odb" "$R/1_synth.sdc"
"${M[@]}" place
for p in prep WS WN ES EN M final; do
  OT_QPHASE=$p "${M[@]}" run RUN_SCRIPT=/work/cts_seq.tcl RUN_LOG_NAME_STEM=v4q_$p
done
' > "$K/trial.log" 2>&1
