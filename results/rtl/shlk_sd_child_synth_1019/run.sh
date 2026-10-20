#!/bin/bash
set -euo pipefail
mkdir -p src work
tar -xf source.tar -C src
cp config.mk constraint.sdc work/
docker run --rm -v "$PWD/src:/src:ro" -v "$PWD/work:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base synth'
