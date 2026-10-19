#!/bin/bash
# QLB-PROG unit bench: compile the image, MUT 0 must PASS, mutants must FAIL (summary in runs/<W>/summary.txt)
F=/srv/opentallas-scratch/claude/qlb-prog-1018; W=$F/runs/${1:-b2}; mkdir -p $W
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
cd $F/src && verilator --version > $W/verilator.version 2>&1
python3 tools/qwen_layerbench/ctlm_image.py --out $F/runs/img --lane-ages results/rtl/qwen_layer_tput_1018/ctlm_prog/lane_ages_dv2f14bn.json > $W/compile.txt || exit 2
for v in "--mut 0 --bmut 0" "--mut 0 --bmut 1" "--mut 0 --bmut 2" "--mut 1 --bmut 0"; do
  python3 rtl/test/qwen_dv/tt_ctlm_prog_bench.py --img $F/runs/img --work $W --decode 3 $v
done 2>&1 | tee $W/summary.txt
