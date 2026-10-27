#!/bin/bash
# HEAD-CORE-LAT-R5 geometry probe: synth (netlist copy) + 12.2a1 island patch + floorplan/place ONLY (no CTS/GRT)
set -euo pipefail
K=$(realpath "$1"); MEM=${2:-24}; N=hcl-r5-$(basename $K)-$$
docker run --rm --name "$N" --cpus=16 --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work openroad/orfs:asap7lock bash -lc "
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /OpenROAD-flow-scripts/flow
M=(make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16)
R=/work/run/results/asap7/hd_elemA_rb/base
\"\${M[@]}\" synth
ODB_IN=\$R/1_synth.odb openroad -exit /work/patch_synth.tcl
cp /work/constraint_pd.sdc \$R/1_synth.sdc
touch \$R/1_synth.odb \$R/1_synth.sdc
\"\${M[@]}\" place
" > "$K/place.log" 2>&1
