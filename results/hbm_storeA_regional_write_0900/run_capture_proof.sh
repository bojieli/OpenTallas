#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
yosys -p 'read_verilog -sv ot_hgi_sfu_store_a_regional_capture.sv capture_miter.sv; prep -top capture_miter -flatten; async2sync; opt; check -assert; sat -verify -seq 3 -tempinduct -prove mismatch 0' > capture_positive.log 2>&1
sed 's/assign region_data\[2048\*region+:2048\]=data_q;/assign region_data[2048*region+:2048]=data_q ^ (region==3?2048\x27d1:2048\x27d0);/' ot_hgi_sfu_store_a_regional_capture.sv > capture_mutant.sv
if yosys -p 'read_verilog -sv capture_mutant.sv capture_miter.sv; prep -top capture_miter -flatten; async2sync; opt; check -assert; sat -verify -seq 3 -prove mismatch 0' > capture_mutant.log 2>&1; then echo 'ERROR: capture mutant escaped';exit 1;fi
grep -E 'SUCCESS|proof did fail' capture_positive.log capture_mutant.log
