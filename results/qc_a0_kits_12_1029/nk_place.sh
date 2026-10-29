#!/bin/bash
# QC-A0-KITS-12: ONE NK both-reset placement-only prototype (GEOM QC-NK-BOTHRESET-PLACE-1029 PASS-COND); no CTS/GRT/route
set -euo pipefail
k=/srv/opentallas-scratch2/claude/qc-a0-kits-12-1029/nk_place
sudo docker run --rm --name qca0k12-nk-place --cpus=16 --memory=32g --memory-swap=32g -v "$k":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16 place" >"$k/place.log" 2>&1
