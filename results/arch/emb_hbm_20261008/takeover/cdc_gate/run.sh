#!/bin/bash
set -eu
cd /srv/opentallas-scratch/codex/emb-cdc-gate
base="rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_cdc.sv"
iverilog -g2012 -s tb_emb_cdc -o positive.vvp $base rtl/test/emb_hbm/tb_emb_cdc.sv
vvp positive.vvp > positive.log 2>&1
iverilog -g2012 -s tb_emb_cdc -Ptb_emb_cdc.NEG=1 -o negative.vvp $base rtl/test/emb_hbm/tb_emb_cdc.sv
if vvp negative.vvp > negative.log 2>&1; then echo NEGATIVE_UNEXPECTED_PASS; exit 1; fi
grep -q "FAIL emb_cdc" negative.log
iverilog -g2012 -s ot_qfd_emb_pc -Pot_qfd_emb_pc.ENABLE=1 -o composite.vvp $base rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pkg.sv rtl/qwen_sys/emb_hbm_20261008/ot_hbm_r14_stream_pc_srow.sv rtl/qwen_sys/emb_hbm_20261008/ot_qwen_ctrl_pc_emb.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pcport.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pc.sv > composite_parse.log 2>&1
sha256sum rtl/lib/*.sv rtl/qwen_sys/emb_hbm_20261008/*.sv rtl/test/emb_hbm/tb_emb_cdc.sv > source.sha256
printf "PASS component CDC + expected mutation failure + enabled composite elaboration\n"
