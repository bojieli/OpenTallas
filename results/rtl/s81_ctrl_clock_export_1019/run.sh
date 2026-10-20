#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")"
for mode in baseline explicit; do
 docker run --rm -v "$PWD:/proof" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/sta -exit /proof/$mode.tcl >$mode.log 2>&1
 echo $? >$mode.exit
 done
