#!/bin/bash
set -eu
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
export CANDIDATE_DIR=results/rtl/qw_head_safe32_1020/bound_r3
python3 results/rtl/qw_head_safe32_1020/prepare_native_parent.py
O="$PWD/results/rtl/qw_head_safe32_1020/bound_parent_r3"
mkdir -p "$O"
for img in img0 imgh;do
 python3 rtl/test/qwen_dv/tt_ctlm_prog_native32_bench.py --decode 3 --hard 1 --segcal 1 --work "$O/$img" --img results/rtl/qlb_c4b_1018/lmh_cal/codex_r1/$img > "$O/$img.out" 2>&1
done
