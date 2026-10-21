#!/bin/bash
set -u
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
python3 results/rtl/qw_head_safe32_1020/prepare_parent.py || exit 2
O="$PWD/results/rtl/qw_head_safe32_1020/parent"
mkdir -p "$O"
for img in img0 imgh;do
 python3 rtl/test/qwen_dv/tt_ctlm_prog_safe32_bench.py --decode 3 --hard 1 --segcal 1 --work "$O/$img" --img results/rtl/qlb_c4b_1018/lmh_cal/codex_r1/$img > "$O/$img.out" 2>&1
 echo rc=$? >> "$O/$img.out"
done
