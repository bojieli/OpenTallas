#!/bin/bash
set -u
cd /srv/opentallas-scratch/codex/emb-stack-elaboration
sources=(rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv rtl/physical/ot_qwen_die_cdc_ch.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_link_far.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_link_far_bus.sv rtl/qwen_sys/emb_hbm_20261008/synth/ot_qfd_emb_strip.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_strip_bus.sv rtl/qwen_sys/emb_hbm_20261008/ot_hbm_r14_stream_pc_srow.sv rtl/qwen_sys/emb_hbm_20261008/ot_qwen_ctrl_pc_emb.sv rtl/qwen_sys/emb_hbm_20261008/synth/ot_qfd_emb_pcport.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_cdc.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pc.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pc_bus.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_stack_bus.sv)
sha256sum "${sources[@]}" > source_sha256.txt
iverilog -g2012 -s ot_qfd_emb_stack_bus -Pot_qfd_emb_stack_bus.ENABLE=1 -o enabled "${sources[@]}" > enabled.log 2>&1; erc=$?
iverilog -g2012 -s ot_qfd_emb_stack_bus -o disabled "${sources[@]}" > disabled.log 2>&1; drc=$?
printf 'enabled_elaboration_exit=%s\ndefault_elaboration_exit=%s\n' "$erc" "$drc" > exits.txt
[ "$erc" -eq 0 ] && [ "$drc" -eq 0 ]
