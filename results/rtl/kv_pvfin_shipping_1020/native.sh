#!/bin/bash
set -eu
r=$PWD
docker run --rm -v "$r/src:/src:ro" -v "$r/native:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base synth' >native/synth.log 2>&1
docker run --rm -v "$r/src:/src:ro" -v "$r/native:/work" -w /work openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 python3 /work/run_census.py >native/census.log 2>&1
