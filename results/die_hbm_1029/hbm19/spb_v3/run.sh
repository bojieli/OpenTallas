#!/bin/bash
set -u
cd "$(dirname "$0")"
docker run --rm --name dh19-spb-v3_stagger3 --cpus=4 --memory=32g --memory-swap=32g -v "$PWD":/work -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /work/probe.tcl > /work/grt.log 2>&1'
rc=$?
echo "$rc" > probe.exit
exit "$rc"
