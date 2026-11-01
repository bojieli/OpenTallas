#!/bin/bash
set -eu
K=$1
DOCKER=docker
$DOCKER info >/dev/null 2>&1 || DOCKER='sudo docker'
$DOCKER run --rm --cpus 2 --memory 8g --memory-swap 8g -v "$K":/work -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; cd /OpenROAD-flow-scripts/flow; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=2 finish; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=2 do-generate_abstract' > "$K/route.log" 2>&1
