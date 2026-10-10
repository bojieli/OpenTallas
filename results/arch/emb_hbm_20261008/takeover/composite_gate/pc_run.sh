#!/bin/bash
set -eu
cd /srv/opentallas-scratch/codex/emb-cdc-gate
iverilog -g2012 -s tb_emb_pc -o pc.vvp rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pkg.sv rtl/qwen_sys/emb_hbm_20261008/ot_hbm_r14_stream_pc_srow.sv rtl/qwen_sys/emb_hbm_20261008/ot_qwen_ctrl_pc_emb.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pcport.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_cdc.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pc.sv rtl/test/emb_hbm/tb_emb_dram_pc.sv rtl/test/emb_hbm/tb_emb_pc.sv > pc_compile.log 2>&1
vvp pc.vvp > pc_positive.log 2>&1
sha256sum rtl/lib/*.sv rtl/qwen_sys/emb_hbm_20261008/*.sv rtl/test/emb_hbm/tb_emb_pc.sv rtl/test/emb_hbm/tb_emb_dram_pc.sv > pc_source.sha256
