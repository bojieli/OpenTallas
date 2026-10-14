#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
tag=${1:-split}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version | tee verilator_version.txt
"$V" --version | grep -q "Verilator 5.050"
yosys -Q -p "read_json eg_gold.json; hierarchy -top gold_eg; write_verilog -noattr eg_gold.sv" > eg_gold_emit.log
yosys -Q -p "read_json eg_${tag}.json; hierarchy -top split_eg; write_verilog -noattr eg_dut.sv" > eg_dut_emit.log
"$V" --binary --timing -j 4 -Wno-fatal --top-module tb --Mdir work_eg_${tag}_v5050 eg_gold.sv eg_dut.sv eg_surrogates.sv eg_tb.sv retention_cell_models.sv > eg_${tag}_build.log 2>&1
./work_eg_${tag}_v5050/Vtb > eg_${tag}_runtime.log 2>&1
