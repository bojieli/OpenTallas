#!/bin/bash
# QW-H16X: RTL parent bench (qfd_tt_ctlm_dv with the safe32 head RTL incl. the h16v restructures and their simulation
# reference checks), img0 / imgh, Verilator 5.050.  repo root; usage: run_rtl_parent.sh OUT
set -u
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
O=$1; mkdir -p $O
python3 results/rtl/qw_head_safe32_1020/h16x/prepare_rtl_parent.py || exit 2
for img in img0 imgh; do
 python3 rtl/test/qwen_dv/tt_ctlm_prog_safe32_h16x_bench.py --decode 3 --hard 1 --segcal 1 --work "$O/$img" --img results/rtl/qlb_c4b_1018/lmh_cal/codex_r1/$img > "$O/$img.out" 2>&1 &
done
wait
for img in img0 imgh; do echo "$img: $(grep -E 'CTLM_PROG .*(PASS|FAIL)|H16V|H16X|fatal|Error' $O/$img.out | tail -2)"; done
