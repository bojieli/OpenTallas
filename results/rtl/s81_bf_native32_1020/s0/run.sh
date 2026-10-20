#!/bin/bash
set -eu
mkdir -p work
cp config.mk work/config.mk
docker run --rm -v "$PWD/src:/src:ro" -v "$PWD/work:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'trap "chmod -R a+rwX /work >/dev/null 2>&1 || true" EXIT; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=4 synth'
