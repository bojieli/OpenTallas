#!/bin/bash
set -u
cd /srv/opentallas-scratch/codex/emb-station-gate
pc=(rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pkg.sv rtl/qwen_sys/emb_hbm_20261008/ot_hbm_r14_stream_pc_srow.sv rtl/qwen_sys/emb_hbm_20261008/ot_qwen_ctrl_pc_emb.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_cdc.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pcport.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pc.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pc_bus.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_station_pair.sv rtl/test/emb_hbm/tb_emb_dram_pc.sv rtl/test/emb_hbm/tb_emb_station_window.sv)
for stages in 0 17; do
 iverilog -g2012 -s tb_emb_station_window -Ptb_emb_station_window.STAGES=$stages -o window$stages "${pc[@]}" > window${stages}_compile.log 2>&1 || exit 1
 vvp window$stages > window${stages}.log 2>&1 || exit 2
done
