#!/bin/bash
set -euo pipefail
K=$1
DK=docker;docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --cpus 8 --memory 48g --memory-swap 48g -v "$K":/work -e HUID="$(id -u)" -e HGID="$(id -g)" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
R=$(ls -d /work/run/results/asap7/*/base | head -1)
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 -o "$R/1_synth.odb" -o "$R/1_synth.sdc" place > /work/run_place.log 2>&1
rc=$?;tail -20 /work/run_place.log;chown -R "$HUID:$HGID" /work;exit $rc'
