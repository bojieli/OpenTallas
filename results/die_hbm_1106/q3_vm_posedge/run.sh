#!/bin/bash
set -eu
cd "$(dirname "$0")"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
verilator --binary --timing --top-module tb -Wno-fatal -j 4 -Mdir obj tb.sv shells.sv mechanism.sv >build.log 2>&1
./obj/Vtb >result.log 2>&1
cat result.log
