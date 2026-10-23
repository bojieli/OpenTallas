#!/bin/bash
set -u
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
cd src || exit 2
B=rtl/test/qwen_dv/tt_ctlm_prog_bench.py;I=results/rtl/qlb_c4b_1018/lmh_cal/codex_r1
for m in 36 37; do
 (python3 "$B" --decode 3 --hard 1 --segcal 1 --img "$I/imgh" --work "../runs/m${m}" --mut "$m" > "../runs/m${m}.log" 2>&1; echo $? > "../runs/m${m}.rc") &
done
(python3 "$B" --decode 3 --hard 1 --segcal 0 --img "$I/img0" --work ../runs/default_off > ../runs/default_off.log 2>&1; echo $? > ../runs/default_off.rc) &
wait
