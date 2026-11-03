#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
iverilog -g2012 -s tb -o sim native_modules.sv tb.sv > compile.log 2>&1
vvp sim > result_unpadded.log 2>&1
iverilog -g2012 -s tb -Ptb.PAD=1 -o sim_pad native_modules.sv tb.sv >> compile.log 2>&1
vvp sim_pad > result_padded_control.log 2>&1
iverilog -g2012 -s tb -Ptb.REQMUT=1 -o sim_mutant native_modules.sv tb.sv >> compile.log 2>&1
if vvp sim_mutant > result_mutant.log 2>&1; then echo 'ERROR mutant escaped'; exit 1; fi
echo 'PASS: unpadded projection mismatch observed, padded calendar control clean, one-edge request mutant caught'
cat result_unpadded.log result_padded_control.log result_mutant.log
