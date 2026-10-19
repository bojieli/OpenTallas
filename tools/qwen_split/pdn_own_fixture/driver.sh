#!/bin/bash
# Run INSIDE pinned ORFS container, cwd generated fixture directory.
set -eu
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
openroad -no_init -exit candidate.tcl > candidate.log 2>&1
grep -q 'All shapes on net VDD are connected' candidate.log
grep -q 'All shapes on net VSS are connected' candidate.log
grep -q OWN_GRID_FIXTURE_PASS candidate.log
if openroad -no_init -exit mutant.tcl > mutant.log 2>&1; then
  echo 'original phase-grid mutant unexpectedly passed' >&2; exit 1
fi
grep -q 'PDN-0185.*Insufficient width' mutant.log
openroad -no_init -exit readback.tcl > readback.log 2>&1
python3 check_shorts.py shapes.tsv > shorts.json
echo 'OWN_GRID_NATIVE_PASS: 32 closed macros, VDD/VSS connected, original-phase mutant PDN-0185, zero cross-net shape intersections'
