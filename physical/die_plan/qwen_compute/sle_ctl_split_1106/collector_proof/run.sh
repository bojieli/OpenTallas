#!/bin/bash
set -eu
cd "$(dirname "$0")"
iverilog -g2012 -s tb -o good primitive.sv graphs.sv tb.sv
vvp good > good.log
iverilog -g2012 -s tb -o mutant primitive.sv mutant.sv tb.sv
if vvp mutant > mutant.log; then echo MUTANT_NOT_CAUGHT;exit 1;fi
echo COLLECTOR_PASS_MUTANT_CAUGHT
