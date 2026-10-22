#!/bin/bash
# ROOT4-QWPOST unit bench: tt_ctlm_prog_bench on the REGENERATED ctlm image (main 0408184bd), Verilator 5.050.
# MUT 0 must PASS; --bmut 1, --bmut 2, --mut 1 must FAIL (regex 'CTLM_PROG .*: FAIL').
L=/srv/opentallas-scratch/claude/root4-qwpost; W=$L/runs/${1:-unit}; rm -rf $W; mkdir -p $W
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
cd $L/src && verilator --version > $W/verilator.version 2>&1
IMG=results/rtl/qwen_layer_tput_1018/ctlm_prog/image
python3 tools/qwen_layerbench/ctlm_image.py --out $W/img --lane-ages results/rtl/qwen_layer_tput_1018/ctlm_prog/lane_ages_dv2f14bn.json > $W/compile.txt || exit 2
cmp $W/img/program.memh $IMG/program.memh && echo "IMAGE_REPRODUCES program.memh byte-exact vs committed" | tee $W/image_cmp.txt || echo "IMAGE_DIFFERS" | tee $W/image_cmp.txt
for v in "--mut 0 --bmut 0" "--mut 0 --bmut 1" "--mut 0 --bmut 2" "--mut 1 --bmut 0"; do
  python3 rtl/test/qwen_dv/tt_ctlm_prog_bench.py --img $IMG --work $W --decode 3 $v
done 2>&1 | tee $W/summary.txt
# HARD_HR 1 (the die default: h16c hard head leaf ot_qfd_tt_ctlm_static_hr)
for v in "--mut 0 --bmut 0" "--mut 0 --bmut 1" "--mut 0 --bmut 2" "--mut 1 --bmut 0"; do
  python3 rtl/test/qwen_dv/tt_ctlm_prog_bench.py --img $IMG --work $W --decode 3 --hard 1 $v
done 2>&1 | tee $W/summary_hard.txt
