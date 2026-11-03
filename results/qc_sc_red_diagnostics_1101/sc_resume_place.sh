#!/bin/bash
set -euo pipefail
r=0
docker run --rm --cpus 2 --memory 16g --memory-swap 16g -v "$PWD":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=2"
$M do-3_3_place_gp
$M do-3_4_place_resized
$M do-3_5_place_dp
$M do-3_place
P=$(find /work/run/results/asap7 -path "*/base/3_place.odb" -print -quit)
ODB="$P" OUT=/work/placed_resume.csv openroad -python -exit /work/dump_placed.py > /work/dump_placed_resume.log 2>&1
' > gpl_resume.log 2>&1 || r=$?
printf '%s\n' "$r" > gpl_resume.rc
exit "$r"
