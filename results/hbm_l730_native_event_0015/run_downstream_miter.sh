#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
iverilog -g2012 -s tb -o downstream_positive.vvp native_cells.sv tb_downstream.sv > downstream_compile.log 2>&1
vvp downstream_positive.vvp > downstream_positive.log 2>&1
iverilog -g2012 -s tb -DMUTANT_BYPASS_STAGE -o downstream_mutant.vvp native_cells.sv tb_downstream.sv > downstream_mutant_compile.log 2>&1
vvp downstream_mutant.vvp > downstream_mutant.log 2>&1
