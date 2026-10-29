#!/bin/bash
set -eu
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
python3 formal.py
yosys -Q -p 'read_verilog -sv obs.sv arith_contract.sv formal.sv; hierarchy -top formal; proc; flatten; opt; memory_map; opt_clean; async2sync; dffunmap; opt_clean; sat -seq 10 -tempinduct -set-init-zero -prove eq 1 -verify' > formal.log 2>&1
grep -E 'SUCCESS|FAIL|induction' formal.log | tail -n 8
