#!/bin/bash
# Congestion prototype only: real placement and GRT, unchanged source netlist,
# no CTS or STA signoff; preserve the original running kits.
set -euo pipefail
K=$(cd "$1" && pwd)
C=${2:-8}
M=${3:-32}
DK=docker
docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name "qc-south-$(basename "$K")-$$" --cpus="$C" --memory="${M}g" --memory-swap="${M}g" \
  -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -e
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES='"$C"' do-place
B=$(dirname $(find /work/run/results/asap7 -name 3_place.odb -print -quit))
ODB=$B/3_place.odb OUT=/work/placed.csv openroad -python -exit /work/dump_placed.py
cp "$B/3_place.odb" "$B/4_cts.odb"
cp "$B/3_place.sdc" "$B/4_cts.sdc"
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES='"$C"' POST_GLOBAL_ROUTE_TCL= SKIP_INCREMENTAL_REPAIR=1 SKIP_ANTENNA_REPAIR=1 do-grt
' > "$K/probe.log" 2>&1
