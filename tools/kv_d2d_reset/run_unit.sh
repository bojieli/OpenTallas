#!/bin/bash
set -euo pipefail
iverilog -g2012 -s tb -o polarity.sim functional_cells_udp.v tb_polarity.sv > polarity.compile.log 2>&1
vvp polarity.sim > polarity.log 2>&1
if vvp polarity.sim +MUT=1 > polarity_mutant.log 2>&1; then exit 1; fi
