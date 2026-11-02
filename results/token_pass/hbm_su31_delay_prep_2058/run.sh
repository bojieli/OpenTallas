#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
verilator --binary --timing -j 1 -Wno-fatal --top-module tb_delay -Mdir obj bind_cells.sv native_chains.sv tb_delay.sv > build.log 2>&1
./obj/Vtb_delay > positive.log 2>&1
grep 'SU31_DELAY PASS' positive.log
if ./obj/Vtb_delay +MUT=1 > mutant.log 2>&1;then echo 'MUTANT ESCAPED';exit 2;fi
grep 'SU31_DELAY_MISMATCH' mutant.log
