#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
yosys -p 'read_verilog -sv writer_cones.sv writer_miter.sv; prep -top writer_miter -flatten; opt; memory_map; opt; check -assert; sat -verify -prove mismatch 0 -show-inputs' > writer_positive.log 2>&1
sed 's/{d,d}/{d^2048\x27d1,d}/' writer_miter.sv > writer_mutant.sv
if yosys -p 'read_verilog -sv writer_cones.sv writer_mutant.sv; prep -top writer_miter -flatten; opt; memory_map; opt; check -assert; sat -verify -prove mismatch 0 -show-inputs' > writer_mutant.log 2>&1; then echo 'ERROR: wrong regional data escaped';exit 1;fi
grep -E 'SUCCESS|proof did fail' writer_positive.log writer_mutant.log
