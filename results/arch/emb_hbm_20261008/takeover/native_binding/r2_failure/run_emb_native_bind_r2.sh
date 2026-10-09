#!/bin/bash
set -u
cd /srv/opentallas-scratch/codex/emb-native-bind-r2
iverilog -g2012 -s tb_qfd_protected_phy_typed -o typed ot_gpu_w6_secded_pkg.sv ot_hdc_hbm_model.sv ot_qfd_protected_phy_typed_pc.sv tb_qfd_protected_phy_typed.sv > typed_compile.log 2>&1 || exit 2
vvp typed > typed.log 2>&1 || exit 3
pcsrc=(ot_qfd_emb_pkg.sv ot_reset_sync.sv ot_async_fifo.sv ot_qfd_native_cmd_plain.sv ot_qfd_emb_cdc.sv ot_hbm_r24_stream_pc_srow.sv ot_qwen_ctrl_pc_emb.sv ot_qfd_emb_pcport.sv ot_qfd_emb_pc.sv ot_qfd_emb_pc_native.sv)
iverilog -g2012 -s tb_emb_pc_native -o pc "${pcsrc[@]}" tb_emb_dram_pc.sv tb_emb_pc_native.sv > pc_compile.log 2>&1 || exit 4
vvp pc > pc.log 2>&1 || exit 5
iverilog -g2012 -s ot_qfd_emb_pc_native -o off_elab "${pcsrc[@]}" > off_elab.log 2>&1 || exit 6
sha256sum *.sv > source_sha256.txt
echo PASS_ALL > verdict.txt
