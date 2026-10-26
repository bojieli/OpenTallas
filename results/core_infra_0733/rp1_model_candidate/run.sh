#!/bin/bash
set -euo pipefail
TASK_DIR=$(cd "$(dirname "$0")" && pwd)
D=(docker run --rm --cpus=8 --memory=16g --memory-swap=16g -v "$TASK_DIR":/work -w /work openroad/orfs:asap7lock)
"${D[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/prepare.tcl > "$TASK_DIR/prepare.log" 2>&1
for C in TT FF; do "${D[@]}" bash -c "CORNER=$C /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/probe.tcl" > "$TASK_DIR/native_$C.log" 2>&1; done
python3 "$TASK_DIR/summarize.py" "$TASK_DIR"
