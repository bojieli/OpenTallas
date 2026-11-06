#!/bin/bash
set -euo pipefail
P=$(pwd -P)
docker run --rm --cpus=2 --memory=4g --memory-swap=4g -v "$P":/work -w /work -e HUID=$(id -u) -e HGID=$(id -g) openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
for mode in eq mut1 mut2; do
 case "$mode" in eq) TEST="-verify -prove bad 0";;mut1) TEST="-falsify -prove bad_mut1 0";;mut2) TEST="-falsify -prove bad_mut2 0";;esac
 yosys -Q -p "read_verilog -sv gold_helper.sv candidate_helper.sv miter.sv; prep -top miter; flatten; opt; sat $TEST -show-inputs" > "$mode.log" 2>&1 || exit $?
done
chown -R "$HUID:$HGID" /work
'
