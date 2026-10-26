#!/bin/bash
set -euo pipefail
for c in tt ff ss; do
 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /test/wire_${c}.tcl > /test/wire_${c}.log 2>&1
 grep -q "REAL_WIRE_PASS $c 10" /test/wire_${c}.log
done
