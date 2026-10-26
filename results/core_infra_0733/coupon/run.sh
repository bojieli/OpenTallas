#!/bin/bash
set -euo pipefail
TASK_DIR=$(cd "$(dirname "$0")" && pwd)
docker run --rm --memory=4g --memory-swap=4g --cpus=2 -v "$TASK_DIR":/work -w /work openroad/orfs:asap7lock bash -c 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /work/run_coupon.tcl' > "$TASK_DIR/coupon.log" 2>&1
