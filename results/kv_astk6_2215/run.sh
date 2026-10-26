#!/bin/bash
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
cd "$D"
verilator --binary --timing -j 8 -MAKEFLAGS OBJCACHE= -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -DSYNTHESIS -Irtl --top-module tb --Mdir obj -f files.f >build.log 2>&1
./obj/Vtb >sim.log 2>&1
cat sim.log
