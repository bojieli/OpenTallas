#!/bin/bash
set -euo pipefail
out=${1:?output directory}
python3 tools/qwen_bv_write/exact_e3_bench.py "$out"
yosys -Q -T -p "read_verilog -sv $out/design.sv; hierarchy -top dut; proc; flatten; opt_expr; opt_clean; write_json $out/dut-opt.json" > "$out/yosys.log" 2>&1
python3 tools/qwen_bv_write/clock_census.py "$out/dut-opt.json" "$out/clock_census.json"
