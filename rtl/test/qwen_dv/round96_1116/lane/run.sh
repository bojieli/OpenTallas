#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing --top-module tb -j 2 -Wno-fatal -Wno-lint -Wno-style -Wno-PINMISSING --Mdir obj_lane -f sources.f >build_lane.log 2>&1
./obj_lane/Vtb +K=2 >lane_o.log 2>&1
./obj_lane/Vtb +K=6 >lane_down.log 2>&1
cat lane_o.log lane_down.log
