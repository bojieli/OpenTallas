#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
iverilog -g2012 -s tb -o positive.vvp native_cells.sv tb_alignment.sv > compile.log 2>&1
vvp positive.vvp > positive.log 2>&1
iverilog -g2012 -s tb -DMUTANT_CTL_BYPASS -o mutant.vvp native_cells.sv tb_alignment.sv > mutant_compile.log 2>&1
vvp mutant.vvp > mutant.log 2>&1
