#!/bin/bash
set -euo pipefail
wt=${1:?worktree}
out=${2:?private output directory}
python3 "$(dirname "$0")/prepare.py" "$wt" "$out"
cd "$out"
iverilog -g2012 -s tb -o good.vvp base.sv chunk.sv tb.sv
vvp good.vvp > good.log 2>&1
iverilog -g2012 -s tb -o mutant.vvp base.sv mutant.sv tb.sv
if vvp mutant.vvp > mutant.log 2>&1; then echo "FAIL: wrong-K mutant survived"; exit 1; fi
for form in base chunk; do
 yosys -Q -T -p "read_verilog -sv ${form}_synth.sv ${form}_top.sv; hierarchy -top top; proc; opt; memory_map; opt; techmap; opt; write_json ${form}.json" > "${form}_synth.log" 2>&1
done
tail -n 2 good.log
head -n 2 mutant.log
