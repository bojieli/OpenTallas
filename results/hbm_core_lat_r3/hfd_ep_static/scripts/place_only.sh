#!/bin/bash
# HBM-CORE-LAT-R3 ep: floorplan + place on the kit existing synth (run_kit stopped at the LEC preflight); STOPS before CTS.
set -uo pipefail
K=$(cd "$1" && pwd -P); CPUS=${2:-16}; MEM=${3:-24}
docker run --rm --name hcl3ep-place-$(basename $K | tr -c "A-Za-z0-9_.-" _)-$$ --cpus=$CPUS --memory=${MEM}g --memory-swap=${MEM}g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS place; rc=\$?; R=\$(ls -d /work/run/results/asap7/*/base); if [ -f \$R/3_place.odb ]; then ODB=\$R/3_place.odb OUT=/work/placed.csv openroad -python -exit /work/dump_placed.py > /work/dump_placed.log 2>&1; fi; exit \$rc" > "$K/place_only.log" 2>&1; rc=$?
docker run --rm -v "$K":/work openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
tail -3 "$K/place_only.log"; exit $rc
