#!/bin/bash
set -euo pipefail
R=$PWD
mkdir -p synth
# This is synthesis ONLY. No floorplan, CTS, placement or route target is invoked.
docker run --rm --name kv-attn-sc-synth-1019 -v "$R/src:/src:ro" -v "$R/synth:/work" --entrypoint bash openroad/orfs:asap7lock -lc 'source /OpenROAD-flow-scripts/env.sh; cd /OpenROAD-flow-scripts/flow; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work synth' > synth/run.log 2>&1
