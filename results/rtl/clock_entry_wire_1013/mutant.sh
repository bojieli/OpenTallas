#!/bin/bash
set -uo pipefail
/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /test/mutant_zero.tcl > /test/mutant_zero.log 2>&1
if grep -q REAL_WIRE_PASS /test/mutant_zero.log; then exit 1; fi
grep -q 'zero clock wire arrival despite' /test/mutant_zero.log
