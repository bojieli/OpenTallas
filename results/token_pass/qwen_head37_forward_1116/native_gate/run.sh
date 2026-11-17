#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
/usr/bin/time -v -o build.time "$V" --binary --timing --top-module tb -j 1 -Wno-fatal -Wno-lint -Wno-style --Mdir obj -f sources.f > build.log 2>&1
./obj/Vtb +OT_QC_TABLE_ROM_DIR=masks > run.log 2>&1
cat run.log
grep -q HEAD37_WRAPPER_GATE_PASS run.log
