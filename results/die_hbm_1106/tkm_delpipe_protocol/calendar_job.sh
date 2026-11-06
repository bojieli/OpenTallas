#!/bin/bash
set -eu
cd "$(dirname "$0")"
yosys -p 'read_verilog -sv -DOT_TKM_DEL_PIPE1 calendar_actual.sv; hierarchy -top calendar_actual; proc; opt; async2sync; opt_clean; sat -seq 1 -prove proof_bad 0 -verify' > calendar_eq.log 2>&1
yosys -p 'read_verilog -sv -DOT_TKM_DEL_PIPE1 calendar_mutant.sv; hierarchy -top calendar_actual; proc; opt; async2sync; opt_clean; sat -seq 1 -prove proof_bad 0 -show-inputs -dump_vcd calendar_mutant.vcd' > calendar_mutant.log 2>&1
grep -q 'SAT proof finished - model found: FAIL!' calendar_mutant.log
