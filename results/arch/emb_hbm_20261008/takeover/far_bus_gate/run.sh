#!/bin/bash
set -u
cd /srv/opentallas-scratch/codex/emb-far-bus-gate
sources=(rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv rtl/physical/ot_qwen_die_cdc_ch.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_link_far.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_link_far_bus.sv rtl/test/emb_hbm/tb_emb_far_bus.sv)
iverilog -g2012 -s tb_emb_far_bus -o positive "${sources[@]}" > positive_compile.log 2>&1 || exit 1
vvp positive > positive.log 2>&1 || exit 2
iverilog -g2012 -s tb_emb_far_bus -Ptb_emb_far_bus.NEG=1 -o negative "${sources[@]}" > negative_compile.log 2>&1 || exit 3
vvp negative > negative.log 2>&1; rc=$?
printf 'negative_exit=%s\n' "$rc" > exits.txt
[ "$rc" -ne 0 ]
