#!/bin/bash
set -u
cd /srv/opentallas-scratch/codex/emb-station-gate
pc=(rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pkg.sv rtl/qwen_sys/emb_hbm_20261008/ot_hbm_r14_stream_pc_srow.sv rtl/qwen_sys/emb_hbm_20261008/ot_qwen_ctrl_pc_emb.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_cdc.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pcport.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pc.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pc_bus.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_station_pair.sv rtl/test/emb_hbm/tb_emb_dram_pc.sv rtl/test/emb_hbm/tb_emb_station_pc.sv)
for stages in 0 1 17; do
 iverilog -g2012 -s tb_emb_station_leaf -Ptb_emb_station_leaf.STAGES=$stages -o leaf$stages rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_station_pair.sv rtl/test/emb_hbm/tb_emb_station_leaf.sv > leaf${stages}_compile.log 2>&1 || exit 1
 vvp leaf$stages > leaf${stages}.log 2>&1 || exit 2
done
for stages in 0 17; do
 iverilog -g2012 -s tb_emb_station_pc -Ptb_emb_station_pc.STAGES=$stages -o pc$stages "${pc[@]}" > pc${stages}_compile.log 2>&1 || exit 3
 vvp pc$stages > pc${stages}.log 2>&1 || exit 4
done
iverilog -g2012 -s tb_emb_station_pc -Ptb_emb_station_pc.STAGES=17 -Ptb_emb_station_pc.NEG=1 -o pc_negative "${pc[@]}" > negative_compile.log 2>&1 || exit 5
vvp pc_negative > negative.log 2>&1; rc=$?
printf 'negative_exit=%s\n' "$rc" > exits.txt
[ "$rc" -ne 0 ]
