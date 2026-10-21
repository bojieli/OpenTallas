#!/bin/bash
set -u
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
O=results/rtl/qlb_c4b_1018/lmh_cal/codex_r4
mkdir -p "$O"
for h in 0 1; do
 python3 rtl/test/qwen_dv/tt_ctlm_prog_bench.py --decode 3 --hard "$h" --segcal 0 --work "$O/w_h${h}" --img results/rtl/qlb_c4b_1018/lmh_cal/codex_r1/img0 > "$O/h${h}_default_off.out" 2>&1
 echo rc=$? >> "$O/h${h}_default_off.out"
done
