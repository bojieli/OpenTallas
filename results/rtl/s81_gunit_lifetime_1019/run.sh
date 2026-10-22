#!/bin/bash
set -euo pipefail
v=/opt/verilator-5.050/bin/verilator
if [ ! -x "$v" ]; then v=$(command -v verilator); fi
"$v" --version
"$v" --binary --timing --top-module tb -Wno-fatal -DOT_MEM_NO_INIT --x-initial unique -j 2 --Mdir obj vehicle.sv tb.sv macro.v >build.log 2>&1
for seed in 1 17 241; do ./obj/Vtb +verilator+seed+$seed +verilator+rand+reset+2 >seed_$seed.log 2>&1; cat seed_$seed.log; done
