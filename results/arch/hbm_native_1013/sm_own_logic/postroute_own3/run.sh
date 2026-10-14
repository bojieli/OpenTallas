#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
yosys -Q -p 'read_json eg_gold.json; hierarchy -top gold_eg; write_verilog -noattr eg_gold.sv' > gold_emit.log
yosys -Q -p 'read_json eg_split.json; hierarchy -top split_eg; write_verilog -noattr eg_dut.sv' > dut_emit.log
tag=${1:-0}
python3 prepare.py "$tag"
v=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$v" --binary --timing -j 4 -Wno-fatal --top-module tb --Mdir "obj_$tag" eg_gold.sv eg_dut.sv eg_surrogates.sv eg_tb.sv cell_models.sv > "build_$tag.log" 2>&1 || { tail -25 "build_$tag.log";exit 2; }
./obj_$tag/Vtb > "runtime_$tag.log" 2>&1
cat "runtime_$tag.log"
