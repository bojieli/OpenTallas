#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
tar -xzf source_capsule.tar.gz
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing --top-module tb -j 2 -Wno-fatal -Wno-lint -Wno-style -Wno-PINMISSING --Mdir obj tb.sv safe.sv math.sv orq.sv reset.sv helpers.sv sram.v land.sv land_n32.sv ring.sv delay55.sv station_cb55.sv >build.log 2>&1
./obj/Vtb >run.log 2>&1
cat run.log
