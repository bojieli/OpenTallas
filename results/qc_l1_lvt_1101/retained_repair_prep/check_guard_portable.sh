#!/bin/bash
set -euo pipefail
exec docker run --rm --cpus 2 --memory 8g --memory-swap 8g -v "$PWD":/work -w /work -e OT_RETAINED_A=/work/input.odb -e OT_RETAINED_B=/work/input.odb -e OT_RETAINED_RESULT=/work/guard_api_same_input.json openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit /work/compare_retained.py' > guard_api.log 2>&1
