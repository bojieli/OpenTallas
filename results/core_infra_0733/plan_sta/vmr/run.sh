#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 emit.py > emit.log 2>&1
for corner in TT FF; do
 docker run --rm --cpus=2 --memory=8g --memory-swap=8g -e CORNER="$corner" -v "$PWD":/work openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/model.tcl > "model_${corner}.log" 2>&1
done
