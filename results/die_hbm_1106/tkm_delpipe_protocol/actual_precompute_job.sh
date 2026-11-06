#!/bin/bash
set -eu
cd "$(dirname "$0")"
yosys -p 'read_verilog -sv -DOT_TKM_DEL_PIPE1 precompute_actual.sv; hierarchy -top precompute_actual; proc; opt; async2sync; opt_clean; sat -tempinduct -seq 2 -maxsteps 6 -set-at 1 rst_n 0 -prove proof_bad 0 -verify' > actual_precompute_eq.log 2>&1
yosys -p 'read_verilog -sv -DOT_TKM_DEL_PIPE1 precompute_mutant.sv; hierarchy -top precompute_actual; proc; opt; async2sync; opt_clean; sat -seq 6 -set-at 1 rst_n 0 -prove proof_bad 0 -show-inputs -dump_vcd actual_precompute_mutant.vcd' > actual_precompute_mutant.log 2>&1
grep -q 'SAT proof finished - model found: FAIL!' actual_precompute_mutant.log
