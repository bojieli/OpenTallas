#!/bin/bash
set -u
cd /srv/opentallas-scratch/codex/emb-real-ports-gate
pc_sources=(rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pkg.sv rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv rtl/qwen_sys/emb_hbm_20261008/ot_hbm_r14_stream_pc_srow.sv rtl/qwen_sys/emb_hbm_20261008/ot_qwen_ctrl_pc_emb.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_cdc.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pcport.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pc.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pc_bus.sv rtl/test/emb_hbm/tb_emb_dram_pc.sv rtl/test/emb_hbm/tb_emb_pc_bus.sv)
iverilog -g2012 -s tb_emb_pc_bus -o pc "${pc_sources[@]}" > pc_compile.log 2>&1 || exit 1
vvp pc > pc_positive.log 2>&1 || exit 2
iverilog -g2012 -s tb_emb_pc_bus -Ptb_emb_pc_bus.NEG=1 -o pc_neg "${pc_sources[@]}" > pc_negative_compile.log 2>&1 || exit 3
vvp pc_neg > pc_negative.log 2>&1; pc_rc=$?
strip_sources=(rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pkg.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_strip.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_strip_bus.sv rtl/test/emb_hbm/tb_emb_strip_bus.sv)
iverilog -g2012 -s tb_emb_strip_bus -Ptb_emb_strip_bus.NEG=1 -o strip_neg "${strip_sources[@]}" > strip_negative_compile.log 2>&1 || exit 4
vvp strip_neg > strip_negative.log 2>&1; strip_rc=$?
printf 'pc_negative_exit=%s strip_negative_exit=%s\n' "$pc_rc" "$strip_rc" > exits.txt
[ "$pc_rc" -ne 0 ] && [ "$strip_rc" -ne 0 ]
