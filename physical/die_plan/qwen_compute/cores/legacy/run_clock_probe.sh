#!/bin/bash
set -euo pipefail
K=$(cd "$1" && pwd); C=${2:-8}; M=${3:-32}
DK=docker;docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name "qc-clock-probe-$(basename "$K")-$$" --cpus="$C" --memory="${M}g" --memory-swap="${M}g" \
 -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -e
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES='"$C"' SKIP_CTS_REPAIR_TIMING=1 SKIP_INCREMENTAL_REPAIR=1 SKIP_ANTENNA_REPAIR=1 do-cts do-grt
P=$(find /work/run/results/asap7 -name 5_1_grt.odb -print -quit)
ODB=$P OUT=/work/clock_placed.csv openroad -python -exit /work/dump_placed.py
' > "$K/clock_probe.log" 2>&1
