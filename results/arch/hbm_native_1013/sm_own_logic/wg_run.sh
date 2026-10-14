#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
tag=${1:-split}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version | tee verilator_version.txt
"$V" --version | grep -q "Verilator 5.050"
yosys -Q -p "read_json wg_gold.json; hierarchy -top gold_wg; write_verilog -noattr wg_gold.sv" > wg_gold_emit.log
yosys -Q -p "read_json wg_${tag}.json; hierarchy -top split_wg; write_verilog -noattr wg_dut.sv" > wg_dut_emit.log
"$V" --binary --timing -j 4 -Wno-fatal --top-module tb --Mdir work_wg_${tag}_v5050 wg_gold.sv wg_dut.sv wg_surrogates.sv wg_tb.sv retention_cell_models.sv > wg_${tag}_build.log 2>&1
./work_wg_${tag}_v5050/Vtb > wg_${tag}_runtime.log 2>&1
