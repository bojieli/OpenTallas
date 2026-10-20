#!/bin/bash
set -euo pipefail
docker run --rm -v "$PWD/full_native/src:/src" -v "$PWD/full_native/orfs:/work" -w /OpenROAD-flow-scripts/flow --entrypoint bash openroad/orfs:latest -lc 'make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work synth' > full_native/synth_r2.log 2>&1
docker run --rm -v "$PWD/full_native/src:/src" -v "$PWD/full_native/orfs:/work" -v "$PWD/tools/qwen_romleaf/land32:/lane" -w /work --entrypoint python3 openroad/orfs:latest /lane/full_native_audit.py > full_native/census_r2.log 2>&1
