#!/bin/bash
set -euo pipefail
ulimit -c 0
cd "$(dirname "$0")"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
/usr/bin/time -v -o build.time "$V" --binary --timing --top-module tb -j 1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-IMPLICIT -Wno-SELRANGE -Wno-WIDTH --Mdir obj -f sources.f > build.log 2>&1
./obj/Vtb > run.log 2>&1
cat run.log
grep -q LOOP_WITNESS_PASS run.log
