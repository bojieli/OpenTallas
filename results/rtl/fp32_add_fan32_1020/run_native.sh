#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
A=$(pwd)
mkdir -p native
cp results/rtl/fp32_add_fan32_1020/config.mk results/rtl/fp32_add_fan32_1020/constraint.sdc native/
docker run --rm -v "$A:/src:ro" -v "$A/native:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work synth' > native/synth.log 2>&1
docker run --rm -v "$A:/src:ro" -v "$A/native:/work" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /src/results/rtl/fp32_add_fan32_1020/native_dump.tcl > native/census.log 2>&1
