#!/bin/bash
set -u
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
O="$PWD/results/rtl/qw_head_safe32_1020/bound_parent_r3"
python3 rtl/test/qwen_dv/tt_ctlm_prog_native32_bench.py --decode 3 --hard 1 --segcal 1 --bmut 3 --work "$O/imgh_b3" --img results/rtl/qlb_c4b_1018/lmh_cal/codex_r1/imgh > "$O/imgh_b3.out" 2>&1
rc=$?
printf 'actual_exit=%d expected_exit=1\n' "$rc" >> "$O/imgh_b3.out"
test "$rc" = 1
