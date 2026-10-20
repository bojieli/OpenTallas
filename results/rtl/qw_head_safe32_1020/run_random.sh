#!/bin/bash
set -eu
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
python3 results/rtl/qw_head_safe32_1020/prepare_random.py
O="$PWD/results/rtl/qw_head_safe32_1020/bound_random_r3"
mkdir -p "$O"
for seed in 1 17;do
 export HEAD_INIT_SEED=$seed
 if [ "$seed" = 17 ];then
  mkdir -p "$O/seed17/obj_m0_h1_seg1"
  cp "$O/seed1/obj_m0_h1_seg1/Vtb" "$O/seed17/obj_m0_h1_seg1/Vtb"
 fi
 python3 rtl/test/qwen_dv/tt_ctlm_prog_native32_rand_bench.py --decode 3 --hard 1 --segcal 1 --work "$O/seed$seed" --img results/rtl/qlb_c4b_1018/lmh_cal/codex_r1/imgh > "$O/seed$seed.out" 2>&1
 sha256sum "$O/seed$seed/obj_m0_h1_seg1/Vtb" > "$O/seed$seed/binary.sha256"
done
