#!/bin/bash
set -eu
cd "$(dirname "$0")"
yosys -p 'read_verilog -sv decode_miter.sv; hierarchy -top decode_miter; proc; opt; sat -prove bad 0 -verify' > decode_eq.log 2>&1
yosys -p 'read_verilog -sv decode_mutant.sv; hierarchy -top decode_miter; proc; opt; sat -prove bad 0 -show-inputs -dump_vcd decode_mutant.vcd' > decode_mutant.log 2>&1
grep -q 'SAT proof finished - model found: FAIL!' decode_mutant.log
