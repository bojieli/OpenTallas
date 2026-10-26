#!/bin/bash
set -u
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version
mkdir -p src; tar xzf source.tgz -C src; cd src || exit 2
B=rtl/test/qwen_dv/tt_ctlm_prog_bench.py
I=results/rtl/qlb_c4b_1018/lmh_cal/codex_r1
mkdir -p ../runs
for h in 0 1; do
 (
 python3 "$B" --decode 3 --hard "$h" --segcal 1 --img "$I/img0" --work "../runs/h${h}" > "../runs/h${h}_base.log" 2>&1; echo $? > "../runs/h${h}_base.rc"
 python3 "$B" --decode 3 --hard "$h" --segcal 1 --img "$I/imgh" --work "../runs/h${h}" > "../runs/h${h}_head.log" 2>&1; echo $? > "../runs/h${h}_head.rc"
 python3 "$B" --decode 3 --hard "$h" --segcal 1 --img "$I/imgh" --work "../runs/h${h}" --bmut 3 > "../runs/h${h}_b3.log" 2>&1; echo $? > "../runs/h${h}_b3.rc"
 ) &
done
wait
cat ../runs/*.rc
