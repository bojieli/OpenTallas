#!/bin/bash
set -u
cd /srv/opentallas-scratch/codex/emb-hub-integrated-H1-r4
src=(rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pkg.sv rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv rtl/physical/ot_qwen_die_cdc_ch.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_gw.sv rtl/qwen_sys/emb_hbm_20261008/ot_qwen_die_hub_emb.sv rtl/qwen_sys/emb_hbm_20261008/ot_qwen_die_hub_emb_integrated_impl.sv rtl/qwen_sys/emb_hbm_20261008/ot_qwen_die_hub_emb_integrated_top.sv rtl/physical/ot_qwen_kvc_packet_codec_parallel.sv rtl/test/emb_hbm/tb_emb_hub_integrated_H1.sv)
iverilog -g2012 -s tb_emb_hub_integrated_H1 -Ptb_emb_hub_integrated_H1.MODE=1 -o negative1 "${src[@]}" > negative1_compile.log 2>&1 || exit 1
vvp negative1 > negative1.log 2>&1;rc=$?
printf 'highseq_negative_exit=%s\n' "$rc" > exits.txt
[ "$rc" -ne 0 ]
