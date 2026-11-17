#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
tar -xzf source_capsule.tar.gz
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing --top-module tb -j 2 -Wno-fatal -Wno-lint -Wno-style -Wno-PINMISSING --Mdir obj tb.sv safe.sv math.sv orq.sv reset.sv helpers.sv sram.v land.sv land_n32.sv ring.sv delay55.sv station_cb55.sv >build.log 2>&1
./obj/Vtb +K=2 +P=96 +LEAD=6 >o96late.log 2>&1
./obj/Vtb +K=6 +P=96 +LEAD=6 >down96late.log 2>&1
./obj/Vtb +K=2 +P=96 +LEAD=20 >o96legacy20.log 2>&1
./obj/Vtb +K=6 +P=96 +LEAD=20 +expect_fault=1 >down96legacy20.log 2>&1
cat o96late.log down96late.log o96legacy20.log down96legacy20.log
