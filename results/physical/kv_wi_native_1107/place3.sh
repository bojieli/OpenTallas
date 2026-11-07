#!/bin/bash
set -eu
R=$(cd "$(dirname "$0")" && pwd)
K=$R/place3/kv3_hub_Wi
test ! -f "$K/run/results/asap7/dp_kv3_hub_Wi/base/1_synth.odb"
# Existing mapped RTL is immutable. Rebuild only its missing physical DB using
# the canonical ORFS stage, then use the stock supported floorplan resume.
docker run --rm --cpus=8 --memory=32g --memory-swap=32g -v "$K:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-1_synth' > "$K/synth_odb_relink.log" 2>&1
exec bash "$R/place3/run_kit.sh" "$K" place 32 8
