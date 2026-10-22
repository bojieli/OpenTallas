#!/bin/bash
set -uo pipefail
D=$(cd "$(dirname "$0")" && pwd)
cd "$D"
test "$(stat -Lc %s input.odb)" = 5177961009 || exit 75
mkdir tcl_out3 || exit 2
sha256sum input.odb ctrl_corner.tcl die_repeaters.tcl > tcl_out3/input.sha256
docker run --rm --memory=40g --memory-swap=40g -v "$D":/work -v "$(readlink -f input.odb)":/input.odb:ro -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -exit /work/test3.tcl > /work/tcl_out3/run.log 2>&1; rc=$?; test "$rc" = 0 || exit "$rc"; openroad -python /work/placed_reach.py /work/tcl_out3/repaired.odb /work/skip_nets.txt /work/tcl_out3/actual_reach.json > /work/tcl_out3/actual_reach.log 2>&1'
rc=$?; echo "EXIT $rc $(date -Is)" > tcl_out3/run.exit; exit "$rc"
