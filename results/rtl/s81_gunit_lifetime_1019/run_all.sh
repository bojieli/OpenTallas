#!/bin/bash
set -euo pipefail
verilator --binary --timing --top-module tb -Wno-fatal -DOT_MEM_NO_INIT -DFIXED --x-initial unique -j 2 --Mdir obj_all vehicle.sv tb_all.sv macro.v >build_all.log 2>&1
for seed in 1 17 241; do ./obj_all/Vtb +verilator+seed+$seed +verilator+rand+reset+2 >all_seed_$seed.log 2>&1; cat all_seed_$seed.log; done
