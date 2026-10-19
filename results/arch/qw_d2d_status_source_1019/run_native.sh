#!/bin/bash
set -euo pipefail
R=$(pwd)
A=results/arch/qw_d2d_status_source_1019
mkdir -p native
cp "$A/synth_only.mk" native/config.mk
docker run --rm -v "$R:/src:ro" -v "$R/native:/work" openroad/orfs:latest bash -lc 'cd /OpenROAD-flow-scripts/flow && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work synth' > native/native_synth.log 2>&1
docker run --rm -v "$R:/src:ro" -v "$R/native:/work" openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh; openroad -exit /src/results/arch/qw_d2d_status_source_1019/read_native.tcl' > native/census.log 2>&1
cat native/census.log
