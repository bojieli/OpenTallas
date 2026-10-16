#!/bin/bash
set -eu
iverilog -g2012 -s tb -o positive tb.sv component_sources.sv >positive_compile.log 2>&1
vvp positive >positive.log 2>&1
iverilog -g2012 -s tb -o mutant tb.sv mutant_sources.sv >mutant_compile.log 2>&1
set +e
vvp mutant >mutant.log 2>&1
rc=$?
set -e
printf '%s\n' "$rc" >mutant.exit
test "$rc" -ne 0
cat positive.log mutant.log
