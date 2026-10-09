#!/bin/bash
set -u
cd /srv/opentallas-scratch/codex/emb-group-flop-gate
src=(rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_group_node.sv rtl/test/emb_hbm/tb_emb_group_node.sv)
for base in 0 8 16 24; do
 iverilog -g2012 -s tb_emb_group_node -Ptb_emb_group_node.PCBASE=$base -o base$base "${src[@]}" > base${base}_compile.log 2>&1 || exit 1
 vvp base$base > base${base}.log 2>&1 || exit 2
done
for mode in 2 3 4; do
 iverilog -g2012 -s tb_emb_group_node -Ptb_emb_group_node.MODE=$mode -o mode$mode "${src[@]}" > mode${mode}_compile.log 2>&1 || exit 3
 vvp mode$mode > mode${mode}.log 2>&1 || exit 4
done
iverilog -g2012 -s tb_emb_group_node -Ptb_emb_group_node.MODE=1 -o negative "${src[@]}" > negative_compile.log 2>&1 || exit 5
vvp negative > negative.log 2>&1;rc=$?
printf 'negative_exit=%s\n' "$rc" > exits.txt
[ "$rc" -ne 0 ]
