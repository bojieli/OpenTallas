#!/bin/bash
set -euo pipefail
for c in tt ff ss; do
 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/sta -exit /probe/$c.tcl > /probe/$c.log 2>&1
 grep -q "DEEP_PASS $c" /probe/$c.log
done
