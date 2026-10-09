#!/bin/bash
set -u
cd /srv/opentallas-scratch/codex/emb-hub-boot-merge-gate
src=(rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pkg.sv rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv rtl/physical/ot_qwen_die_cdc_ch.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_gw.sv rtl/qwen_sys/emb_hbm_20261008/ot_qwen_die_hub_emb.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_hub_boot_merge.sv rtl/qwen_sys/emb_hbm_20261008/ot_qwen_die_hub_emb_boot_top.sv rtl/test/emb_hbm/tb_emb_hub_boot_merge.sv)
iverilog -g2012 -s tb_emb_hub_boot_merge -o positive "${src[@]}" > positive_compile.log 2>&1 || exit 1
vvp positive > positive.log 2>&1 || exit 2
iverilog -g2012 -s ot_qwen_die_hub_emb_boot_top -o top_elab "${src[@]}" > top_elab.log 2>&1 || exit 3
iverilog -g2012 -s tb_emb_hub_boot_merge -Ptb_emb_hub_boot_merge.MODE=1 -o negative "${src[@]}" > negative_compile.log 2>&1 || exit 4
vvp negative > negative.log 2>&1;rc=$?
printf 'negative_exit=%s\n' "$rc" > exits.txt
[ "$rc" -ne 0 ]
