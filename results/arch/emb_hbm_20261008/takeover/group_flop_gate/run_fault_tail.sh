#!/bin/bash
set -u
cd /srv/opentallas-scratch/codex/emb-group-flop-gate
src=(rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_group_node.sv rtl/test/emb_hbm/tb_emb_group_node.sv)
iverilog -g2012 -s tb_emb_group_node -Ptb_emb_group_node.MODE=4 -o mode4_r4 "${src[@]}" > mode4_r4_compile.log 2>&1 || exit 1
vvp mode4_r4 > mode4_r4.log 2>&1 || exit 2
iverilog -g2012 -s tb_emb_group_node -Ptb_emb_group_node.MODE=1 -o negative "${src[@]}" > negative_compile.log 2>&1 || exit 3
vvp negative > negative.log 2>&1;rc=$?
printf 'negative_exit=%s\n' "$rc" > exits.txt
[ "$rc" -ne 0 ] || exit 4
/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys -Q -p 'read_verilog -sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_group_node.sv; hierarchy -top ot_qfd_emb_group_node -chparam ENABLE 1 -chparam PCBASE 16; proc; memory_map; opt; stat' > flop_mapping.log 2>&1
