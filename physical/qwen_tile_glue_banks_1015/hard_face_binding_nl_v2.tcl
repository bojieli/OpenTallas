# NL (r13 NL helper): generated from hard_face_binding.tcl for qfd_tile_nl_banked_v1 (53 banks, 13 children).
# Frozen registered packet-source and CLOSED view binding; exact SHA256 bytes.
set qce_face_hashes {
 {rtl/qwen_sys/tile_glue_banks_20261015/qwen_glue_w514.sv} cbbe89fbcc1b1729b75ff685f1327c4bdc4e814730c68f6f5fa3819724a06644
 {physical/ref_tile/qwen_glue_w514/views/qwen_glue_w514/qwen_glue_w514.lef} ab9ca44207f15614df391331b4c9f78ae397216853eafee250715049581db3f3
 {physical/ref_tile/qwen_glue_w514/views/qwen_glue_w514/qwen_glue_w514_tt.lib} 1f98518cb3334b7b1b030ac9921a4b9a3661f69f08e68b9783ab51b6a8604fbd
 {physical/ref_tile/qwen_glue_w514/views/qwen_glue_w514/insertion.json} 5d24d152b0e7eb06eeeb94fe7f864ebba61b8d2d693afff239ad12077758ede9
 {rtl/qwen_sys/head_staging_20261015/ot_qkh_packet_stage.sv} 36c2283ba650704e94e7c17815f88d9c65b69e03f94d2803cffdb9ab55d8e8b1
 {rtl/qwen_sys/head_staging_20261015/qkh_packet_masters.sv} d64775658550748872760041f06ee0c233e4f76aaedb91ee8796844fc7c6d4fd
 {rtl/qwen_sys/tile_glue_banks_20261015/qwen_glue_face_masters.sv} 9c2dd4afab4ded9943b3bb9f72b78cae5605f404d12b66862c1da685c4eb8d0c
 {physical/ref_tile/qwen_glue_v514/views/qwen_glue_v514/qwen_glue_v514.lef} a0f3fb49379ce4eee6b203658f38d443437a3e77faf4b1ca714de005a5a7ed71
 {physical/ref_tile/qwen_glue_v514/views/qwen_glue_v514/qwen_glue_v514_tt.lib} 5ca19ce1b4f9dc7b2acc06e9791d6c309f88b54004d1eb67918d0e0f824ab9f9
 {physical/ref_tile/qwen_glue_v514/views/qwen_glue_v514/insertion.json} dbca26d7607acf9db8492f78a3f7c20021a3aa70c593b35602e4f855ca69efcb
 {physical/ref_tile/qwen_glue_v508/views/qwen_glue_v508/qwen_glue_v508.lef} 06748f98770ebd897d1e221ac9cc6069461bc98aec85acfdf2abfa61bee223d6
 {physical/ref_tile/qwen_glue_v508/views/qwen_glue_v508/qwen_glue_v508_tt.lib} 041d7afbd13e503d88d6aa96d153db71c43b60c3c930850efef3e9338cba8950
 {physical/ref_tile/qwen_glue_v508/views/qwen_glue_v508/insertion.json} 497c56517f0e71161f2c37f1de0a3e1646ad59bdfed71996d12ce128f7519771
 {physical/ref_tile/qkh_packet_v16/views/qkh_packet_v16/qkh_packet_v16.lef} e7944b2e537fd31d61eb714769bcceb1cc3249ca8f927b98d235337d04092eb9
 {physical/ref_tile/qkh_packet_v16/views/qkh_packet_v16/qkh_packet_v16_tt.lib} 34c445a21832ecef9d154a528724f2fb7a15a896902a027081327209cb3728be
 {physical/ref_tile/qkh_packet_v16/views/qkh_packet_v16/insertion.json} ded19f9f75cfc02d815ac07b0149eec691e8892a719781dbc9b8072803d23b62
}
set qce_face_clocks {
 {ck_bank[0]} {{strap} {qkh_packet_v16} {clk}}
 {ck_bank[1]} {{rqr_south_0} {qkh_packet_h256} {clk}}
 {ck_bank[2]} {{rqr_south_1} {qkh_packet_h256} {clk}}
 {ck_bank[3]} {{rqr_south_2} {qkh_packet_h256} {clk}}
 {ck_bank[4]} {{rqr_south_3} {qkh_packet_h256} {clk}}
 {ck_bank[5]} {{rqr_north_0} {qkh_packet_h256} {clk}}
 {ck_bank[6]} {{rqr_north_1} {qkh_packet_h256} {clk}}
 {ck_bank[7]} {{rqr_north_2} {qkh_packet_h256} {clk}}
 {ck_bank[8]} {{rqr_north_3} {qkh_packet_h256} {clk}}
 {ck_bank[9]} {{mq_wrom_0} {qkh_packet_h256} {clk}}
 {ck_bank[10]} {{mq_wrom_1} {qkh_packet_v256} {clk}}
 {ck_bank[11]} {{mq_wrom_2} {qkh_packet_v256} {clk}}
 {ck_bank[12]} {{mq_wrom_3} {qkh_packet_v256} {clk}}
 {ck_bank[13]} {{xdelay_0} {qkh_packet_v256} {clk}}
 {ck_bank[14]} {{xdelay_1} {qkh_packet_h256} {clk}}
 {ck_bank[15]} {{xdelay_2} {qkh_packet_h256} {clk}}
 {ck_bank[16]} {{xdelay_3} {qkh_packet_v256} {clk}}
 {ck_bank[17]} {{xdelay_4} {qkh_packet_h256} {clk}}
 {ck_bank[18]} {{xdelay_5} {qkh_packet_h256} {clk}}
 {ck_bank[19]} {{xdelay_6} {qkh_packet_h256} {clk}}
 {ck_bank[20]} {{xdelay_7} {qkh_packet_v256} {clk}}
 {ck_bank[21]} {{tx0_r0_lo} {qkh_packet_v256} {clk}}
 {ck_bank[22]} {{tx0_r1_lo} {qkh_packet_v256} {clk}}
 {ck_bank[23]} {{tx1_r0_lo} {qkh_packet_v256} {clk}}
 {ck_bank[24]} {{tx1_r1_lo} {qkh_packet_v256} {clk}}
 {ck_bank[25]} {{tx2_r0_lo} {qkh_packet_v256} {clk}}
 {ck_bank[26]} {{tx2_r1_lo} {qkh_packet_v256} {clk}}
 {ck_bank[27]} {{tx3_r0_lo} {qkh_packet_v256} {clk}}
 {ck_bank[28]} {{tx3_r1_lo} {qkh_packet_v256} {clk}}
 {ck_bank[29]} {{tx4_r0_lo} {qkh_packet_v256} {clk}}
 {ck_bank[30]} {{tx4_r1_lo} {qkh_packet_v256} {clk}}
 {ck_bank[31]} {{tx5_r0_lo} {qkh_packet_v256} {clk}}
 {ck_bank[32]} {{tx5_r1_lo} {qkh_packet_v256} {clk}}
 {ck_bank[33]} {{tx6_r0_lo} {qkh_packet_v256} {clk}}
 {ck_bank[34]} {{tx6_r1_lo} {qkh_packet_v256} {clk}}
 {ck_bank[35]} {{tx7_r0_lo} {qkh_packet_v256} {clk}}
 {ck_bank[36]} {{tx7_r1_lo} {qkh_packet_v256} {clk}}
 {ck_bank[37]} {{to_reg} {qwen_glue_v514} {clk}}
 {ck_bank[38]} {{face_t_out} {qwen_glue_w514} {clk}}
 {ck_bank[39]} {{face_tap} {qwen_glue_v508} {clk}}
 {ck_bank[40]} {{s2_word_0} {qwen_glue_v514} {clk}}
 {ck_bank[41]} {{s2_word_1} {qwen_glue_v514} {clk}}
 {ck_bank[42]} {{node_stage_t_out} {qwen_glue_v514} {clk}}
 {ck_bank[43]} {{return_south_0} {qkh_packet_h256} {clk}}
 {ck_bank[44]} {{return_south_1} {qkh_packet_h256} {clk}}
 {ck_bank[45]} {{return_south_2} {qkh_packet_h256} {clk}}
 {ck_bank[46]} {{return_south_3} {qkh_packet_h256} {clk}}
 {ck_bank[47]} {{return_north_0} {qkh_packet_v256} {clk}}
 {ck_bank[48]} {{return_north_1} {qkh_packet_v256} {clk}}
 {ck_bank[49]} {{return_north_2} {qkh_packet_v256} {clk}}
 {ck_bank[50]} {{return_north_3} {qkh_packet_v256} {clk}}
 {ck_bank[51]} {{xdelay_extra} {qkh_packet_v256} {clk}}
 {ck_bank[52]} {{s2_x_full} {qkh_packet_v256} {clk}}
 {ck_reset[0]} {{reset_root} {qkh_packet_v16} {clk}}
 {ck_reset[1]} {{reset_mid_w} {qkh_packet_v16} {clk}}
 {ck_reset[2]} {{reset_mid_e} {qkh_packet_v16} {clk}}
 {ck_reset[3]} {{reset_mid_high} {qkh_packet_v16} {clk}}
 {ck_reset[4]} {{reset_branch_w_low} {qkh_packet_v16} {clk}}
 {ck_reset[5]} {{reset_branch_w_mid} {qkh_packet_v16} {clk}}
 {ck_reset[6]} {{reset_branch_w_high0} {qkh_packet_v16} {clk}}
 {ck_reset[7]} {{reset_branch_w_high1} {qkh_packet_v16} {clk}}
 {ck_reset[8]} {{reset_branch_e_low} {qkh_packet_v16} {clk}}
 {ck_reset[9]} {{reset_branch_e_mid} {qkh_packet_v16} {clk}}
 {ck_reset[10]} {{reset_branch_e_high} {qkh_packet_v16} {clk}}
 {ck_child[0]} {{u_logic.g_rom_pipe.g_rph.g_rb[0].g_hd.u_rp} {ot_qwen_tile_rpair} {clk}}
 {ck_child[1]} {{u_logic.g_rom_pipe.g_rph.g_rb[1].g_hd.u_rp} {ot_qwen_tile_rpair} {clk}}
 {ck_child[2]} {{u_logic.g_rom_pipe.g_rph.g_rb[2].g_hd.u_rp} {ot_qwen_tile_rpair} {clk}}
 {ck_child[3]} {{u_logic.g_rom_pipe.g_rph.g_rb[3].g_hd.u_rp} {ot_qwen_tile_rpair} {clk}}
 {ck_child[4]} {{u_logic.g_rom_pipe.g_rph.g_rb[4].g_hd.u_rp} {ot_qwen_tile_rpair} {clk}}
 {ck_child[5]} {{u_logic.u_me.g_hier.g_sl[0].g_hd.u_lh} {ot_qwen_tile_lsl_fp1} {clk}}
 {ck_child[6]} {{u_logic.u_me.g_hier.g_sl[1].g_hd.u_lh} {ot_qwen_tile_lsl_fp1} {clk}}
 {ck_child[7]} {{u_logic.u_me.g_hier.g_sl[2].g_hd.u_lh} {ot_qwen_tile_lsl_fp1} {clk}}
 {ck_child[8]} {{u_logic.u_me.g_hier.g_sl[3].g_hd.u_lh} {ot_qwen_tile_lsl_fp1} {clk}}
 {ck_child[9]} {{u_logic.u_me.g_hier.g_sl[4].g_hd.u_lh} {ot_qwen_tile_lsl_fp1} {clk}}
 {ck_child[10]} {{u_logic.u_me.g_hier.g_sl[5].g_hd.u_lh} {ot_qwen_tile_lsl_fp1} {clk}}
 {ck_child[11]} {{u_logic.u_me.g_hier.g_sl[6].g_hd.u_lh} {ot_qwen_tile_lsl_fp1} {clk}}
 {ck_child[12]} {{u_logic.u_me.g_hier.g_sl[7].g_hd.u_lh} {ot_qwen_tile_lsl_fp1} {clk}}
}
source /src/physical/qwen_tile_glue_banks_1015/hard_face_audit_nl_v2.tcl
