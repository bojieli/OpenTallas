#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
cd "$(dirname "$0")"
verilator --binary --timing -Wno-fatal --top-module tb -j 4 --Mdir obj tb.sv ot_rom_64x64_m2.v > build.log 2>&1
./obj/Vtb +OT_ROM_DIR=. > sim.log 2>&1
tail -5 sim.log
