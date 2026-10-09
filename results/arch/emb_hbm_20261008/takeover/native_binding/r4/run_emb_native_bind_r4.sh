#!/bin/bash
set -u
cd /srv/opentallas-scratch/codex/emb-native-bind-r4
iverilog -g2012 -s tb_qfd_protected_phy_typed -o typed ot_gpu_w6_secded_pkg.sv ot_hdc_hbm_model.sv ot_qfd_protected_phy_typed_pc.sv tb_qfd_protected_phy_typed.sv > typed_compile.log 2>&1 || exit 2
vvp typed > typed.log 2>&1 || exit 3
iverilog -g2012 -s tb_qfd_protected_phy_typed -Ptb_qfd_protected_phy_typed.ROLE_MUT=1 -o typed_role_mut ot_gpu_w6_secded_pkg.sv ot_hdc_hbm_model.sv ot_qfd_protected_phy_typed_pc.sv tb_qfd_protected_phy_typed.sv > role_mut_compile.log 2>&1 || exit 7
vvp typed_role_mut > role_mut.log 2>&1
[ "$?" = 1 ] || exit 8
pcsrc=(ot_qfd_emb_pkg.sv ot_reset_sync.sv ot_async_fifo.sv ot_qfd_native_cmd_plain.sv ot_qfd_emb_cdc.sv ot_hbm_r14_stream_pc_srow.sv ot_qwen_ctrl_pc_emb.sv ot_qfd_emb_pcport.sv ot_qfd_emb_pc.sv ot_qfd_emb_pc_native.sv)
iverilog -g2012 -s tb_emb_pc_native -o pc "${pcsrc[@]}" tb_emb_dram_pc.sv tb_emb_pc_native.sv > pc_compile.log 2>&1 || exit 4
vvp pc > pc.log 2>&1 || exit 5
iverilog -g2012 -s ot_qfd_emb_pc_native -o off_elab "${pcsrc[@]}" > off_elab.log 2>&1 || exit 6
iverilog -g2012 -s tb_emb_pc_native -Ptb_emb_pc_native.ENABLE=0 -o off_sim "${pcsrc[@]}" tb_emb_dram_pc.sv tb_emb_pc_native.sv > off_compile.log 2>&1 || exit 9
vvp off_sim > off.log 2>&1 || exit 10
sha256sum *.sv > source_sha256.txt
echo PASS_ALL > verdict.txt
