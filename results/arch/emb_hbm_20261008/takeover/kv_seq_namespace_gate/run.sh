#!/bin/bash
set -u
cd /srv/opentallas-scratch/codex/emb-kv-seq-namespace
src=(rtl/lib/ot_async_fifo.sv rtl/lib/ot_reset_sync.sv rtl/physical/ot_qwen_die_cdc_ch.sv rtl/physical/ot_qwen_die_hub_identity.sv rtl/physical/ot_qwen_kvc_hub_cdc.sv rtl/physical/ot_qwen_kvc_packet_codec_parallel.sv rtl/physical/ot_qwen_kvc_write_link_bridge.sv rtl/test/emb_hbm/tb_emb_kv_seq_namespace.sv)
iverilog -g2012 -s tb_emb_kv_seq_namespace -o positive "${src[@]}" > positive_compile.log 2>&1 || exit 1
vvp positive > positive.log 2>&1 || exit 2
iverilog -g2012 -s tb_emb_kv_seq_namespace -Ptb_emb_kv_seq_namespace.NEG=1 -o negative "${src[@]}" > negative_compile.log 2>&1 || exit 3
vvp negative > negative.log 2>&1 || exit 4
