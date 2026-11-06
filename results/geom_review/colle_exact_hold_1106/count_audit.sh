#!/bin/bash
set -euo pipefail
r=/srv/opentallas-scratch2/claude/codex-colle-exact-hold-1106
for side in ${COLLE_AUDIT_SIDES:-e w}; do
 k="$r/$side/cert_input1"
 base=$(find "$k/run/results/asap7" -mindepth 2 -maxdepth 2 -type d -name base)
 test -s "$base/6_final.odb"
 docker run --rm --cpus=2 --memory=8g --memory-swap=8g -v "$k":/work -v "$base":/base:ro -v "$r/functional_count.py":/count.py:ro -e ODB=/base/6_final.odb -e COUNT_OUT=/work/final_functional_count.json -e PINS=/work/pins.json -e OUT=/work/final_pin_audit.json openroad/orfs:asap7lock bash -lc '
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
openroad -python -exit /count.py
openroad -python -exit /work/pin_audit.py
' > "$k/final_count_audit.log" 2>&1
 done
