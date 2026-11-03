module hbm_arch_q_b010 (
    input  wire clk,
    input  wire arst_n,
    input  wire [4401:0] L11_i,    
    input  wire [4512:0] L161m_i,    
    input  wire [72:0] L186m_i,    
    output wire [1756:0] L175m_o,    
    output wire [569:0] L183m_o,    
    output wire [35:0] L188m_o,    
    output wire [1:0] L190m_o,    
    output wire [4097:0] L20_o,    
    input  wire [21:0] L101x2_i,    
    output wire [21:0] L101x2_o,    
    input  wire [5:0] L126x7_i,    
    output wire [5:0] L126x7_o,    
    input  wire [4127:0] L14x1_i,    
    output wire [4127:0] L14x1_o,    
    input  wire [1389:0] L167mx1_i,    
    output wire [1389:0] L167mx1_o,    
    input  wire [1388:0] L168mx1_i,    
    output wire [1388:0] L168mx1_o,    
    input  wire [1:0] L204mx1_i,    
    output wire [1:0] L204mx1_o,    
    input  wire [1:0] L205mx1_i,    
    output wire [1:0] L205mx1_o,    
    input  wire [1615:0] L28x2_i,    
    output wire [1615:0] L28x2_o,    
    input  wire [1329:0] L36x2_i,    
    output wire [1329:0] L36x2_o,    
    input  wire [788:0] L42x2_i,    
    output wire [788:0] L42x2_o,    
    input  wire [788:0] L43x2_i,    
    output wire [788:0] L43x2_o,    
    input  wire [612:0] L51x2_i,    
    output wire [612:0] L51x2_o,    
    input  wire [612:0] L52x7_i,    
    output wire [612:0] L52x7_o,    
    input  wire [1662:0] L730x3_i,    
    output wire [1662:0] L730x3_o,    
    input  wire [4:0] L732x3_i,    
    output wire [4:0] L732x3_o,    
    input  wire [3:0] L733x2_i,    
    output wire [3:0] L733x2_o,    
    input  wire [1:0] L734x6_i,    
    output wire [1:0] L734x6_o,    
    input  wire [1:0] L735x4_i,    
    output wire [1:0] L735x4_o,    
    input  wire [274:0] L73x2_i,    
    output wire [274:0] L73x2_o    
);
    wire [4400:0] L11_i_q;
    wire L11_i_eq;
    wire [4511:0] L161m_i_q;
    wire L161m_i_eq;
    wire [71:0] L186m_i_q;
    wire L186m_i_eq;
    wire [0:0] w_u_hb_idx_s_Q2_r0c0_k3h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c0_k3h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c0_k3h1_prdy;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54724_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54726_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54728_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54730_Y;
    wire [31:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71548_Q;
    wire [551:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71549_Q;
    wire [551:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71550_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71551_Q;
    wire [567:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71552_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71553_Q;
    wire [3:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71554_Q;
    wire [2175:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71555_Q;
    wire [29:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71556_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71557_Q;
    wire [567:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71558_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71559_Q;
    wire [3:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71560_Q;
    wire [2175:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71561_Q;
    wire [29:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71562_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71563_Q;
    wire [137:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__fbfcce2b;
    wire [137:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__f60b7f7f;
    wire [137:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__5eb5a230;
    wire [137:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__da7629f4;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55671_Y;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55672_Y;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55673_Y;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55674_Y;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55675_Y;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55676_Y;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55677_Y;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55678_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_auto_proc_dff_cc_220_proc_dff_71533_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_auto_proc_dff_cc_220_proc_dff_71538_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_auto_proc_dff_cc_220_proc_dff_71543_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_167_55670_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_logic_not_ot_hbm_idx_chunk_rt_h_sv_154_55666_Y;
    wire [31:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71508_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71509_Q;
    wire [31:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71510_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71511_Q;
    wire [31:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71512_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71513_Q;
    wire [31:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71514_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71515_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71516_Q;
    wire [3:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71517_Q;
    wire [31:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71518_Q;
    wire [567:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71519_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71520_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71521_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71522_Q;
    wire [3:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71523_Q;
    wire [2175:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71524_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71525_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71526_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71527_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71528_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71529_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71530_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71531_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71532_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71537_Q;
    wire [15:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71542_Q;
    wire [15:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71547_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_reduce_and_ot_hbm_idx_chunk_rt_h_sv_155_55667_Y;
    wire [0:0] w_u_hb_idx_s_Q2_r0c1_k0h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c1_k0h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c1_k0h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q2_r0c1_k0h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c1_k0h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c1_k0h1_prdy;
    wire [0:0] w_u_hb_idx_s_Q2_r0c1_k1h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c1_k1h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c1_k1h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q2_r0c1_k1h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c1_k1h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c1_k1h1_prdy;
    wire [0:0] w_u_hb_idx_s_Q2_r0c1_k2h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c1_k2h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c1_k2h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q2_r0c1_k2h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c1_k2h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c1_k2h1_prdy;
    wire [0:0] w_u_hb_idx_s_Q2_r0c1_k3h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c1_k3h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c1_k3h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q2_r0c1_k3h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c1_k3h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c1_k3h1_prdy;
    wire [4:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n;
    wire [568:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_qlate_q;
    wire [4:0] w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_vl_q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54724_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54726_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54728_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54730_Y;
    wire [31:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71548_Q;
    wire [551:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71549_Q;
    wire [551:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71550_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71551_Q;
    wire [567:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71552_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71553_Q;
    wire [3:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71554_Q;
    wire [2175:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71555_Q;
    wire [29:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71556_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71557_Q;
    wire [567:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71558_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71559_Q;
    wire [3:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71560_Q;
    wire [2175:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71561_Q;
    wire [29:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71562_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71563_Q;
    wire [137:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__2e9bf0c8;
    wire [137:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__58d9bac9;
    wire [137:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__6c41aa0b;
    wire [137:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__334ecc88;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55671_Y;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55672_Y;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55673_Y;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55674_Y;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55675_Y;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55676_Y;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55677_Y;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55678_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_auto_proc_dff_cc_220_proc_dff_71533_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_auto_proc_dff_cc_220_proc_dff_71538_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_auto_proc_dff_cc_220_proc_dff_71543_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_167_55670_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_logic_not_ot_hbm_idx_chunk_rt_h_sv_154_55666_Y;
    wire [31:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71508_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71509_Q;
    wire [31:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71510_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71511_Q;
    wire [31:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71512_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71513_Q;
    wire [31:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71514_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71515_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71516_Q;
    wire [3:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71517_Q;
    wire [31:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71518_Q;
    wire [567:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71519_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71520_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71521_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71522_Q;
    wire [3:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71523_Q;
    wire [2175:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71524_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71525_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71526_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71527_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71528_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71529_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71530_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71531_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71532_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71537_Q;
    wire [15:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71542_Q;
    wire [15:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71547_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_reduce_and_ot_hbm_idx_chunk_rt_h_sv_155_55667_Y;
    wire [0:0] w_u_hb_idx_s_Q2_r0c2_k0h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c2_k0h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c2_k0h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q2_r0c2_k0h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c2_k0h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c2_k0h1_prdy;
    wire [0:0] w_u_hb_idx_s_Q2_r0c2_k1h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c2_k1h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c2_k1h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q2_r0c2_k1h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c2_k1h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c2_k1h1_prdy;
    wire [0:0] w_u_hb_idx_s_Q2_r0c2_k2h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c2_k2h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c2_k2h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q2_r0c2_k2h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c2_k2h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c2_k2h1_prdy;
    wire [0:0] w_u_hb_idx_s_Q2_r0c2_k3h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c2_k3h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c2_k3h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q2_r0c2_k3h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c2_k3h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c2_k3h1_prdy;
    wire [4:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_g_delivered_reset_u_rr_rst_n;
    wire [568:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_qlate_q;
    wire [4:0] w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_vl_q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54724_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54726_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54728_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54730_Y;
    wire [31:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71548_Q;
    wire [551:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71549_Q;
    wire [551:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71550_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71551_Q;
    wire [567:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71552_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71553_Q;
    wire [3:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71554_Q;
    wire [2175:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71555_Q;
    wire [29:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71556_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71557_Q;
    wire [567:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71558_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71559_Q;
    wire [3:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71560_Q;
    wire [2175:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71561_Q;
    wire [29:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71562_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71563_Q;
    wire [137:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__9b5c0437;
    wire [137:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__3a381be0;
    wire [137:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__bafd53de;
    wire [137:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__68484ba2;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55671_Y;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55672_Y;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55673_Y;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55674_Y;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55675_Y;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55676_Y;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55677_Y;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55678_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_auto_proc_dff_cc_220_proc_dff_71533_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_auto_proc_dff_cc_220_proc_dff_71538_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_auto_proc_dff_cc_220_proc_dff_71543_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_167_55670_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_logic_not_ot_hbm_idx_chunk_rt_h_sv_154_55666_Y;
    wire [31:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71508_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71509_Q;
    wire [31:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71510_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71511_Q;
    wire [31:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71512_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71513_Q;
    wire [31:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71514_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71515_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71516_Q;
    wire [3:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71517_Q;
    wire [31:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71518_Q;
    wire [567:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71519_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71520_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71521_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71522_Q;
    wire [3:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71523_Q;
    wire [2175:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71524_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71525_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71526_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71527_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71528_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71529_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71530_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71531_Q;
    wire [7:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71532_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71537_Q;
    wire [15:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71542_Q;
    wire [15:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71547_Q;
    wire [0:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_reduce_and_ot_hbm_idx_chunk_rt_h_sv_155_55667_Y;
    wire [0:0] w_u_hb_idx_s_Q2_r0c3_k0h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c3_k0h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c3_k0h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q2_r0c3_k0h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c3_k0h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c3_k0h1_prdy;
    wire [0:0] w_u_hb_idx_s_Q2_r0c3_k1h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c3_k1h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c3_k1h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q2_r0c3_k1h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c3_k1h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c3_k1h1_prdy;
    wire [0:0] w_u_hb_idx_s_Q2_r0c3_k2h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c3_k2h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c3_k2h0_prdy;
    wire [4:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_g_delivered_reset_u_rr_rst_n;
    wire [568:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_u_qlate_q;
    wire [4:0] w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_u_vl_q;
    wire [0:0] w_u_hcb_Q7_u_c_auto_proc_dff_cc_220_proc_dff_66845_Y;
    wire [0:0] w_u_hcb_Q7_u_c_auto_proc_dff_cc_220_proc_dff_66855_Y;
    wire [0:0] w_u_hcb_Q7_u_c_auto_proc_dff_cc_220_proc_dff_66860_Y;
    wire [0:0] w_u_hcb_Q7_u_c_auto_proc_dff_cc_220_proc_dff_66865_Y;
    wire [0:0] w_u_hcb_Q7_u_c_auto_proc_dff_cc_220_proc_dff_66870_Y;
    wire [0:0] w_u_hcb_Q7_u_c_auto_proc_dff_cc_220_proc_dff_66882_Y;
    wire [0:0] w_u_hcb_Q7_u_c_eq_ot_hbm_hc_bankq_static_sv_50_54279_Y;
    wire [0:0] w_u_hcb_Q7_u_c_eq_ot_hbm_hc_bankq_static_sv_50_54281_Y;
    wire [0:0] w_u_hcb_Q7_u_c_eq_ot_hbm_hc_bankq_static_sv_50_54283_Y;
    wire [0:0] w_u_hcb_Q7_u_c_logic_and_ot_hbm_hc_bankq_static_sv_50_54280_Y;
    wire [0:0] w_u_hcb_Q7_u_c_logic_and_ot_hbm_hc_bankq_static_sv_50_54282_Y;
    wire [0:0] w_u_hcb_Q7_u_c_logic_and_ot_hbm_hc_bankq_static_sv_50_54284_Y;
    wire [0:0] w_u_hcb_Q7_u_c_logic_and_ot_hbm_hc_bankq_static_sv_61_54321_Y;
    wire [0:0] w_u_hcb_Q7_u_c_logic_not_ot_hbm_hc_bankq_static_sv_47_54276_Y;
    wire [0:0] w_u_hcb_Q7_u_c_logic_not_ot_hbm_hc_bankq_static_sv_60_54320_Y;
    wire [0:0] w_u_hcb_Q7_u_c_logic_not_ot_hbm_hc_bankq_static_sv_67_54323_Y;
    wire [0:0] w_u_hcb_Q7_u_c_logic_not_ot_hbm_hc_bankq_static_sv_76_54326_Y;
    wire [4095:0] w_u_hcb_Q7_u_c_procdff_66844_Q;
    wire [0:0] w_u_hcb_Q7_u_c_procdff_66849_Q;
    wire [0:0] w_u_hcb_Q7_u_c_procdff_66850_Q;
    wire [7:0] w_u_hcb_Q7_u_c_procdff_66851_Q;
    wire [9:0] w_u_hcb_Q7_u_c_procdff_66852_Q;
    wire [9:0] w_u_hcb_Q7_u_c_procdff_66853_Q;
    wire [4095:0] w_u_hcb_Q7_u_c_procdff_66854_Q;
    wire [0:0] w_u_hcb_Q7_u_c_procdff_66859_Q;
    wire [0:0] w_u_hcb_Q7_u_c_procdff_66864_Q;
    wire [0:0] w_u_hcb_Q7_u_c_procdff_66869_Q;
    wire [0:0] w_u_hcb_Q7_u_c_procdff_66874_Q;
    wire [0:0] w_u_hcb_Q7_u_c_procdff_66875_Q;
    wire [31:0] w_u_hcb_Q7_u_c_procdff_66876_Q;
    wire [1:0] w_u_hcb_Q7_u_c_procdff_66877_Q;
    wire [255:0] w_u_hcb_Q7_u_c_procdff_66878_Q;
    wire [767:0] w_u_hcb_Q7_u_c_procdff_66879_Q;
    wire [1023:0] w_u_hcb_Q7_u_c_procdff_66880_Q;
    wire [31:0] w_u_hcb_Q7_u_c_procdff_66881_Q;
    wire [0:0] w_u_hcb_Q7_u_c_procdff_66886_Q;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55781_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55783_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55785_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55787_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55789_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55791_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55793_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55795_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55797_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55799_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55801_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55803_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55805_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55807_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55809_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55811_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55813_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55815_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55817_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55819_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55821_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55823_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55825_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55827_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55829_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55831_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55833_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55835_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55837_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55839_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55841_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55843_Y;
    wire [0:0] w_u_hcb_Q7_u_c_procmux_55845_Y;
    wire [255:0] w_u_hcb_Q7_u_c_procmux_55847_Y;
    wire [255:0] w_u_hcb_Q7_u_c_procmux_55849_Y;
    wire [255:0] w_u_hcb_Q7_u_c_procmux_55851_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54287_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54288_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54289_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54290_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54291_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54292_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54293_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54294_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54295_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54296_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54297_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54298_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54299_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54300_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54301_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54302_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54303_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54304_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54305_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54306_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54307_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54308_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54309_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54310_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54311_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54312_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54313_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54314_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54315_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54316_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54317_Y;
    wire [0:0] w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54318_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_auto_proc_dff_cc_220_proc_dff_71776_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_auto_proc_dff_cc_220_proc_dff_71781_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54672_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54674_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54676_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54678_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54680_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54682_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54684_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54686_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54688_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54690_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54692_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54694_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54696_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54698_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54700_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54702_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54704_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54706_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54708_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54710_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54712_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54714_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54716_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54718_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54673_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54675_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54677_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54679_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54681_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54683_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54685_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54687_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54689_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54691_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54693_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54695_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54697_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54699_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54701_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54703_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54705_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54707_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54709_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54711_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54713_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54715_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54717_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54719_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_logic_not_ot_hbm_hc_bank_static_sv_59_54669_Y;
    wire [1:0] w_u_hcb_Q7_u_c_u_b_procdff_71773_Q;
    wire [9:0] w_u_hcb_Q7_u_c_u_b_procdff_71774_Q;
    wire [1023:0] w_u_hcb_Q7_u_c_u_b_procdff_71775_Q;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_procdff_71780_Q;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_procdff_71785_Q;
    wire [1:0] w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_auto_proc_dff_cc_220_proc_dff_71640_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_auto_proc_dff_cc_220_proc_dff_71660_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_auto_proc_dff_cc_220_proc_dff_71665_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_auto_proc_dff_cc_220_proc_dff_71670_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_auto_proc_dff_cc_220_proc_dff_71675_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_auto_proc_dff_cc_220_proc_dff_71680_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_669_55081_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55088_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55090_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55092_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55094_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55096_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55098_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55100_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55102_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55104_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55106_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55108_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55110_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55112_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55114_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55116_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55118_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55120_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55122_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55124_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55126_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55128_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55130_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55132_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55134_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55136_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55138_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55140_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55142_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55144_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55146_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55148_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55150_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55152_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55154_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55156_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55158_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55160_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55162_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55164_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55166_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55168_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55170_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55172_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55174_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55176_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55178_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55180_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55182_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55184_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55186_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55188_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55190_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55192_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55194_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55196_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55198_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55200_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55202_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55204_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55206_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55208_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55210_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55212_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55214_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55216_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55218_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55220_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55222_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55224_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55226_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55228_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55230_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55232_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55234_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55236_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55238_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55240_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55242_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55244_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55246_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55248_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55250_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55252_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55254_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55256_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55258_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55260_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55262_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55264_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55266_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55268_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55270_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55272_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55274_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55276_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55278_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55280_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55282_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55284_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55286_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55288_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55290_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55292_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55294_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55296_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55298_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55300_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55302_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55304_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55306_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55308_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55310_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55312_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55314_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55316_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55318_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55320_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55322_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55324_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55326_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55328_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55330_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55332_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55334_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55336_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55338_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55340_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55342_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_not_ot_hdc_v41x_hcp_sv_666_55079_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_not_ot_hdc_v41x_hcp_sv_669_55080_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_not_ot_hdc_v41x_hcp_sv_741_55344_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_logic_or_ot_hdc_v41x_hcp_sv_672_55082_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55087_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55089_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55091_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55093_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55095_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55097_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55099_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55101_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55103_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55105_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55107_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55109_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55111_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55113_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55115_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55117_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55119_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55121_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55123_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55125_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55127_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55129_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55131_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55133_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55135_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55137_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55139_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55141_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55143_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55145_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55147_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55149_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55151_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55153_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55155_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55157_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55159_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55161_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55163_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55165_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55167_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55169_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55171_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55173_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55175_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55177_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55179_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55181_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55183_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55185_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55187_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55189_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55191_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55193_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55195_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55197_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55199_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55201_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55203_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55205_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55207_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55209_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55211_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55213_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55215_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55217_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55219_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55221_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55223_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55225_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55227_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55229_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55231_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55233_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55235_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55237_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55239_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55241_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55243_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55245_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55247_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55249_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55251_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55253_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55255_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55257_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55259_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55261_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55263_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55265_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55267_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55269_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55271_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55273_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55275_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55277_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55279_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55281_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55283_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55285_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55287_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55289_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55291_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55293_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55295_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55297_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55299_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55301_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55303_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55305_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55307_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55309_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55311_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55313_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55315_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55317_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55319_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55321_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55323_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55325_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55327_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55329_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55331_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55333_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55335_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55337_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55339_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55341_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_procdff_71644_Q;
    wire [127:0] w_u_hcb_Q7_u_c_u_b_u_st_procdff_71645_Q;
    wire [127:0] w_u_hcb_Q7_u_c_u_b_u_st_procdff_71646_Q;
    wire [31:0] w_u_hcb_Q7_u_c_u_b_u_st_procdff_71647_Q;
    wire [9:0] w_u_hcb_Q7_u_c_u_b_u_st_procdff_71648_Q;
    wire [9:0] w_u_hcb_Q7_u_c_u_b_u_st_procdff_71649_Q;
    wire [31:0] w_u_hcb_Q7_u_c_u_b_u_st_procdff_71650_Q;
    wire [28:0] w_u_hcb_Q7_u_c_u_b_u_st_procdff_71651_Q;
    wire [28:0] w_u_hcb_Q7_u_c_u_b_u_st_procdff_71652_Q;
    wire [28:0] w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q;
    wire [28:0] w_u_hcb_Q7_u_c_u_b_u_st_procdff_71654_Q;
    wire [28:0] w_u_hcb_Q7_u_c_u_b_u_st_procdff_71655_Q;
    wire [28:0] w_u_hcb_Q7_u_c_u_b_u_st_procdff_71656_Q;
    wire [28:0] w_u_hcb_Q7_u_c_u_b_u_st_procdff_71657_Q;
    wire [28:0] w_u_hcb_Q7_u_c_u_b_u_st_procdff_71658_Q;
    wire [28:0] w_u_hcb_Q7_u_c_u_b_u_st_procdff_71659_Q;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_procdff_71664_Q;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_procdff_71669_Q;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_procdff_71674_Q;
    wire [8:0] w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_procdff_71684_Q;
    wire [0:0] w_u_hcb_Q7_u_c_u_b_u_st_reduce_or_ot_hdc_v41x_hcp_sv_750_55345_Y;
    wire [0:0] w_u_hcb_Q7_u_c_u_rst_rst_n;
    wire [1:0] w_u_hcb_Q7_ot_hbm_hc_bank128_pair0_fault;
    wire [511:0] w_u_hcb_Q7_ot_hbm_hc_bank128_pair0_sum_out;
    wire [1:0] w_u_hcb_Q7_ot_hbm_hc_bank128_pair1_fault;
    wire [511:0] w_u_hcb_Q7_ot_hbm_hc_bank128_pair1_sum_out;
    wire [1:0] w_u_hcb_Q7_ot_hbm_hc_bank128_pair2_fault;
    wire [511:0] w_u_hcb_Q7_ot_hbm_hc_bank128_pair2_sum_out;
    wire [1:0] w_u_hcb_Q7_ot_hbm_hc_bank128_pair3_fault;
    wire [511:0] w_u_hcb_Q7_ot_hbm_hc_bank128_pair3_sum_out;
    wire [1:0] w_u_hcb_Q7_ot_hbm_hc_bank128_pair4_fault;
    wire [511:0] w_u_hcb_Q7_ot_hbm_hc_bank128_pair4_sum_out;
    wire [1:0] w_u_hcb_Q7_ot_hbm_hc_bank128_pair5_fault;
    wire [511:0] w_u_hcb_Q7_ot_hbm_hc_bank128_pair5_sum_out;
    wire [1:0] w_u_hcb_Q7_ot_hbm_hc_bank128_pair6_fault;
    wire [511:0] w_u_hcb_Q7_ot_hbm_hc_bank128_pair6_sum_out;
    wire [1:0] w_u_hcb_Q7_ot_hbm_hc_bank128_pair7_fault;
    wire [511:0] w_u_hcb_Q7_ot_hbm_hc_bank128_pair7_sum_out;
    wire [21:0] L101x2_o_s0;
    wire [21:0] L101x2_o_s1;
    wire [21:0] L101x2_o_s2;
    wire [5:0] L126x7_o_s0;
    wire [5:0] L126x7_o_s1;
    wire [5:0] L126x7_o_s2;
    wire [4127:0] L14x1_o_s0;
    wire [4127:0] L14x1_o_s1;
    wire [4127:0] L14x1_o_s2;
    wire [4127:0] L14x1_o_s3;
    wire [4127:0] L14x1_o_s4;
    wire [1389:0] L167mx1_o_s0;
    wire [1389:0] L167mx1_o_s1;
    wire [1389:0] L167mx1_o_s2;
    wire [1389:0] L167mx1_o_s3;
    wire [1389:0] L167mx1_o_s4;
    wire [1388:0] L168mx1_o_s0;
    wire [1388:0] L168mx1_o_s1;
    wire [1388:0] L168mx1_o_s2;
    wire [1388:0] L168mx1_o_s3;
    wire [1388:0] L168mx1_o_s4;
    wire [1:0] L204mx1_o_s0;
    wire [1:0] L204mx1_o_s1;
    wire [1:0] L204mx1_o_s2;
    wire [1:0] L205mx1_o_s0;
    wire [1:0] L205mx1_o_s1;
    wire [1:0] L205mx1_o_s2;
    wire [1615:0] L28x2_o_s0;
    wire [1615:0] L28x2_o_s1;
    wire [1615:0] L28x2_o_s2;
    wire [1615:0] L28x2_o_s3;
    wire [1329:0] L36x2_o_s0;
    wire [1329:0] L36x2_o_s1;
    wire [788:0] L42x2_o_s0;
    wire [788:0] L42x2_o_s1;
    wire [788:0] L42x2_o_s2;
    wire [788:0] L43x2_o_s0;
    wire [788:0] L43x2_o_s1;
    wire [788:0] L43x2_o_s2;
    wire [612:0] L51x2_o_s0;
    wire [612:0] L51x2_o_s1;
    wire [612:0] L51x2_o_s2;
    wire [612:0] L52x7_o_s0;
    wire [612:0] L52x7_o_s1;
    wire [612:0] L52x7_o_s2;
    wire [1662:0] L730x3_o_s0;
    wire [1662:0] L730x3_o_s1;
    wire [4:0] L732x3_o_s0;
    wire [4:0] L732x3_o_s1;
    wire [3:0] L733x2_o_s0;
    wire [3:0] L733x2_o_s1;
    wire [1:0] L734x6_o_s0;
    wire [1:0] L734x6_o_s1;
    wire [1:0] L735x4_o_s0;
    wire [1:0] L735x4_o_s1;
    wire [1:0] L735x4_o_s2;
    wire [1:0] L735x4_o_s3;
    wire [1:0] L735x4_o_s4;
    wire [1:0] L735x4_o_s5;
    wire [1:0] L735x4_o_s6;
    wire [1:0] L735x4_o_s7;
    wire [1:0] L735x4_o_s8;
    wire [1:0] L735x4_o_s9;
    wire [1:0] L735x4_o_s10;
    wire [274:0] L73x2_o_s0;
    wire [274:0] L73x2_o_s1;
    wire [274:0] L73x2_o_s2;
     
    wire rst_root_n;
    ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));   
    wire rst_n_t0;
    wire rst_n_t1;
    wire rst_n_t2;
    wire rst_n_t3;
    wire rst_n_t4;
    wire rst_n_t5;
    wire rst_n_t6;
    wire rst_n_t7;
    wire rst_n_t8;
    wire rst_n_t9;
    wire rst_n_t10;
    wire rst_n_t11;
    wire rst_n_t12;
    wire rst_n_t13;
    wire rst_n_t14;
    wire rst_n_t15;
    wire rst_n_t16;
    wire rst_n_t17;
    wire rst_n_t18;
    wire rst_n_t19;
    wire rst_n_t20;
    wire rst_n_t21;
    wire rst_n_t22;
    wire rst_n_t23;
    wire rst_n_t24;
    wire rst_n_t25;
    wire rst_n_t26;
    wire rst_n_t27;
    wire rst_n_t28;
    wire rst_n_t29;
    wire rst_n_t30;
    wire rst_n_t31;
    wire rst_n_t32;
    wire rst_n_t33;
    wire rst_n_t34;
    wire rst_n_t35;
    wire rst_n_t36;
    wire rst_n_t37;
    wire rst_n_t38;
    wire rst_n_t39;
    wire rst_n_t40;
    wire rst_rl_0;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));   
    wire rst_rl_1;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));   
    wire rst_rl_2;
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));   
    wire rst_rl_3;
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_rl_3));   
    wire rst_rl_4;
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_rl_3), .q(rst_rl_4));   
    wire rst_rl_5;
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_4), .q(rst_rl_5));   
    wire rst_rl_6;
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_rl_5), .q(rst_rl_6));   
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_rl_6), .q(rst_n_t17));   
    wire rst_rl_8;
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_rl_0), .q(rst_rl_8));   
    wire rst_rl_9;
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_rl_8), .q(rst_rl_9));   
    wire rst_rl_10;
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_9), .q(rst_rl_10));   
    wire rst_rl_11;
    ot_dp_rrelay u_rrl_11 (.clk(clk), .d(rst_rl_10), .q(rst_rl_11));   
    wire rst_rl_12;
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_11), .q(rst_rl_12));   
    wire rst_rl_13;
    ot_dp_rrelay u_rrl_13 (.clk(clk), .d(rst_rl_12), .q(rst_rl_13));   
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_13), .q(rst_n_t13));   
    wire rst_rl_15;
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_8), .q(rst_rl_15));   
    wire rst_rl_16;
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_15), .q(rst_rl_16));   
    wire rst_rl_17;
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_16), .q(rst_rl_17));   
    wire rst_rl_18;
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_rl_17), .q(rst_rl_18));   
    wire rst_rl_19;
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_18), .q(rst_rl_19));   
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_19), .q(rst_n_t3));   
    ot_dp_rrelay u_rrl_21 (.clk(clk), .d(rst_rl_19), .q(rst_n_t0));   
    wire rst_rl_22;
    ot_dp_rrelay u_rrl_22 (.clk(clk), .d(rst_rl_8), .q(rst_rl_22));   
    wire rst_rl_23;
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_22), .q(rst_rl_23));   
    wire rst_rl_24;
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_23), .q(rst_rl_24));   
    wire rst_rl_25;
    ot_dp_rrelay u_rrl_25 (.clk(clk), .d(rst_rl_24), .q(rst_rl_25));   
    wire rst_rl_26;
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_rl_25), .q(rst_rl_26));   
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_26), .q(rst_n_t10));   
    wire rst_rl_28;
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_24), .q(rst_rl_28));   
    wire rst_rl_29;
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_rl_28), .q(rst_rl_29));   
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_rl_29), .q(rst_n_t7));   
    ot_dp_rrelay u_rrl_31 (.clk(clk), .d(rst_rl_29), .q(rst_n_t4));   
    wire rst_rl_32;
    ot_dp_rrelay u_rrl_32 (.clk(clk), .d(rst_root_n), .q(rst_rl_32));   
    wire rst_rl_33;
    ot_dp_rrelay u_rrl_33 (.clk(clk), .d(rst_rl_32), .q(rst_rl_33));   
    wire rst_rl_34;
    ot_dp_rrelay u_rrl_34 (.clk(clk), .d(rst_rl_33), .q(rst_rl_34));   
    wire rst_rl_35;
    ot_dp_rrelay u_rrl_35 (.clk(clk), .d(rst_rl_34), .q(rst_rl_35));   
    wire rst_rl_36;
    ot_dp_rrelay u_rrl_36 (.clk(clk), .d(rst_rl_35), .q(rst_rl_36));   
    wire rst_rl_37;
    ot_dp_rrelay u_rrl_37 (.clk(clk), .d(rst_rl_36), .q(rst_rl_37));   
    wire rst_rl_38;
    ot_dp_rrelay u_rrl_38 (.clk(clk), .d(rst_rl_37), .q(rst_rl_38));   
    ot_dp_rrelay u_rrl_39 (.clk(clk), .d(rst_rl_38), .q(rst_n_t20));   
    wire rst_rl_40;
    ot_dp_rrelay u_rrl_40 (.clk(clk), .d(rst_rl_36), .q(rst_rl_40));   
    wire rst_rl_41;
    ot_dp_rrelay u_rrl_41 (.clk(clk), .d(rst_rl_40), .q(rst_rl_41));   
    ot_dp_rrelay u_rrl_42 (.clk(clk), .d(rst_rl_41), .q(rst_n_t22));   
    wire rst_rl_43;
    ot_dp_rrelay u_rrl_43 (.clk(clk), .d(rst_rl_40), .q(rst_rl_43));   
    ot_dp_rrelay u_rrl_44 (.clk(clk), .d(rst_rl_43), .q(rst_n_t25));   
    wire rst_rl_45;
    ot_dp_rrelay u_rrl_45 (.clk(clk), .d(rst_root_n), .q(rst_rl_45));   
    wire rst_rl_46;
    ot_dp_rrelay u_rrl_46 (.clk(clk), .d(rst_rl_45), .q(rst_rl_46));   
    wire rst_rl_47;
    ot_dp_rrelay u_rrl_47 (.clk(clk), .d(rst_rl_46), .q(rst_rl_47));   
    wire rst_rl_48;
    ot_dp_rrelay u_rrl_48 (.clk(clk), .d(rst_rl_47), .q(rst_rl_48));   
    wire rst_rl_49;
    ot_dp_rrelay u_rrl_49 (.clk(clk), .d(rst_rl_48), .q(rst_rl_49));   
    wire rst_rl_50;
    ot_dp_rrelay u_rrl_50 (.clk(clk), .d(rst_rl_49), .q(rst_rl_50));   
    wire rst_rl_51;
    ot_dp_rrelay u_rrl_51 (.clk(clk), .d(rst_rl_50), .q(rst_rl_51));   
    ot_dp_rrelay u_rrl_52 (.clk(clk), .d(rst_rl_51), .q(rst_n_t1));   
    wire rst_rl_53;
    ot_dp_rrelay u_rrl_53 (.clk(clk), .d(rst_rl_49), .q(rst_rl_53));   
    wire rst_rl_54;
    ot_dp_rrelay u_rrl_54 (.clk(clk), .d(rst_rl_53), .q(rst_rl_54));   
    ot_dp_rrelay u_rrl_55 (.clk(clk), .d(rst_rl_54), .q(rst_n_t2));   
    wire rst_rl_56;
    ot_dp_rrelay u_rrl_56 (.clk(clk), .d(rst_root_n), .q(rst_rl_56));   
    wire rst_rl_57;
    ot_dp_rrelay u_rrl_57 (.clk(clk), .d(rst_rl_56), .q(rst_rl_57));   
    wire rst_rl_58;
    ot_dp_rrelay u_rrl_58 (.clk(clk), .d(rst_rl_57), .q(rst_rl_58));   
    wire rst_rl_59;
    ot_dp_rrelay u_rrl_59 (.clk(clk), .d(rst_rl_58), .q(rst_rl_59));   
    wire rst_rl_60;
    ot_dp_rrelay u_rrl_60 (.clk(clk), .d(rst_rl_59), .q(rst_rl_60));   
    wire rst_rl_61;
    ot_dp_rrelay u_rrl_61 (.clk(clk), .d(rst_rl_60), .q(rst_rl_61));   
    wire rst_rl_62;
    ot_dp_rrelay u_rrl_62 (.clk(clk), .d(rst_rl_61), .q(rst_rl_62));   
    ot_dp_rrelay u_rrl_63 (.clk(clk), .d(rst_rl_62), .q(rst_n_t8));   
    wire rst_rl_64;
    ot_dp_rrelay u_rrl_64 (.clk(clk), .d(rst_rl_61), .q(rst_rl_64));   
    ot_dp_rrelay u_rrl_65 (.clk(clk), .d(rst_rl_64), .q(rst_n_t5));   
    wire rst_rl_66;
    ot_dp_rrelay u_rrl_66 (.clk(clk), .d(rst_root_n), .q(rst_rl_66));   
    wire rst_rl_67;
    ot_dp_rrelay u_rrl_67 (.clk(clk), .d(rst_rl_66), .q(rst_rl_67));   
    wire rst_rl_68;
    ot_dp_rrelay u_rrl_68 (.clk(clk), .d(rst_rl_67), .q(rst_rl_68));   
    wire rst_rl_69;
    ot_dp_rrelay u_rrl_69 (.clk(clk), .d(rst_rl_68), .q(rst_rl_69));   
    wire rst_rl_70;
    ot_dp_rrelay u_rrl_70 (.clk(clk), .d(rst_rl_69), .q(rst_rl_70));   
    wire rst_rl_71;
    ot_dp_rrelay u_rrl_71 (.clk(clk), .d(rst_rl_70), .q(rst_rl_71));   
    wire rst_rl_72;
    ot_dp_rrelay u_rrl_72 (.clk(clk), .d(rst_rl_71), .q(rst_rl_72));   
    ot_dp_rrelay u_rrl_73 (.clk(clk), .d(rst_rl_72), .q(rst_n_t14));   
    wire rst_rl_74;
    ot_dp_rrelay u_rrl_74 (.clk(clk), .d(rst_rl_71), .q(rst_rl_74));   
    ot_dp_rrelay u_rrl_75 (.clk(clk), .d(rst_rl_74), .q(rst_n_t11));   
    wire rst_rl_76;
    ot_dp_rrelay u_rrl_76 (.clk(clk), .d(rst_root_n), .q(rst_rl_76));   
    wire rst_rl_77;
    ot_dp_rrelay u_rrl_77 (.clk(clk), .d(rst_rl_76), .q(rst_rl_77));   
    wire rst_rl_78;
    ot_dp_rrelay u_rrl_78 (.clk(clk), .d(rst_rl_77), .q(rst_rl_78));   
    wire rst_rl_79;
    ot_dp_rrelay u_rrl_79 (.clk(clk), .d(rst_rl_78), .q(rst_rl_79));   
    wire rst_rl_80;
    ot_dp_rrelay u_rrl_80 (.clk(clk), .d(rst_rl_79), .q(rst_rl_80));   
    wire rst_rl_81;
    ot_dp_rrelay u_rrl_81 (.clk(clk), .d(rst_rl_80), .q(rst_rl_81));   
    wire rst_rl_82;
    ot_dp_rrelay u_rrl_82 (.clk(clk), .d(rst_rl_81), .q(rst_rl_82));   
    ot_dp_rrelay u_rrl_83 (.clk(clk), .d(rst_rl_82), .q(rst_n_t15));   
    wire rst_rl_84;
    ot_dp_rrelay u_rrl_84 (.clk(clk), .d(rst_root_n), .q(rst_rl_84));   
    wire rst_rl_85;
    ot_dp_rrelay u_rrl_85 (.clk(clk), .d(rst_rl_84), .q(rst_rl_85));   
    wire rst_rl_86;
    ot_dp_rrelay u_rrl_86 (.clk(clk), .d(rst_rl_85), .q(rst_rl_86));   
    wire rst_rl_87;
    ot_dp_rrelay u_rrl_87 (.clk(clk), .d(rst_rl_86), .q(rst_rl_87));   
    wire rst_rl_88;
    ot_dp_rrelay u_rrl_88 (.clk(clk), .d(rst_rl_87), .q(rst_rl_88));   
    wire rst_rl_89;
    ot_dp_rrelay u_rrl_89 (.clk(clk), .d(rst_rl_88), .q(rst_rl_89));   
    wire rst_rl_90;
    ot_dp_rrelay u_rrl_90 (.clk(clk), .d(rst_rl_89), .q(rst_rl_90));   
    ot_dp_rrelay u_rrl_91 (.clk(clk), .d(rst_rl_90), .q(rst_n_t16));   
    wire rst_rl_92;
    ot_dp_rrelay u_rrl_92 (.clk(clk), .d(rst_rl_85), .q(rst_rl_92));   
    wire rst_rl_93;
    ot_dp_rrelay u_rrl_93 (.clk(clk), .d(rst_rl_92), .q(rst_rl_93));   
    wire rst_rl_94;
    ot_dp_rrelay u_rrl_94 (.clk(clk), .d(rst_rl_93), .q(rst_rl_94));   
    wire rst_rl_95;
    ot_dp_rrelay u_rrl_95 (.clk(clk), .d(rst_rl_94), .q(rst_rl_95));   
    wire rst_rl_96;
    ot_dp_rrelay u_rrl_96 (.clk(clk), .d(rst_rl_95), .q(rst_rl_96));   
    ot_dp_rrelay u_rrl_97 (.clk(clk), .d(rst_rl_96), .q(rst_n_t38));   
    wire rst_rl_98;
    ot_dp_rrelay u_rrl_98 (.clk(clk), .d(rst_rl_93), .q(rst_rl_98));   
    wire rst_rl_99;
    ot_dp_rrelay u_rrl_99 (.clk(clk), .d(rst_rl_98), .q(rst_rl_99));   
    wire rst_rl_100;
    ot_dp_rrelay u_rrl_100 (.clk(clk), .d(rst_rl_99), .q(rst_rl_100));   
    ot_dp_rrelay u_rrl_101 (.clk(clk), .d(rst_rl_100), .q(rst_n_t12));   
    wire rst_rl_102;
    ot_dp_rrelay u_rrl_102 (.clk(clk), .d(rst_rl_93), .q(rst_rl_102));   
    wire rst_rl_103;
    ot_dp_rrelay u_rrl_103 (.clk(clk), .d(rst_rl_102), .q(rst_rl_103));   
    wire rst_rl_104;
    ot_dp_rrelay u_rrl_104 (.clk(clk), .d(rst_rl_103), .q(rst_rl_104));   
    ot_dp_rrelay u_rrl_105 (.clk(clk), .d(rst_rl_104), .q(rst_n_t37));   
    wire rst_rl_106;
    ot_dp_rrelay u_rrl_106 (.clk(clk), .d(rst_rl_102), .q(rst_rl_106));   
    wire rst_rl_107;
    ot_dp_rrelay u_rrl_107 (.clk(clk), .d(rst_rl_106), .q(rst_rl_107));   
    ot_dp_rrelay u_rrl_108 (.clk(clk), .d(rst_rl_107), .q(rst_n_t9));   
    wire rst_rl_109;
    ot_dp_rrelay u_rrl_109 (.clk(clk), .d(rst_rl_102), .q(rst_rl_109));   
    wire rst_rl_110;
    ot_dp_rrelay u_rrl_110 (.clk(clk), .d(rst_rl_109), .q(rst_rl_110));   
    ot_dp_rrelay u_rrl_111 (.clk(clk), .d(rst_rl_110), .q(rst_n_t36));   
    wire rst_rl_112;
    ot_dp_rrelay u_rrl_112 (.clk(clk), .d(rst_rl_109), .q(rst_rl_112));   
    ot_dp_rrelay u_rrl_113 (.clk(clk), .d(rst_rl_112), .q(rst_n_t6));   
    wire rst_rl_114;
    ot_dp_rrelay u_rrl_114 (.clk(clk), .d(rst_rl_109), .q(rst_rl_114));   
    ot_dp_rrelay u_rrl_115 (.clk(clk), .d(rst_rl_114), .q(rst_n_t35));   
    ot_dp_rrelay u_rrl_116 (.clk(clk), .d(rst_rl_114), .q(rst_n_t34));   
    wire rst_rl_117;
    ot_dp_rrelay u_rrl_117 (.clk(clk), .d(rst_root_n), .q(rst_rl_117));   
    wire rst_rl_118;
    ot_dp_rrelay u_rrl_118 (.clk(clk), .d(rst_rl_117), .q(rst_rl_118));   
    wire rst_rl_119;
    ot_dp_rrelay u_rrl_119 (.clk(clk), .d(rst_rl_118), .q(rst_rl_119));   
    wire rst_rl_120;
    ot_dp_rrelay u_rrl_120 (.clk(clk), .d(rst_rl_119), .q(rst_rl_120));   
    wire rst_rl_121;
    ot_dp_rrelay u_rrl_121 (.clk(clk), .d(rst_rl_120), .q(rst_rl_121));   
    wire rst_rl_122;
    ot_dp_rrelay u_rrl_122 (.clk(clk), .d(rst_rl_121), .q(rst_rl_122));   
    wire rst_rl_123;
    ot_dp_rrelay u_rrl_123 (.clk(clk), .d(rst_rl_122), .q(rst_rl_123));   
    ot_dp_rrelay u_rrl_124 (.clk(clk), .d(rst_rl_123), .q(rst_n_t19));   
    wire rst_rl_125;
    ot_dp_rrelay u_rrl_125 (.clk(clk), .d(rst_rl_121), .q(rst_rl_125));   
    wire rst_rl_126;
    ot_dp_rrelay u_rrl_126 (.clk(clk), .d(rst_rl_125), .q(rst_rl_126));   
    ot_dp_rrelay u_rrl_127 (.clk(clk), .d(rst_rl_126), .q(rst_n_t18));   
    wire rst_rl_128;
    ot_dp_rrelay u_rrl_128 (.clk(clk), .d(rst_rl_121), .q(rst_rl_128));   
    wire rst_rl_129;
    ot_dp_rrelay u_rrl_129 (.clk(clk), .d(rst_rl_128), .q(rst_rl_129));   
    ot_dp_rrelay u_rrl_130 (.clk(clk), .d(rst_rl_129), .q(rst_n_t21));   
    wire rst_rl_131;
    ot_dp_rrelay u_rrl_131 (.clk(clk), .d(rst_root_n), .q(rst_rl_131));   
    wire rst_rl_132;
    ot_dp_rrelay u_rrl_132 (.clk(clk), .d(rst_rl_131), .q(rst_rl_132));   
    wire rst_rl_133;
    ot_dp_rrelay u_rrl_133 (.clk(clk), .d(rst_rl_132), .q(rst_rl_133));   
    wire rst_rl_134;
    ot_dp_rrelay u_rrl_134 (.clk(clk), .d(rst_rl_133), .q(rst_rl_134));   
    wire rst_rl_135;
    ot_dp_rrelay u_rrl_135 (.clk(clk), .d(rst_rl_134), .q(rst_rl_135));   
    wire rst_rl_136;
    ot_dp_rrelay u_rrl_136 (.clk(clk), .d(rst_rl_135), .q(rst_rl_136));   
    wire rst_rl_137;
    ot_dp_rrelay u_rrl_137 (.clk(clk), .d(rst_rl_136), .q(rst_rl_137));   
    ot_dp_rrelay u_rrl_138 (.clk(clk), .d(rst_rl_137), .q(rst_n_t23));   
    wire rst_rl_139;
    ot_dp_rrelay u_rrl_139 (.clk(clk), .d(rst_rl_133), .q(rst_rl_139));   
    wire rst_rl_140;
    ot_dp_rrelay u_rrl_140 (.clk(clk), .d(rst_rl_139), .q(rst_rl_140));   
    wire rst_rl_141;
    ot_dp_rrelay u_rrl_141 (.clk(clk), .d(rst_rl_140), .q(rst_rl_141));   
    wire rst_rl_142;
    ot_dp_rrelay u_rrl_142 (.clk(clk), .d(rst_rl_141), .q(rst_rl_142));   
    ot_dp_rrelay u_rrl_143 (.clk(clk), .d(rst_rl_142), .q(rst_n_t27));   
    wire rst_rl_144;
    ot_dp_rrelay u_rrl_144 (.clk(clk), .d(rst_rl_132), .q(rst_rl_144));   
    wire rst_rl_145;
    ot_dp_rrelay u_rrl_145 (.clk(clk), .d(rst_rl_144), .q(rst_rl_145));   
    wire rst_rl_146;
    ot_dp_rrelay u_rrl_146 (.clk(clk), .d(rst_rl_145), .q(rst_rl_146));   
    wire rst_rl_147;
    ot_dp_rrelay u_rrl_147 (.clk(clk), .d(rst_rl_146), .q(rst_rl_147));   
    wire rst_rl_148;
    ot_dp_rrelay u_rrl_148 (.clk(clk), .d(rst_rl_147), .q(rst_rl_148));   
    ot_dp_rrelay u_rrl_149 (.clk(clk), .d(rst_rl_148), .q(rst_n_t24));   
    wire rst_rl_150;
    ot_dp_rrelay u_rrl_150 (.clk(clk), .d(rst_rl_132), .q(rst_rl_150));   
    wire rst_rl_151;
    ot_dp_rrelay u_rrl_151 (.clk(clk), .d(rst_rl_150), .q(rst_rl_151));   
    wire rst_rl_152;
    ot_dp_rrelay u_rrl_152 (.clk(clk), .d(rst_rl_151), .q(rst_rl_152));   
    wire rst_rl_153;
    ot_dp_rrelay u_rrl_153 (.clk(clk), .d(rst_rl_152), .q(rst_rl_153));   
    wire rst_rl_154;
    ot_dp_rrelay u_rrl_154 (.clk(clk), .d(rst_rl_153), .q(rst_rl_154));   
    ot_dp_rrelay u_rrl_155 (.clk(clk), .d(rst_rl_154), .q(rst_n_t29));   
    wire rst_rl_156;
    ot_dp_rrelay u_rrl_156 (.clk(clk), .d(rst_rl_153), .q(rst_rl_156));   
    ot_dp_rrelay u_rrl_157 (.clk(clk), .d(rst_rl_156), .q(rst_n_t32));   
    wire rst_rl_158;
    ot_dp_rrelay u_rrl_158 (.clk(clk), .d(rst_root_n), .q(rst_rl_158));   
    wire rst_rl_159;
    ot_dp_rrelay u_rrl_159 (.clk(clk), .d(rst_rl_158), .q(rst_rl_159));   
    wire rst_rl_160;
    ot_dp_rrelay u_rrl_160 (.clk(clk), .d(rst_rl_159), .q(rst_rl_160));   
    wire rst_rl_161;
    ot_dp_rrelay u_rrl_161 (.clk(clk), .d(rst_rl_160), .q(rst_rl_161));   
    wire rst_rl_162;
    ot_dp_rrelay u_rrl_162 (.clk(clk), .d(rst_rl_161), .q(rst_rl_162));   
    wire rst_rl_163;
    ot_dp_rrelay u_rrl_163 (.clk(clk), .d(rst_rl_162), .q(rst_rl_163));   
    wire rst_rl_164;
    ot_dp_rrelay u_rrl_164 (.clk(clk), .d(rst_rl_163), .q(rst_rl_164));   
    ot_dp_rrelay u_rrl_165 (.clk(clk), .d(rst_rl_164), .q(rst_n_t26));   
    wire rst_rl_166;
    ot_dp_rrelay u_rrl_166 (.clk(clk), .d(rst_rl_162), .q(rst_rl_166));   
    wire rst_rl_167;
    ot_dp_rrelay u_rrl_167 (.clk(clk), .d(rst_rl_166), .q(rst_rl_167));   
    ot_dp_rrelay u_rrl_168 (.clk(clk), .d(rst_rl_167), .q(rst_n_t31));   
    wire rst_rl_169;
    ot_dp_rrelay u_rrl_169 (.clk(clk), .d(rst_root_n), .q(rst_rl_169));   
    wire rst_rl_170;
    ot_dp_rrelay u_rrl_170 (.clk(clk), .d(rst_rl_169), .q(rst_rl_170));   
    wire rst_rl_171;
    ot_dp_rrelay u_rrl_171 (.clk(clk), .d(rst_rl_170), .q(rst_rl_171));   
    wire rst_rl_172;
    ot_dp_rrelay u_rrl_172 (.clk(clk), .d(rst_rl_171), .q(rst_rl_172));   
    wire rst_rl_173;
    ot_dp_rrelay u_rrl_173 (.clk(clk), .d(rst_rl_172), .q(rst_rl_173));   
    wire rst_rl_174;
    ot_dp_rrelay u_rrl_174 (.clk(clk), .d(rst_rl_173), .q(rst_rl_174));   
    wire rst_rl_175;
    ot_dp_rrelay u_rrl_175 (.clk(clk), .d(rst_rl_174), .q(rst_rl_175));   
    ot_dp_rrelay u_rrl_176 (.clk(clk), .d(rst_rl_175), .q(rst_n_t28));   
    wire rst_rl_177;
    ot_dp_rrelay u_rrl_177 (.clk(clk), .d(rst_root_n), .q(rst_rl_177));   
    wire rst_rl_178;
    ot_dp_rrelay u_rrl_178 (.clk(clk), .d(rst_rl_177), .q(rst_rl_178));   
    wire rst_rl_179;
    ot_dp_rrelay u_rrl_179 (.clk(clk), .d(rst_rl_178), .q(rst_rl_179));   
    wire rst_rl_180;
    ot_dp_rrelay u_rrl_180 (.clk(clk), .d(rst_rl_179), .q(rst_rl_180));   
    wire rst_rl_181;
    ot_dp_rrelay u_rrl_181 (.clk(clk), .d(rst_rl_180), .q(rst_rl_181));   
    wire rst_rl_182;
    ot_dp_rrelay u_rrl_182 (.clk(clk), .d(rst_rl_181), .q(rst_rl_182));   
    wire rst_rl_183;
    ot_dp_rrelay u_rrl_183 (.clk(clk), .d(rst_rl_182), .q(rst_rl_183));   
    ot_dp_rrelay u_rrl_184 (.clk(clk), .d(rst_rl_183), .q(rst_n_t30));   
    wire rst_rl_185;
    ot_dp_rrelay u_rrl_185 (.clk(clk), .d(rst_rl_178), .q(rst_rl_185));   
    wire rst_rl_186;
    ot_dp_rrelay u_rrl_186 (.clk(clk), .d(rst_rl_185), .q(rst_rl_186));   
    wire rst_rl_187;
    ot_dp_rrelay u_rrl_187 (.clk(clk), .d(rst_rl_186), .q(rst_rl_187));   
    wire rst_rl_188;
    ot_dp_rrelay u_rrl_188 (.clk(clk), .d(rst_rl_187), .q(rst_rl_188));   
    wire rst_rl_189;
    ot_dp_rrelay u_rrl_189 (.clk(clk), .d(rst_rl_188), .q(rst_rl_189));   
    ot_dp_rrelay u_rrl_190 (.clk(clk), .d(rst_rl_189), .q(rst_n_t39));   
    ot_dp_rrelay u_rrl_191 (.clk(clk), .d(rst_rl_189), .q(rst_n_t40));   
    wire rst_rl_192;
    ot_dp_rrelay u_rrl_192 (.clk(clk), .d(rst_root_n), .q(rst_rl_192));   
    wire rst_rl_193;
    ot_dp_rrelay u_rrl_193 (.clk(clk), .d(rst_rl_192), .q(rst_rl_193));   
    wire rst_rl_194;
    ot_dp_rrelay u_rrl_194 (.clk(clk), .d(rst_rl_193), .q(rst_rl_194));   
    wire rst_rl_195;
    ot_dp_rrelay u_rrl_195 (.clk(clk), .d(rst_rl_194), .q(rst_rl_195));   
    wire rst_rl_196;
    ot_dp_rrelay u_rrl_196 (.clk(clk), .d(rst_rl_195), .q(rst_rl_196));   
    wire rst_rl_197;
    ot_dp_rrelay u_rrl_197 (.clk(clk), .d(rst_rl_196), .q(rst_rl_197));   
    wire rst_rl_198;
    ot_dp_rrelay u_rrl_198 (.clk(clk), .d(rst_rl_197), .q(rst_rl_198));   
    ot_dp_rrelay u_rrl_199 (.clk(clk), .d(rst_rl_198), .q(rst_n_t33));   
    wire rst_n = rst_n_t16;
    ot_dp_st #(.W(4401)) u_bin_L11_i (.clk(clk), .rst_n(rst_n), .d(L11_i[4400:0]), .ea(L11_i[4401]), .q(L11_i_q), .eq(L11_i_eq));
    ot_dp_st #(.W(4512)) u_bin_L161m_i (.clk(clk), .rst_n(rst_n), .d(L161m_i[4511:0]), .ea(L161m_i[4512]), .q(L161m_i_q), .eq(L161m_i_eq));
    ot_dp_st #(.W(72)) u_bin_L186m_i (.clk(clk), .rst_n(rst_n), .d(L186m_i[71:0]), .ea(L186m_i[72]), .q(L186m_i_q), .eq(L186m_i_eq));
    ot_dp_st #(.W(1756)) u_bout_L175m_o (.clk(clk), .rst_n(rst_n), .d({w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_u_qlate_q[568:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_g_delivered_reset_u_rr_rst_n[3:2], w_u_hb_idx_s_Q2_r0c3_k2h0_cs_out[31:0], w_u_hb_idx_s_Q2_r0c3_k2h0_cf_out[0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71532_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71531_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71530_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71529_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71528_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71527_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71526_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71525_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71524_Q[2175:1088]}), .ea(rst_n), .q(L175m_o[1755:0]), .eq(L175m_o[1756]));
    ot_dp_st #(.W(569)) u_bout_L183m_o (.clk(clk), .rst_n(rst_n), .d({w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71556_Q[29:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71553_Q[0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71551_Q[0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71549_Q[551], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71549_Q[545:413], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71549_Q[407:275], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71549_Q[269:0]}), .ea(rst_n), .q(L183m_o[568:0]), .eq(L183m_o[569]));
    ot_dp_st #(.W(35)) u_bout_L188m_o (.clk(clk), .rst_n(rst_n), .d({w_u_hb_idx_s_Q2_r0c0_k3h1_prdy[1:0], w_u_hb_idx_s_Q2_r0c0_k3h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c0_k3h1_cf_out[0]}), .ea(rst_n), .q(L188m_o[34:0]), .eq(L188m_o[35]));
    ot_dp_st #(.W(1)) u_bout_L190m_o (.clk(clk), .rst_n(rst_n), .d(w_u_hcb_Q7_u_c_procdff_66869_Q[0]), .ea(rst_n), .q(L190m_o[0:0]), .eq(L190m_o[1]));
    ot_dp_st #(.W(4097)) u_bout_L20_o (.clk(clk), .rst_n(rst_n), .d({w_u_hcb_Q7_u_c_procdff_66849_Q[0], w_u_hcb_Q7_u_c_procdff_66844_Q[4095:0]}), .ea(rst_n), .q(L20_o[4096:0]), .eq(L20_o[4097]));
    ot_dp_st #(.W(21)) u_ft_L101x2_o_0 (.clk(clk), .rst_n(rst_n), .d(L101x2_i[20:0]), .ea(L101x2_i[21]), .q(L101x2_o_s0[20:0]), .eq(L101x2_o_s0[21]));
    ot_dp_st #(.W(21)) u_ft_L101x2_o_1 (.clk(clk), .rst_n(rst_n), .d(L101x2_o_s0[20:0]), .ea(L101x2_o_s0[21]), .q(L101x2_o_s1[20:0]), .eq(L101x2_o_s1[21]));
    ot_dp_st #(.W(21)) u_ft_L101x2_o_2 (.clk(clk), .rst_n(rst_n), .d(L101x2_o_s1[20:0]), .ea(L101x2_o_s1[21]), .q(L101x2_o_s2[20:0]), .eq(L101x2_o_s2[21]));
    ot_dp_st #(.W(21)) u_ft_L101x2_o_3 (.clk(clk), .rst_n(rst_n), .d(L101x2_o_s2[20:0]), .ea(L101x2_o_s2[21]), .q(L101x2_o[20:0]), .eq(L101x2_o[21]));
    ot_dp_st #(.W(5)) u_ft_L126x7_o_0 (.clk(clk), .rst_n(rst_n), .d(L126x7_i[4:0]), .ea(L126x7_i[5]), .q(L126x7_o_s0[4:0]), .eq(L126x7_o_s0[5]));
    ot_dp_st #(.W(5)) u_ft_L126x7_o_1 (.clk(clk), .rst_n(rst_n), .d(L126x7_o_s0[4:0]), .ea(L126x7_o_s0[5]), .q(L126x7_o_s1[4:0]), .eq(L126x7_o_s1[5]));
    ot_dp_st #(.W(5)) u_ft_L126x7_o_2 (.clk(clk), .rst_n(rst_n), .d(L126x7_o_s1[4:0]), .ea(L126x7_o_s1[5]), .q(L126x7_o_s2[4:0]), .eq(L126x7_o_s2[5]));
    ot_dp_st #(.W(5)) u_ft_L126x7_o_3 (.clk(clk), .rst_n(rst_n), .d(L126x7_o_s2[4:0]), .ea(L126x7_o_s2[5]), .q(L126x7_o[4:0]), .eq(L126x7_o[5]));
    ot_dp_st #(.W(4127)) u_ft_L14x1_o_0 (.clk(clk), .rst_n(rst_n), .d(L14x1_i[4126:0]), .ea(L14x1_i[4127]), .q(L14x1_o_s0[4126:0]), .eq(L14x1_o_s0[4127]));
    ot_dp_st #(.W(4127)) u_ft_L14x1_o_1 (.clk(clk), .rst_n(rst_n), .d(L14x1_o_s0[4126:0]), .ea(L14x1_o_s0[4127]), .q(L14x1_o_s1[4126:0]), .eq(L14x1_o_s1[4127]));
    ot_dp_st #(.W(4127)) u_ft_L14x1_o_2 (.clk(clk), .rst_n(rst_n), .d(L14x1_o_s1[4126:0]), .ea(L14x1_o_s1[4127]), .q(L14x1_o_s2[4126:0]), .eq(L14x1_o_s2[4127]));
    ot_dp_st #(.W(4127)) u_ft_L14x1_o_3 (.clk(clk), .rst_n(rst_n), .d(L14x1_o_s2[4126:0]), .ea(L14x1_o_s2[4127]), .q(L14x1_o_s3[4126:0]), .eq(L14x1_o_s3[4127]));
    ot_dp_st #(.W(4127)) u_ft_L14x1_o_4 (.clk(clk), .rst_n(rst_n), .d(L14x1_o_s3[4126:0]), .ea(L14x1_o_s3[4127]), .q(L14x1_o_s4[4126:0]), .eq(L14x1_o_s4[4127]));
    ot_dp_st #(.W(4127)) u_ft_L14x1_o_5 (.clk(clk), .rst_n(rst_n), .d(L14x1_o_s4[4126:0]), .ea(L14x1_o_s4[4127]), .q(L14x1_o[4126:0]), .eq(L14x1_o[4127]));
    ot_dp_st #(.W(1389)) u_ft_L167mx1_o_0 (.clk(clk), .rst_n(rst_n), .d(L167mx1_i[1388:0]), .ea(L167mx1_i[1389]), .q(L167mx1_o_s0[1388:0]), .eq(L167mx1_o_s0[1389]));
    ot_dp_st #(.W(1389)) u_ft_L167mx1_o_1 (.clk(clk), .rst_n(rst_n), .d(L167mx1_o_s0[1388:0]), .ea(L167mx1_o_s0[1389]), .q(L167mx1_o_s1[1388:0]), .eq(L167mx1_o_s1[1389]));
    ot_dp_st #(.W(1389)) u_ft_L167mx1_o_2 (.clk(clk), .rst_n(rst_n), .d(L167mx1_o_s1[1388:0]), .ea(L167mx1_o_s1[1389]), .q(L167mx1_o_s2[1388:0]), .eq(L167mx1_o_s2[1389]));
    ot_dp_st #(.W(1389)) u_ft_L167mx1_o_3 (.clk(clk), .rst_n(rst_n), .d(L167mx1_o_s2[1388:0]), .ea(L167mx1_o_s2[1389]), .q(L167mx1_o_s3[1388:0]), .eq(L167mx1_o_s3[1389]));
    ot_dp_st #(.W(1389)) u_ft_L167mx1_o_4 (.clk(clk), .rst_n(rst_n), .d(L167mx1_o_s3[1388:0]), .ea(L167mx1_o_s3[1389]), .q(L167mx1_o_s4[1388:0]), .eq(L167mx1_o_s4[1389]));
    ot_dp_st #(.W(1389)) u_ft_L167mx1_o_5 (.clk(clk), .rst_n(rst_n), .d(L167mx1_o_s4[1388:0]), .ea(L167mx1_o_s4[1389]), .q(L167mx1_o[1388:0]), .eq(L167mx1_o[1389]));
    ot_dp_st #(.W(1388)) u_ft_L168mx1_o_0 (.clk(clk), .rst_n(rst_n), .d(L168mx1_i[1387:0]), .ea(L168mx1_i[1388]), .q(L168mx1_o_s0[1387:0]), .eq(L168mx1_o_s0[1388]));
    ot_dp_st #(.W(1388)) u_ft_L168mx1_o_1 (.clk(clk), .rst_n(rst_n), .d(L168mx1_o_s0[1387:0]), .ea(L168mx1_o_s0[1388]), .q(L168mx1_o_s1[1387:0]), .eq(L168mx1_o_s1[1388]));
    ot_dp_st #(.W(1388)) u_ft_L168mx1_o_2 (.clk(clk), .rst_n(rst_n), .d(L168mx1_o_s1[1387:0]), .ea(L168mx1_o_s1[1388]), .q(L168mx1_o_s2[1387:0]), .eq(L168mx1_o_s2[1388]));
    ot_dp_st #(.W(1388)) u_ft_L168mx1_o_3 (.clk(clk), .rst_n(rst_n), .d(L168mx1_o_s2[1387:0]), .ea(L168mx1_o_s2[1388]), .q(L168mx1_o_s3[1387:0]), .eq(L168mx1_o_s3[1388]));
    ot_dp_st #(.W(1388)) u_ft_L168mx1_o_4 (.clk(clk), .rst_n(rst_n), .d(L168mx1_o_s3[1387:0]), .ea(L168mx1_o_s3[1388]), .q(L168mx1_o_s4[1387:0]), .eq(L168mx1_o_s4[1388]));
    ot_dp_st #(.W(1388)) u_ft_L168mx1_o_5 (.clk(clk), .rst_n(rst_n), .d(L168mx1_o_s4[1387:0]), .ea(L168mx1_o_s4[1388]), .q(L168mx1_o[1387:0]), .eq(L168mx1_o[1388]));
    ot_dp_st #(.W(1)) u_ft_L204mx1_o_0 (.clk(clk), .rst_n(rst_n), .d(L204mx1_i[0:0]), .ea(L204mx1_i[1]), .q(L204mx1_o_s0[0:0]), .eq(L204mx1_o_s0[1]));
    ot_dp_st #(.W(1)) u_ft_L204mx1_o_1 (.clk(clk), .rst_n(rst_n), .d(L204mx1_o_s0[0:0]), .ea(L204mx1_o_s0[1]), .q(L204mx1_o_s1[0:0]), .eq(L204mx1_o_s1[1]));
    ot_dp_st #(.W(1)) u_ft_L204mx1_o_2 (.clk(clk), .rst_n(rst_n), .d(L204mx1_o_s1[0:0]), .ea(L204mx1_o_s1[1]), .q(L204mx1_o_s2[0:0]), .eq(L204mx1_o_s2[1]));
    ot_dp_st #(.W(1)) u_ft_L204mx1_o_3 (.clk(clk), .rst_n(rst_n), .d(L204mx1_o_s2[0:0]), .ea(L204mx1_o_s2[1]), .q(L204mx1_o[0:0]), .eq(L204mx1_o[1]));
    ot_dp_st #(.W(1)) u_ft_L205mx1_o_0 (.clk(clk), .rst_n(rst_n), .d(L205mx1_i[0:0]), .ea(L205mx1_i[1]), .q(L205mx1_o_s0[0:0]), .eq(L205mx1_o_s0[1]));
    ot_dp_st #(.W(1)) u_ft_L205mx1_o_1 (.clk(clk), .rst_n(rst_n), .d(L205mx1_o_s0[0:0]), .ea(L205mx1_o_s0[1]), .q(L205mx1_o_s1[0:0]), .eq(L205mx1_o_s1[1]));
    ot_dp_st #(.W(1)) u_ft_L205mx1_o_2 (.clk(clk), .rst_n(rst_n), .d(L205mx1_o_s1[0:0]), .ea(L205mx1_o_s1[1]), .q(L205mx1_o_s2[0:0]), .eq(L205mx1_o_s2[1]));
    ot_dp_st #(.W(1)) u_ft_L205mx1_o_3 (.clk(clk), .rst_n(rst_n), .d(L205mx1_o_s2[0:0]), .ea(L205mx1_o_s2[1]), .q(L205mx1_o[0:0]), .eq(L205mx1_o[1]));
    ot_dp_st #(.W(1615)) u_ft_L28x2_o_0 (.clk(clk), .rst_n(rst_n), .d(L28x2_i[1614:0]), .ea(L28x2_i[1615]), .q(L28x2_o_s0[1614:0]), .eq(L28x2_o_s0[1615]));
    ot_dp_st #(.W(1615)) u_ft_L28x2_o_1 (.clk(clk), .rst_n(rst_n), .d(L28x2_o_s0[1614:0]), .ea(L28x2_o_s0[1615]), .q(L28x2_o_s1[1614:0]), .eq(L28x2_o_s1[1615]));
    ot_dp_st #(.W(1615)) u_ft_L28x2_o_2 (.clk(clk), .rst_n(rst_n), .d(L28x2_o_s1[1614:0]), .ea(L28x2_o_s1[1615]), .q(L28x2_o_s2[1614:0]), .eq(L28x2_o_s2[1615]));
    ot_dp_st #(.W(1615)) u_ft_L28x2_o_3 (.clk(clk), .rst_n(rst_n), .d(L28x2_o_s2[1614:0]), .ea(L28x2_o_s2[1615]), .q(L28x2_o_s3[1614:0]), .eq(L28x2_o_s3[1615]));
    ot_dp_st #(.W(1615)) u_ft_L28x2_o_4 (.clk(clk), .rst_n(rst_n), .d(L28x2_o_s3[1614:0]), .ea(L28x2_o_s3[1615]), .q(L28x2_o[1614:0]), .eq(L28x2_o[1615]));
    ot_dp_st #(.W(1329)) u_ft_L36x2_o_0 (.clk(clk), .rst_n(rst_n), .d(L36x2_i[1328:0]), .ea(L36x2_i[1329]), .q(L36x2_o_s0[1328:0]), .eq(L36x2_o_s0[1329]));
    ot_dp_st #(.W(1329)) u_ft_L36x2_o_1 (.clk(clk), .rst_n(rst_n), .d(L36x2_o_s0[1328:0]), .ea(L36x2_o_s0[1329]), .q(L36x2_o_s1[1328:0]), .eq(L36x2_o_s1[1329]));
    ot_dp_st #(.W(1329)) u_ft_L36x2_o_2 (.clk(clk), .rst_n(rst_n), .d(L36x2_o_s1[1328:0]), .ea(L36x2_o_s1[1329]), .q(L36x2_o[1328:0]), .eq(L36x2_o[1329]));
    ot_dp_st #(.W(788)) u_ft_L42x2_o_0 (.clk(clk), .rst_n(rst_n), .d(L42x2_i[787:0]), .ea(L42x2_i[788]), .q(L42x2_o_s0[787:0]), .eq(L42x2_o_s0[788]));
    ot_dp_st #(.W(788)) u_ft_L42x2_o_1 (.clk(clk), .rst_n(rst_n), .d(L42x2_o_s0[787:0]), .ea(L42x2_o_s0[788]), .q(L42x2_o_s1[787:0]), .eq(L42x2_o_s1[788]));
    ot_dp_st #(.W(788)) u_ft_L42x2_o_2 (.clk(clk), .rst_n(rst_n), .d(L42x2_o_s1[787:0]), .ea(L42x2_o_s1[788]), .q(L42x2_o_s2[787:0]), .eq(L42x2_o_s2[788]));
    ot_dp_st #(.W(788)) u_ft_L42x2_o_3 (.clk(clk), .rst_n(rst_n), .d(L42x2_o_s2[787:0]), .ea(L42x2_o_s2[788]), .q(L42x2_o[787:0]), .eq(L42x2_o[788]));
    ot_dp_st #(.W(788)) u_ft_L43x2_o_0 (.clk(clk), .rst_n(rst_n), .d(L43x2_i[787:0]), .ea(L43x2_i[788]), .q(L43x2_o_s0[787:0]), .eq(L43x2_o_s0[788]));
    ot_dp_st #(.W(788)) u_ft_L43x2_o_1 (.clk(clk), .rst_n(rst_n), .d(L43x2_o_s0[787:0]), .ea(L43x2_o_s0[788]), .q(L43x2_o_s1[787:0]), .eq(L43x2_o_s1[788]));
    ot_dp_st #(.W(788)) u_ft_L43x2_o_2 (.clk(clk), .rst_n(rst_n), .d(L43x2_o_s1[787:0]), .ea(L43x2_o_s1[788]), .q(L43x2_o_s2[787:0]), .eq(L43x2_o_s2[788]));
    ot_dp_st #(.W(788)) u_ft_L43x2_o_3 (.clk(clk), .rst_n(rst_n), .d(L43x2_o_s2[787:0]), .ea(L43x2_o_s2[788]), .q(L43x2_o[787:0]), .eq(L43x2_o[788]));
    ot_dp_st #(.W(612)) u_ft_L51x2_o_0 (.clk(clk), .rst_n(rst_n), .d(L51x2_i[611:0]), .ea(L51x2_i[612]), .q(L51x2_o_s0[611:0]), .eq(L51x2_o_s0[612]));
    ot_dp_st #(.W(612)) u_ft_L51x2_o_1 (.clk(clk), .rst_n(rst_n), .d(L51x2_o_s0[611:0]), .ea(L51x2_o_s0[612]), .q(L51x2_o_s1[611:0]), .eq(L51x2_o_s1[612]));
    ot_dp_st #(.W(612)) u_ft_L51x2_o_2 (.clk(clk), .rst_n(rst_n), .d(L51x2_o_s1[611:0]), .ea(L51x2_o_s1[612]), .q(L51x2_o_s2[611:0]), .eq(L51x2_o_s2[612]));
    ot_dp_st #(.W(612)) u_ft_L51x2_o_3 (.clk(clk), .rst_n(rst_n), .d(L51x2_o_s2[611:0]), .ea(L51x2_o_s2[612]), .q(L51x2_o[611:0]), .eq(L51x2_o[612]));
    ot_dp_st #(.W(612)) u_ft_L52x7_o_0 (.clk(clk), .rst_n(rst_n), .d(L52x7_i[611:0]), .ea(L52x7_i[612]), .q(L52x7_o_s0[611:0]), .eq(L52x7_o_s0[612]));
    ot_dp_st #(.W(612)) u_ft_L52x7_o_1 (.clk(clk), .rst_n(rst_n), .d(L52x7_o_s0[611:0]), .ea(L52x7_o_s0[612]), .q(L52x7_o_s1[611:0]), .eq(L52x7_o_s1[612]));
    ot_dp_st #(.W(612)) u_ft_L52x7_o_2 (.clk(clk), .rst_n(rst_n), .d(L52x7_o_s1[611:0]), .ea(L52x7_o_s1[612]), .q(L52x7_o_s2[611:0]), .eq(L52x7_o_s2[612]));
    ot_dp_st #(.W(612)) u_ft_L52x7_o_3 (.clk(clk), .rst_n(rst_n), .d(L52x7_o_s2[611:0]), .ea(L52x7_o_s2[612]), .q(L52x7_o[611:0]), .eq(L52x7_o[612]));
    ot_dp_st #(.W(1662)) u_ft_L730x3_o_0 (.clk(clk), .rst_n(rst_n), .d(L730x3_i[1661:0]), .ea(L730x3_i[1662]), .q(L730x3_o_s0[1661:0]), .eq(L730x3_o_s0[1662]));
    ot_dp_st #(.W(1662)) u_ft_L730x3_o_1 (.clk(clk), .rst_n(rst_n), .d(L730x3_o_s0[1661:0]), .ea(L730x3_o_s0[1662]), .q(L730x3_o_s1[1661:0]), .eq(L730x3_o_s1[1662]));
    ot_dp_st #(.W(1662)) u_ft_L730x3_o_2 (.clk(clk), .rst_n(rst_n), .d(L730x3_o_s1[1661:0]), .ea(L730x3_o_s1[1662]), .q(L730x3_o[1661:0]), .eq(L730x3_o[1662]));
    ot_dp_st #(.W(4)) u_ft_L732x3_o_0 (.clk(clk), .rst_n(rst_n), .d(L732x3_i[3:0]), .ea(L732x3_i[4]), .q(L732x3_o_s0[3:0]), .eq(L732x3_o_s0[4]));
    ot_dp_st #(.W(4)) u_ft_L732x3_o_1 (.clk(clk), .rst_n(rst_n), .d(L732x3_o_s0[3:0]), .ea(L732x3_o_s0[4]), .q(L732x3_o_s1[3:0]), .eq(L732x3_o_s1[4]));
    ot_dp_st #(.W(4)) u_ft_L732x3_o_2 (.clk(clk), .rst_n(rst_n), .d(L732x3_o_s1[3:0]), .ea(L732x3_o_s1[4]), .q(L732x3_o[3:0]), .eq(L732x3_o[4]));
    ot_dp_st #(.W(3)) u_ft_L733x2_o_0 (.clk(clk), .rst_n(rst_n), .d(L733x2_i[2:0]), .ea(L733x2_i[3]), .q(L733x2_o_s0[2:0]), .eq(L733x2_o_s0[3]));
    ot_dp_st #(.W(3)) u_ft_L733x2_o_1 (.clk(clk), .rst_n(rst_n), .d(L733x2_o_s0[2:0]), .ea(L733x2_o_s0[3]), .q(L733x2_o_s1[2:0]), .eq(L733x2_o_s1[3]));
    ot_dp_st #(.W(3)) u_ft_L733x2_o_2 (.clk(clk), .rst_n(rst_n), .d(L733x2_o_s1[2:0]), .ea(L733x2_o_s1[3]), .q(L733x2_o[2:0]), .eq(L733x2_o[3]));
    ot_dp_st #(.W(1)) u_ft_L734x6_o_0 (.clk(clk), .rst_n(rst_n), .d(L734x6_i[0:0]), .ea(L734x6_i[1]), .q(L734x6_o_s0[0:0]), .eq(L734x6_o_s0[1]));
    ot_dp_st #(.W(1)) u_ft_L734x6_o_1 (.clk(clk), .rst_n(rst_n), .d(L734x6_o_s0[0:0]), .ea(L734x6_o_s0[1]), .q(L734x6_o_s1[0:0]), .eq(L734x6_o_s1[1]));
    ot_dp_st #(.W(1)) u_ft_L734x6_o_2 (.clk(clk), .rst_n(rst_n), .d(L734x6_o_s1[0:0]), .ea(L734x6_o_s1[1]), .q(L734x6_o[0:0]), .eq(L734x6_o[1]));
    ot_dp_st #(.W(1)) u_ft_L735x4_o_0 (.clk(clk), .rst_n(rst_n), .d(L735x4_i[0:0]), .ea(L735x4_i[1]), .q(L735x4_o_s0[0:0]), .eq(L735x4_o_s0[1]));
    ot_dp_st #(.W(1)) u_ft_L735x4_o_1 (.clk(clk), .rst_n(rst_n), .d(L735x4_o_s0[0:0]), .ea(L735x4_o_s0[1]), .q(L735x4_o_s1[0:0]), .eq(L735x4_o_s1[1]));
    ot_dp_st #(.W(1)) u_ft_L735x4_o_2 (.clk(clk), .rst_n(rst_n), .d(L735x4_o_s1[0:0]), .ea(L735x4_o_s1[1]), .q(L735x4_o_s2[0:0]), .eq(L735x4_o_s2[1]));
    ot_dp_st #(.W(1)) u_ft_L735x4_o_3 (.clk(clk), .rst_n(rst_n), .d(L735x4_o_s2[0:0]), .ea(L735x4_o_s2[1]), .q(L735x4_o_s3[0:0]), .eq(L735x4_o_s3[1]));
    ot_dp_st #(.W(1)) u_ft_L735x4_o_4 (.clk(clk), .rst_n(rst_n), .d(L735x4_o_s3[0:0]), .ea(L735x4_o_s3[1]), .q(L735x4_o_s4[0:0]), .eq(L735x4_o_s4[1]));
    ot_dp_st #(.W(1)) u_ft_L735x4_o_5 (.clk(clk), .rst_n(rst_n), .d(L735x4_o_s4[0:0]), .ea(L735x4_o_s4[1]), .q(L735x4_o_s5[0:0]), .eq(L735x4_o_s5[1]));
    ot_dp_st #(.W(1)) u_ft_L735x4_o_6 (.clk(clk), .rst_n(rst_n), .d(L735x4_o_s5[0:0]), .ea(L735x4_o_s5[1]), .q(L735x4_o_s6[0:0]), .eq(L735x4_o_s6[1]));
    ot_dp_st #(.W(1)) u_ft_L735x4_o_7 (.clk(clk), .rst_n(rst_n), .d(L735x4_o_s6[0:0]), .ea(L735x4_o_s6[1]), .q(L735x4_o_s7[0:0]), .eq(L735x4_o_s7[1]));
    ot_dp_st #(.W(1)) u_ft_L735x4_o_8 (.clk(clk), .rst_n(rst_n), .d(L735x4_o_s7[0:0]), .ea(L735x4_o_s7[1]), .q(L735x4_o_s8[0:0]), .eq(L735x4_o_s8[1]));
    ot_dp_st #(.W(1)) u_ft_L735x4_o_9 (.clk(clk), .rst_n(rst_n), .d(L735x4_o_s8[0:0]), .ea(L735x4_o_s8[1]), .q(L735x4_o_s9[0:0]), .eq(L735x4_o_s9[1]));
    ot_dp_st #(.W(1)) u_ft_L735x4_o_10 (.clk(clk), .rst_n(rst_n), .d(L735x4_o_s9[0:0]), .ea(L735x4_o_s9[1]), .q(L735x4_o_s10[0:0]), .eq(L735x4_o_s10[1]));
    ot_dp_st #(.W(1)) u_ft_L735x4_o_11 (.clk(clk), .rst_n(rst_n), .d(L735x4_o_s10[0:0]), .ea(L735x4_o_s10[1]), .q(L735x4_o[0:0]), .eq(L735x4_o[1]));
    ot_dp_st #(.W(274)) u_ft_L73x2_o_0 (.clk(clk), .rst_n(rst_n), .d(L73x2_i[273:0]), .ea(L73x2_i[274]), .q(L73x2_o_s0[273:0]), .eq(L73x2_o_s0[274]));
    ot_dp_st #(.W(274)) u_ft_L73x2_o_1 (.clk(clk), .rst_n(rst_n), .d(L73x2_o_s0[273:0]), .ea(L73x2_o_s0[274]), .q(L73x2_o_s1[273:0]), .eq(L73x2_o_s1[274]));
    ot_dp_st #(.W(274)) u_ft_L73x2_o_2 (.clk(clk), .rst_n(rst_n), .d(L73x2_o_s1[273:0]), .ea(L73x2_o_s1[274]), .q(L73x2_o_s2[273:0]), .eq(L73x2_o_s2[274]));
    ot_dp_st #(.W(274)) u_ft_L73x2_o_3 (.clk(clk), .rst_n(rst_n), .d(L73x2_o_s2[273:0]), .ea(L73x2_o_s2[274]), .q(L73x2_o[273:0]), .eq(L73x2_o[274]));
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54724_Y = !w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71563_Q[4:3];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54726_Y = 2'b01 == w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71563_Q[4:3];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54728_Y = 2'b10 == w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71563_Q[4:3];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54730_Y = {2{1'b1}} == w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71563_Q[4:3];   
    reg [31:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71548_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71548_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71548_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71548_q <= 32'b00000000000000000000000000000100;   
    reg [551:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71549_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71549_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71549_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71549_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71550_Q[551:0];   
    reg [551:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71550_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71550_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71550_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71550_q <= {w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__da7629f4[137:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__5eb5a230[137:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__f60b7f7f[137:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__fbfcce2b[137:0]};   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71551_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71551_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71551_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71551_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71557_Q[0];   
    reg [567:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71552_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71552_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71552_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71552_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71558_Q[567:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71553_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71553_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71553_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71553_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71559_Q[0];   
    reg [3:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71554_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71554_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71554_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71554_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71560_Q[3:0];   
    reg [2175:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71555_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71555_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71555_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71555_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71561_Q[2175:0];   
    reg [29:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71556_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71556_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71556_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71556_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71562_Q[29:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71557_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71557_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71557_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71557_q <= L161m_i_q[553];   
    reg [567:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71558_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71558_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71558_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71558_q <= L161m_i_q[1121:554];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71559_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71559_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71559_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71559_q <= L161m_i_q[1122];   
    reg [3:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71560_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71560_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71560_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71560_q <= L161m_i_q[1126:1123];   
    reg [2175:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71561_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71561_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71561_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71561_q <= L161m_i_q[3302:1127];   
    reg [29:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71562_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71562_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71562_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71562_q <= L161m_i_q[3332:3303];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71563_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71563_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71563_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71563_q <= 8'b00001000;   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__fbfcce2b = w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54724_Y[0] ? {w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71537_Q[0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_vl_q[4:1], w_u_hb_idx_s_Q2_r0c1_k3h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c1_k2h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c1_k1h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c1_k0h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c1_k3h1_cf_out[0], w_u_hb_idx_s_Q2_r0c1_k2h1_cf_out[0], w_u_hb_idx_s_Q2_r0c1_k1h1_cf_out[0], w_u_hb_idx_s_Q2_r0c1_k0h1_cf_out[0]} : L161m_i_q[138:1];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__f60b7f7f = w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54726_Y[0] ? {w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71537_Q[0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_vl_q[4:1], w_u_hb_idx_s_Q2_r0c1_k3h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c1_k2h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c1_k1h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c1_k0h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c1_k3h1_cf_out[0], w_u_hb_idx_s_Q2_r0c1_k2h1_cf_out[0], w_u_hb_idx_s_Q2_r0c1_k1h1_cf_out[0], w_u_hb_idx_s_Q2_r0c1_k0h1_cf_out[0]} : L161m_i_q[276:139];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__5eb5a230 = w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54728_Y[0] ? {w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71537_Q[0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_vl_q[4:1], w_u_hb_idx_s_Q2_r0c1_k3h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c1_k2h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c1_k1h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c1_k0h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c1_k3h1_cf_out[0], w_u_hb_idx_s_Q2_r0c1_k2h1_cf_out[0], w_u_hb_idx_s_Q2_r0c1_k1h1_cf_out[0], w_u_hb_idx_s_Q2_r0c1_k0h1_cf_out[0]} : L161m_i_q[414:277];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__da7629f4 = w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54730_Y[0] ? {w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71537_Q[0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_vl_q[4:1], w_u_hb_idx_s_Q2_r0c1_k3h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c1_k2h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c1_k1h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c1_k0h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c1_k3h1_cf_out[0], w_u_hb_idx_s_Q2_r0c1_k2h1_cf_out[0], w_u_hb_idx_s_Q2_r0c1_k1h1_cf_out[0], w_u_hb_idx_s_Q2_r0c1_k0h1_cf_out[0]} : L161m_i_q[552:415];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55671_Y = w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71521_Q[7:0] + {8{1'b0}};   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55672_Y = w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71521_Q[7:0] + 8'b00000001;   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55673_Y = w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71521_Q[7:0] + 8'b00000010;   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55674_Y = w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71521_Q[7:0] + 8'b00000011;   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55675_Y = w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71521_Q[7:0] + 8'b00000100;   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55676_Y = w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71521_Q[7:0] + 8'b00000101;   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55677_Y = w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71521_Q[7:0] + 8'b00000110;   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55678_Y = w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71521_Q[7:0] + 8'b00000111;   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_auto_proc_dff_cc_220_proc_dff_71533_Y = ~L161m_i_q[0];
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_auto_proc_dff_cc_220_proc_dff_71538_Y = ~L161m_i_q[0];
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_auto_proc_dff_cc_220_proc_dff_71543_Y = ~L161m_i_q[0];
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y = w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71557_Q[0] && w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[4];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_167_55670_Y = w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71559_Q[0] && w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[4];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y = w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_vl_q[0] && w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[4];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_logic_not_ot_hbm_idx_chunk_rt_h_sv_154_55666_Y = !L161m_i_q[0];   
    reg [31:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71508_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71508_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71508_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71508_q <= w_u_hb_idx_s_Q2_r0c1_k3h1_cs_out[31:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71509_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71509_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71509_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71509_q <= w_u_hb_idx_s_Q2_r0c1_k3h1_cf_out[0];   
    reg [31:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71510_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71510_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71510_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71510_q <= w_u_hb_idx_s_Q2_r0c1_k2h1_cs_out[31:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71511_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71511_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71511_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71511_q <= w_u_hb_idx_s_Q2_r0c1_k2h1_cf_out[0];   
    reg [31:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71512_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71512_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71512_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71512_q <= w_u_hb_idx_s_Q2_r0c1_k1h1_cs_out[31:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71513_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71513_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71513_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71513_q <= w_u_hb_idx_s_Q2_r0c1_k1h1_cf_out[0];   
    reg [31:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71514_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71514_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71514_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71514_q <= w_u_hb_idx_s_Q2_r0c1_k0h1_cs_out[31:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71515_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71515_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71515_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71515_q <= w_u_hb_idx_s_Q2_r0c1_k0h1_cf_out[0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71516_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71516_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71516_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71516_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0];   
    reg [3:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71517_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71517_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71517_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71517_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_vl_q[4:1];   
    reg [31:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71518_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71518_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71518_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71518_q <= 32'b00000000000000000000000000001000;   
    reg [567:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71519_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71519_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71519_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71519_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71558_Q[567:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71520_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71520_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71520_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71520_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_167_55670_Y[0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71521_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71521_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71521_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71521_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71563_Q[7:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71522_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71522_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71522_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71522_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0];   
    reg [3:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71523_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71523_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71523_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71523_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71560_Q[3:0];   
    reg [2175:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71524_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71524_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71524_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71524_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71561_Q[2175:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71525_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71525_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71525_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71525_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55671_Y[7:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71526_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71526_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71526_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71526_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55672_Y[7:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71527_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71527_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71527_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71527_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55673_Y[7:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71528_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71528_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71528_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71528_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55674_Y[7:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71529_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71529_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71529_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71529_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55675_Y[7:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71530_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71530_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71530_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71530_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55676_Y[7:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71531_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71531_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71531_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71531_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55677_Y[7:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71532_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71532_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71532_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71532_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55678_Y[7:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71537_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71537_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71537_q;
    always @(posedge clk or negedge L161m_i_q[0])
        if (!L161m_i_q[0]) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71537_q <= 1'b0; else g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71537_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_reduce_and_ot_hbm_idx_chunk_rt_h_sv_155_55667_Y[0];   
    reg [15:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71542_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71542_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71542_q;
    always @(posedge clk or negedge L161m_i_q[0])
        if (!L161m_i_q[0]) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71542_q <= 16'b0000000000000000; else g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71542_q <= {w_u_hb_idx_s_Q2_r0c1_k3h1_prdy[1:0], w_u_hb_idx_s_Q2_r0c1_k3h0_prdy[1:0], w_u_hb_idx_s_Q2_r0c1_k2h1_prdy[1:0], w_u_hb_idx_s_Q2_r0c1_k2h0_prdy[1:0], w_u_hb_idx_s_Q2_r0c1_k1h1_prdy[1:0], w_u_hb_idx_s_Q2_r0c1_k1h0_prdy[1:0], w_u_hb_idx_s_Q2_r0c1_k0h1_prdy[1:0], w_u_hb_idx_s_Q2_r0c1_k0h0_prdy[1:0]};   
    reg [15:0] g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71547_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71547_Q = g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71547_q;
    always @(posedge clk or negedge L161m_i_q[0])
        if (!L161m_i_q[0]) g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71547_q <= 16'b0000000000000000; else g_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71547_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71542_Q[15:0];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_reduce_and_ot_hbm_idx_chunk_rt_h_sv_155_55667_Y = &w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71547_Q[15:0];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54724_Y = !w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71563_Q[4:3];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54726_Y = 2'b01 == w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71563_Q[4:3];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54728_Y = 2'b10 == w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71563_Q[4:3];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54730_Y = {2{1'b1}} == w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71563_Q[4:3];   
    reg [31:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71548_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71548_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71548_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71548_q <= 32'b00000000000000000000000000000100;   
    reg [551:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71549_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71549_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71549_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71549_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71550_Q[551:0];   
    reg [551:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71550_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71550_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71550_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71550_q <= {w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__334ecc88[137:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__6c41aa0b[137:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__58d9bac9[137:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__2e9bf0c8[137:0]};   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71551_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71551_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71551_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71551_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71557_Q[0];   
    reg [567:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71552_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71552_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71552_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71552_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71558_Q[567:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71553_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71553_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71553_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71553_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71559_Q[0];   
    reg [3:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71554_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71554_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71554_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71554_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71560_Q[3:0];   
    reg [2175:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71555_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71555_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71555_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71555_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71561_Q[2175:0];   
    reg [29:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71556_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71556_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71556_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71556_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71562_Q[29:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71557_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71557_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71557_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71557_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71551_Q[0];   
    reg [567:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71558_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71558_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71558_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71558_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71552_Q[567:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71559_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71559_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71559_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71559_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71553_Q[0];   
    reg [3:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71560_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71560_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71560_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71560_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71554_Q[3:0];   
    reg [2175:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71561_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71561_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71561_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71561_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71555_Q[2175:0];   
    reg [29:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71562_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71562_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71562_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71562_q <= w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71556_Q[29:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71563_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71563_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71563_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71563_q <= 8'b00010000;   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__2e9bf0c8 = w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54724_Y[0] ? {w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71537_Q[0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_vl_q[4:1], w_u_hb_idx_s_Q2_r0c2_k3h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c2_k2h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c2_k1h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c2_k0h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c2_k3h1_cf_out[0], w_u_hb_idx_s_Q2_r0c2_k2h1_cf_out[0], w_u_hb_idx_s_Q2_r0c2_k1h1_cf_out[0], w_u_hb_idx_s_Q2_r0c2_k0h1_cf_out[0]} : w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71549_Q[137:0];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__58d9bac9 = w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54726_Y[0] ? {w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71537_Q[0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_vl_q[4:1], w_u_hb_idx_s_Q2_r0c2_k3h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c2_k2h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c2_k1h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c2_k0h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c2_k3h1_cf_out[0], w_u_hb_idx_s_Q2_r0c2_k2h1_cf_out[0], w_u_hb_idx_s_Q2_r0c2_k1h1_cf_out[0], w_u_hb_idx_s_Q2_r0c2_k0h1_cf_out[0]} : w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71549_Q[275:138];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__6c41aa0b = w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54728_Y[0] ? {w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71537_Q[0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_vl_q[4:1], w_u_hb_idx_s_Q2_r0c2_k3h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c2_k2h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c2_k1h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c2_k0h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c2_k3h1_cf_out[0], w_u_hb_idx_s_Q2_r0c2_k2h1_cf_out[0], w_u_hb_idx_s_Q2_r0c2_k1h1_cf_out[0], w_u_hb_idx_s_Q2_r0c2_k0h1_cf_out[0]} : w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71549_Q[413:276];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__334ecc88 = w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54730_Y[0] ? {w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71537_Q[0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_vl_q[4:1], w_u_hb_idx_s_Q2_r0c2_k3h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c2_k2h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c2_k1h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c2_k0h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c2_k3h1_cf_out[0], w_u_hb_idx_s_Q2_r0c2_k2h1_cf_out[0], w_u_hb_idx_s_Q2_r0c2_k1h1_cf_out[0], w_u_hb_idx_s_Q2_r0c2_k0h1_cf_out[0]} : w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_procdff_71549_Q[551:414];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55671_Y = w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71521_Q[7:0] + {8{1'b0}};   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55672_Y = w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71521_Q[7:0] + 8'b00000001;   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55673_Y = w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71521_Q[7:0] + 8'b00000010;   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55674_Y = w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71521_Q[7:0] + 8'b00000011;   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55675_Y = w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71521_Q[7:0] + 8'b00000100;   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55676_Y = w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71521_Q[7:0] + 8'b00000101;   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55677_Y = w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71521_Q[7:0] + 8'b00000110;   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55678_Y = w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71521_Q[7:0] + 8'b00000111;   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_auto_proc_dff_cc_220_proc_dff_71533_Y = ~L161m_i_q[0];
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_auto_proc_dff_cc_220_proc_dff_71538_Y = ~L161m_i_q[0];
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_auto_proc_dff_cc_220_proc_dff_71543_Y = ~L161m_i_q[0];
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y = w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71557_Q[0] && w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_g_delivered_reset_u_rr_rst_n[4];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_167_55670_Y = w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71559_Q[0] && w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_g_delivered_reset_u_rr_rst_n[4];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y = w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_vl_q[0] && w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_g_delivered_reset_u_rr_rst_n[4];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_logic_not_ot_hbm_idx_chunk_rt_h_sv_154_55666_Y = !L161m_i_q[0];   
    reg [31:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71508_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71508_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71508_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71508_q <= w_u_hb_idx_s_Q2_r0c2_k3h1_cs_out[31:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71509_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71509_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71509_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71509_q <= w_u_hb_idx_s_Q2_r0c2_k3h1_cf_out[0];   
    reg [31:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71510_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71510_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71510_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71510_q <= w_u_hb_idx_s_Q2_r0c2_k2h1_cs_out[31:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71511_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71511_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71511_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71511_q <= w_u_hb_idx_s_Q2_r0c2_k2h1_cf_out[0];   
    reg [31:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71512_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71512_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71512_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71512_q <= w_u_hb_idx_s_Q2_r0c2_k1h1_cs_out[31:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71513_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71513_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71513_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71513_q <= w_u_hb_idx_s_Q2_r0c2_k1h1_cf_out[0];   
    reg [31:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71514_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71514_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71514_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71514_q <= w_u_hb_idx_s_Q2_r0c2_k0h1_cs_out[31:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71515_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71515_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71515_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71515_q <= w_u_hb_idx_s_Q2_r0c2_k0h1_cf_out[0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71516_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71516_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71516_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71516_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0];   
    reg [3:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71517_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71517_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71517_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71517_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_vl_q[4:1];   
    reg [31:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71518_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71518_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71518_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71518_q <= 32'b00000000000000000000000000001000;   
    reg [567:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71519_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71519_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71519_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71519_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71558_Q[567:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71520_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71520_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71520_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71520_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_167_55670_Y[0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71521_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71521_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71521_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71521_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71563_Q[7:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71522_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71522_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71522_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71522_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0];   
    reg [3:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71523_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71523_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71523_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71523_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71560_Q[3:0];   
    reg [2175:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71524_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71524_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71524_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71524_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71561_Q[2175:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71525_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71525_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71525_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71525_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55671_Y[7:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71526_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71526_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71526_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71526_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55672_Y[7:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71527_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71527_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71527_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71527_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55673_Y[7:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71528_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71528_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71528_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71528_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55674_Y[7:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71529_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71529_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71529_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71529_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55675_Y[7:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71530_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71530_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71530_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71530_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55676_Y[7:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71531_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71531_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71531_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71531_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55677_Y[7:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71532_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71532_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71532_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71532_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55678_Y[7:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71537_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71537_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71537_q;
    always @(posedge clk or negedge L161m_i_q[0])
        if (!L161m_i_q[0]) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71537_q <= 1'b0; else g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71537_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_reduce_and_ot_hbm_idx_chunk_rt_h_sv_155_55667_Y[0];   
    reg [15:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71542_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71542_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71542_q;
    always @(posedge clk or negedge L161m_i_q[0])
        if (!L161m_i_q[0]) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71542_q <= 16'b0000000000000000; else g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71542_q <= {w_u_hb_idx_s_Q2_r0c2_k3h1_prdy[1:0], w_u_hb_idx_s_Q2_r0c2_k3h0_prdy[1:0], w_u_hb_idx_s_Q2_r0c2_k2h1_prdy[1:0], w_u_hb_idx_s_Q2_r0c2_k2h0_prdy[1:0], w_u_hb_idx_s_Q2_r0c2_k1h1_prdy[1:0], w_u_hb_idx_s_Q2_r0c2_k1h0_prdy[1:0], w_u_hb_idx_s_Q2_r0c2_k0h1_prdy[1:0], w_u_hb_idx_s_Q2_r0c2_k0h0_prdy[1:0]};   
    reg [15:0] g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71547_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71547_Q = g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71547_q;
    always @(posedge clk or negedge L161m_i_q[0])
        if (!L161m_i_q[0]) g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71547_q <= 16'b0000000000000000; else g_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71547_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71542_Q[15:0];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_reduce_and_ot_hbm_idx_chunk_rt_h_sv_155_55667_Y = &w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71547_Q[15:0];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54724_Y = !w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71563_Q[4:3];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54726_Y = 2'b01 == w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71563_Q[4:3];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54728_Y = 2'b10 == w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71563_Q[4:3];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54730_Y = {2{1'b1}} == w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71563_Q[4:3];   
    reg [31:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71548_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71548_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71548_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71548_q <= 32'b00000000000000000000000000000100;   
    reg [551:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71549_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71549_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71549_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71549_q <= w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71550_Q[551:0];   
    reg [551:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71550_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71550_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71550_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71550_q <= {w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__68484ba2[137:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__bafd53de[137:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__3a381be0[137:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__9b5c0437[137:0]};   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71551_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71551_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71551_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71551_q <= w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71557_Q[0];   
    reg [567:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71552_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71552_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71552_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71552_q <= w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71558_Q[567:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71553_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71553_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71553_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71553_q <= w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71559_Q[0];   
    reg [3:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71554_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71554_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71554_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71554_q <= w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71560_Q[3:0];   
    reg [2175:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71555_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71555_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71555_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71555_q <= w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71561_Q[2175:0];   
    reg [29:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71556_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71556_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71556_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71556_q <= w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71562_Q[29:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71557_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71557_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71557_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71557_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71551_Q[0];   
    reg [567:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71558_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71558_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71558_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71558_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71552_Q[567:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71559_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71559_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71559_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71559_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71553_Q[0];   
    reg [3:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71560_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71560_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71560_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71560_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71554_Q[3:0];   
    reg [2175:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71561_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71561_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71561_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71561_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71555_Q[2175:0];   
    reg [29:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71562_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71562_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71562_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71562_q <= w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71556_Q[29:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71563_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71563_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71563_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71563_q <= 8'b00011000;   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__9b5c0437 = w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54724_Y[0] ? {w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71537_Q[0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_u_vl_q[4:1], L186m_i_q[69:38], L186m_i_q[32:1], w_u_hb_idx_s_Q2_r0c3_k1h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c3_k0h1_cs_out[31:0], L186m_i_q[37], L186m_i_q[0], w_u_hb_idx_s_Q2_r0c3_k1h1_cf_out[0], w_u_hb_idx_s_Q2_r0c3_k0h1_cf_out[0]} : w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71549_Q[137:0];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__3a381be0 = w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54726_Y[0] ? {w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71537_Q[0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_u_vl_q[4:1], L186m_i_q[69:38], L186m_i_q[32:1], w_u_hb_idx_s_Q2_r0c3_k1h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c3_k0h1_cs_out[31:0], L186m_i_q[37], L186m_i_q[0], w_u_hb_idx_s_Q2_r0c3_k1h1_cf_out[0], w_u_hb_idx_s_Q2_r0c3_k0h1_cf_out[0]} : w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71549_Q[275:138];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__bafd53de = w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54728_Y[0] ? {w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71537_Q[0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_u_vl_q[4:1], L186m_i_q[69:38], L186m_i_q[32:1], w_u_hb_idx_s_Q2_r0c3_k1h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c3_k0h1_cs_out[31:0], L186m_i_q[37], L186m_i_q[0], w_u_hb_idx_s_Q2_r0c3_k1h1_cf_out[0], w_u_hb_idx_s_Q2_r0c3_k0h1_cf_out[0]} : w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71549_Q[413:276];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__68484ba2 = w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54730_Y[0] ? {w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71537_Q[0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_u_vl_q[4:1], L186m_i_q[69:38], L186m_i_q[32:1], w_u_hb_idx_s_Q2_r0c3_k1h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c3_k0h1_cs_out[31:0], L186m_i_q[37], L186m_i_q[0], w_u_hb_idx_s_Q2_r0c3_k1h1_cf_out[0], w_u_hb_idx_s_Q2_r0c3_k0h1_cf_out[0]} : w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_procdff_71549_Q[551:414];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55671_Y = w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71521_Q[7:0] + {8{1'b0}};   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55672_Y = w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71521_Q[7:0] + 8'b00000001;   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55673_Y = w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71521_Q[7:0] + 8'b00000010;   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55674_Y = w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71521_Q[7:0] + 8'b00000011;   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55675_Y = w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71521_Q[7:0] + 8'b00000100;   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55676_Y = w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71521_Q[7:0] + 8'b00000101;   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55677_Y = w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71521_Q[7:0] + 8'b00000110;   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55678_Y = w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71521_Q[7:0] + 8'b00000111;   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_auto_proc_dff_cc_220_proc_dff_71533_Y = ~L161m_i_q[0];
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_auto_proc_dff_cc_220_proc_dff_71538_Y = ~L161m_i_q[0];
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_auto_proc_dff_cc_220_proc_dff_71543_Y = ~L161m_i_q[0];
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y = w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71557_Q[0] && w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_g_delivered_reset_u_rr_rst_n[4];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_167_55670_Y = w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71559_Q[0] && w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_g_delivered_reset_u_rr_rst_n[4];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y = w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_u_vl_q[0] && w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_g_delivered_reset_u_rr_rst_n[4];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_logic_not_ot_hbm_idx_chunk_rt_h_sv_154_55666_Y = !L161m_i_q[0];   
    reg [31:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71508_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71508_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71508_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71508_q <= L186m_i_q[69:38];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71509_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71509_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71509_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71509_q <= L186m_i_q[37];   
    reg [31:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71510_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71510_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71510_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71510_q <= L186m_i_q[32:1];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71511_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71511_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71511_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71511_q <= L186m_i_q[0];   
    reg [31:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71512_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71512_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71512_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71512_q <= w_u_hb_idx_s_Q2_r0c3_k1h1_cs_out[31:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71513_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71513_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71513_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71513_q <= w_u_hb_idx_s_Q2_r0c3_k1h1_cf_out[0];   
    reg [31:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71514_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71514_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71514_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71514_q <= w_u_hb_idx_s_Q2_r0c3_k0h1_cs_out[31:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71515_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71515_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71515_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71515_q <= w_u_hb_idx_s_Q2_r0c3_k0h1_cf_out[0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71516_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71516_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71516_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71516_q <= w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0];   
    reg [3:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71517_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71517_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71517_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71517_q <= w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_u_vl_q[4:1];   
    reg [31:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71518_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71518_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71518_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71518_q <= 32'b00000000000000000000000000001000;   
    reg [567:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71519_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71519_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71519_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71519_q <= w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71558_Q[567:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71520_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71520_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71520_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71520_q <= w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_167_55670_Y[0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71521_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71521_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71521_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71521_q <= w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71563_Q[7:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71522_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71522_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71522_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71522_q <= w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0];   
    reg [3:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71523_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71523_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71523_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71523_q <= w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71560_Q[3:0];   
    reg [2175:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71524_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71524_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71524_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71524_q <= w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_procdff_71561_Q[2175:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71525_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71525_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71525_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71525_q <= w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55671_Y[7:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71526_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71526_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71526_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71526_q <= w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55672_Y[7:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71527_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71527_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71527_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71527_q <= w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55673_Y[7:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71528_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71528_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71528_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71528_q <= w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55674_Y[7:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71529_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71529_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71529_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71529_q <= w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55675_Y[7:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71530_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71530_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71530_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71530_q <= w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55676_Y[7:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71531_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71531_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71531_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71531_q <= w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55677_Y[7:0];   
    reg [7:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71532_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71532_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71532_q;
    always @(posedge clk) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71532_q <= w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55678_Y[7:0];   
    reg [0:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71537_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71537_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71537_q;
    always @(posedge clk or negedge L161m_i_q[0])
        if (!L161m_i_q[0]) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71537_q <= 1'b0; else g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71537_q <= w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_reduce_and_ot_hbm_idx_chunk_rt_h_sv_155_55667_Y[0];   
    reg [15:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71542_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71542_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71542_q;
    always @(posedge clk or negedge L161m_i_q[0])
        if (!L161m_i_q[0]) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71542_q <= 16'b0000000000000000; else g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71542_q <= {L186m_i_q[71:70], L186m_i_q[36:33], w_u_hb_idx_s_Q2_r0c3_k2h0_prdy[1:0], w_u_hb_idx_s_Q2_r0c3_k1h1_prdy[1:0], w_u_hb_idx_s_Q2_r0c3_k1h0_prdy[1:0], w_u_hb_idx_s_Q2_r0c3_k0h1_prdy[1:0], w_u_hb_idx_s_Q2_r0c3_k0h0_prdy[1:0]};   
    reg [15:0] g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71547_q;
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71547_Q = g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71547_q;
    always @(posedge clk or negedge L161m_i_q[0])
        if (!L161m_i_q[0]) g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71547_q <= 16'b0000000000000000; else g_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71547_q <= w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71542_Q[15:0];   
    assign w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_reduce_and_ot_hbm_idx_chunk_rt_h_sv_155_55667_Y = &w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71547_Q[15:0];   
     
    ot_rst_delivered3 #(.REGIONS(5)) u_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr (
        .clk(clk),
        .rst_n(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n),
        .rst_n_in(L161m_i_q[0])
    );
     
    ot_hdc_delay #(.D(0), .W(569)) u_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_qlate (
        .clk(clk),
        .d({w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71522_Q[0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71519_Q[567:0]}),
        .q(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_qlate_q),
        .rst_n(1'b1)
    );
     
    ot_hdc_delay #(.D(104), .RESET(1), .W(5)) u_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_vl (
        .clk(clk),
        .d({w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71523_Q[3:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71520_Q[0]}),
        .q(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_vl_q),
        .rst_n(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[4])
    );
     
    ot_rst_delivered3 #(.REGIONS(5)) u_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_g_delivered_reset_u_rr (
        .clk(clk),
        .rst_n(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_g_delivered_reset_u_rr_rst_n),
        .rst_n_in(L161m_i_q[0])
    );
     
    ot_hdc_delay #(.D(0), .W(569)) u_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_qlate (
        .clk(clk),
        .d({w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71522_Q[0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71519_Q[567:0]}),
        .q(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_qlate_q),
        .rst_n(1'b1)
    );
     
    ot_hdc_delay #(.D(104), .RESET(1), .W(5)) u_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_vl (
        .clk(clk),
        .d({w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71523_Q[3:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71520_Q[0]}),
        .q(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_vl_q),
        .rst_n(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_g_delivered_reset_u_rr_rst_n[4])
    );
     
    ot_rst_delivered3 #(.REGIONS(5)) u_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_g_delivered_reset_u_rr (
        .clk(clk),
        .rst_n(w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_g_delivered_reset_u_rr_rst_n),
        .rst_n_in(L161m_i_q[0])
    );
     
    ot_hdc_delay #(.D(0), .W(569)) u_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_u_qlate (
        .clk(clk),
        .d({w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71522_Q[0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71519_Q[567:0]}),
        .q(w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_u_qlate_q),
        .rst_n(1'b1)
    );
     
    ot_hdc_delay #(.D(104), .RESET(1), .W(5)) u_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_u_vl (
        .clk(clk),
        .d({w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71523_Q[3:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71520_Q[0]}),
        .q(w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_u_vl_q),
        .rst_n(w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_g_delivered_reset_u_rr_rst_n[4])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c0_k3h1 (
        .cf_in(L161m_i_q[3909]),
        .cf_out(w_u_hb_idx_s_Q2_r0c0_k3h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(L161m_i_q[3941:3910]),
        .cs_out(w_u_hb_idx_s_Q2_r0c0_k3h1_cs_out),
        .hid4(L161m_i_q[3908:3877]),
        .key(L161m_i_q[3876:3333]),
        .prdy(w_u_hb_idx_s_Q2_r0c0_k3h1_prdy),
        .q_b(L161m_i_q[4510:3943]),
        .qv_b(L161m_i_q[4511]),
        .rst_col(L161m_i_q[3942])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c1_k0h0 (
        .cf_out(w_u_hb_idx_s_Q2_r0c1_k0h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q2_r0c1_k0h0_cs_out),
        .hid4({w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71528_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71527_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71526_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71524_Q[543:0]),
        .prdy(w_u_hb_idx_s_Q2_r0c1_k0h0_prdy),
        .q_b(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[0])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c1_k0h1 (
        .cf_in(w_u_hb_idx_s_Q2_r0c1_k0h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q2_r0c1_k0h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q2_r0c1_k0h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q2_r0c1_k0h1_cs_out),
        .hid4({w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71532_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71531_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71530_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71524_Q[543:0]),
        .prdy(w_u_hb_idx_s_Q2_r0c1_k0h1_prdy),
        .q_b(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[0])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c1_k1h0 (
        .cf_out(w_u_hb_idx_s_Q2_r0c1_k1h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q2_r0c1_k1h0_cs_out),
        .hid4({w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71528_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71527_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71526_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71524_Q[1087:544]),
        .prdy(w_u_hb_idx_s_Q2_r0c1_k1h0_prdy),
        .q_b(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[1])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c1_k1h1 (
        .cf_in(w_u_hb_idx_s_Q2_r0c1_k1h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q2_r0c1_k1h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q2_r0c1_k1h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q2_r0c1_k1h1_cs_out),
        .hid4({w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71532_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71531_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71530_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71524_Q[1087:544]),
        .prdy(w_u_hb_idx_s_Q2_r0c1_k1h1_prdy),
        .q_b(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[1])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c1_k2h0 (
        .cf_out(w_u_hb_idx_s_Q2_r0c1_k2h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q2_r0c1_k2h0_cs_out),
        .hid4({w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71528_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71527_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71526_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71524_Q[1631:1088]),
        .prdy(w_u_hb_idx_s_Q2_r0c1_k2h0_prdy),
        .q_b(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[2])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c1_k2h1 (
        .cf_in(w_u_hb_idx_s_Q2_r0c1_k2h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q2_r0c1_k2h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q2_r0c1_k2h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q2_r0c1_k2h1_cs_out),
        .hid4({w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71532_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71531_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71530_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71524_Q[1631:1088]),
        .prdy(w_u_hb_idx_s_Q2_r0c1_k2h1_prdy),
        .q_b(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[2])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c1_k3h0 (
        .cf_out(w_u_hb_idx_s_Q2_r0c1_k3h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q2_r0c1_k3h0_cs_out),
        .hid4({w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71528_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71527_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71526_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71524_Q[2175:1632]),
        .prdy(w_u_hb_idx_s_Q2_r0c1_k3h0_prdy),
        .q_b(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[3])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c1_k3h1 (
        .cf_in(w_u_hb_idx_s_Q2_r0c1_k3h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q2_r0c1_k3h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q2_r0c1_k3h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q2_r0c1_k3h1_cs_out),
        .hid4({w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71532_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71531_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71530_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_procdff_71524_Q[2175:1632]),
        .prdy(w_u_hb_idx_s_Q2_r0c1_k3h1_prdy),
        .q_b(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SE_scorer_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[3])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c2_k0h0 (
        .cf_out(w_u_hb_idx_s_Q2_r0c2_k0h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q2_r0c2_k0h0_cs_out),
        .hid4({w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71528_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71527_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71526_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71524_Q[543:0]),
        .prdy(w_u_hb_idx_s_Q2_r0c2_k0h0_prdy),
        .q_b(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_g_delivered_reset_u_rr_rst_n[0])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c2_k0h1 (
        .cf_in(w_u_hb_idx_s_Q2_r0c2_k0h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q2_r0c2_k0h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q2_r0c2_k0h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q2_r0c2_k0h1_cs_out),
        .hid4({w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71532_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71531_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71530_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71524_Q[543:0]),
        .prdy(w_u_hb_idx_s_Q2_r0c2_k0h1_prdy),
        .q_b(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_g_delivered_reset_u_rr_rst_n[0])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c2_k1h0 (
        .cf_out(w_u_hb_idx_s_Q2_r0c2_k1h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q2_r0c2_k1h0_cs_out),
        .hid4({w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71528_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71527_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71526_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71524_Q[1087:544]),
        .prdy(w_u_hb_idx_s_Q2_r0c2_k1h0_prdy),
        .q_b(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_g_delivered_reset_u_rr_rst_n[1])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c2_k1h1 (
        .cf_in(w_u_hb_idx_s_Q2_r0c2_k1h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q2_r0c2_k1h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q2_r0c2_k1h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q2_r0c2_k1h1_cs_out),
        .hid4({w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71532_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71531_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71530_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71524_Q[1087:544]),
        .prdy(w_u_hb_idx_s_Q2_r0c2_k1h1_prdy),
        .q_b(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_g_delivered_reset_u_rr_rst_n[1])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c2_k2h0 (
        .cf_out(w_u_hb_idx_s_Q2_r0c2_k2h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q2_r0c2_k2h0_cs_out),
        .hid4({w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71528_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71527_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71526_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71524_Q[1631:1088]),
        .prdy(w_u_hb_idx_s_Q2_r0c2_k2h0_prdy),
        .q_b(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_g_delivered_reset_u_rr_rst_n[2])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c2_k2h1 (
        .cf_in(w_u_hb_idx_s_Q2_r0c2_k2h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q2_r0c2_k2h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q2_r0c2_k2h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q2_r0c2_k2h1_cs_out),
        .hid4({w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71532_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71531_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71530_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71524_Q[1631:1088]),
        .prdy(w_u_hb_idx_s_Q2_r0c2_k2h1_prdy),
        .q_b(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_g_delivered_reset_u_rr_rst_n[2])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c2_k3h0 (
        .cf_out(w_u_hb_idx_s_Q2_r0c2_k3h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q2_r0c2_k3h0_cs_out),
        .hid4({w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71528_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71527_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71526_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71524_Q[2175:1632]),
        .prdy(w_u_hb_idx_s_Q2_r0c2_k3h0_prdy),
        .q_b(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_g_delivered_reset_u_rr_rst_n[3])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c2_k3h1 (
        .cf_in(w_u_hb_idx_s_Q2_r0c2_k3h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q2_r0c2_k3h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q2_r0c2_k3h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q2_r0c2_k3h1_cs_out),
        .hid4({w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71532_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71531_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71530_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_procdff_71524_Q[2175:1632]),
        .prdy(w_u_hb_idx_s_Q2_r0c2_k3h1_prdy),
        .q_b(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SE_scorer_ge_0_gc_2_leaf_core_g_delivered_reset_u_rr_rst_n[3])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c3_k0h0 (
        .cf_out(w_u_hb_idx_s_Q2_r0c3_k0h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q2_r0c3_k0h0_cs_out),
        .hid4({w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71528_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71527_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71526_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71524_Q[543:0]),
        .prdy(w_u_hb_idx_s_Q2_r0c3_k0h0_prdy),
        .q_b(w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_g_delivered_reset_u_rr_rst_n[0])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c3_k0h1 (
        .cf_in(w_u_hb_idx_s_Q2_r0c3_k0h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q2_r0c3_k0h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q2_r0c3_k0h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q2_r0c3_k0h1_cs_out),
        .hid4({w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71532_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71531_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71530_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71524_Q[543:0]),
        .prdy(w_u_hb_idx_s_Q2_r0c3_k0h1_prdy),
        .q_b(w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_g_delivered_reset_u_rr_rst_n[0])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c3_k1h0 (
        .cf_out(w_u_hb_idx_s_Q2_r0c3_k1h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q2_r0c3_k1h0_cs_out),
        .hid4({w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71528_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71527_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71526_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71524_Q[1087:544]),
        .prdy(w_u_hb_idx_s_Q2_r0c3_k1h0_prdy),
        .q_b(w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_g_delivered_reset_u_rr_rst_n[1])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c3_k1h1 (
        .cf_in(w_u_hb_idx_s_Q2_r0c3_k1h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q2_r0c3_k1h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q2_r0c3_k1h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q2_r0c3_k1h1_cs_out),
        .hid4({w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71532_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71531_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71530_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71524_Q[1087:544]),
        .prdy(w_u_hb_idx_s_Q2_r0c3_k1h1_prdy),
        .q_b(w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_g_delivered_reset_u_rr_rst_n[1])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c3_k2h0 (
        .cf_out(w_u_hb_idx_s_Q2_r0c3_k2h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q2_r0c3_k2h0_cs_out),
        .hid4({w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71528_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71527_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71526_Q[7:0], w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_procdff_71524_Q[1631:1088]),
        .prdy(w_u_hb_idx_s_Q2_r0c3_k2h0_prdy),
        .q_b(w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SE_scorer_ge_0_gc_3_leaf_core_g_delivered_reset_u_rr_rst_n[2])
    );
     
    ot_hbm_hc_bank128_pair_core u_u_hcb_Q7_ot_hbm_hc_bank128_pair0 (
        .clk(clk),
        .fault(w_u_hcb_Q7_ot_hbm_hc_bank128_pair0_fault),
        .go(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71644_Q[0]),
        .lane_valid(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71645_Q[15:0]),
        .rst_n(w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0]),
        .square(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71646_Q[15:0]),
        .sum_in(w_u_hcb_Q7_u_c_procdff_66854_Q[511:0]),
        .sum_out(w_u_hcb_Q7_ot_hbm_hc_bank128_pair0_sum_out),
        .weight_addr(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71648_Q[9:0]),
        .weight_read(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71669_Q[0]),
        .weight_we0(w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54673_Y[0]),
        .weight_we1(w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54675_Y[0]),
        .write_addr(w_u_hcb_Q7_u_c_u_b_procdff_71774_Q[9:0]),
        .write_data(w_u_hcb_Q7_u_c_u_b_procdff_71775_Q[511:0]),
        .x_addr(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71649_Q[6:0]),
        .x_read(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71674_Q[0]),
        .x_write(w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54705_Y[0])
    );
     
    ot_hbm_hc_bank128_pair_core u_u_hcb_Q7_ot_hbm_hc_bank128_pair1 (
        .clk(clk),
        .fault(w_u_hcb_Q7_ot_hbm_hc_bank128_pair1_fault),
        .go(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71644_Q[0]),
        .lane_valid(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71645_Q[31:16]),
        .rst_n(w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0]),
        .square(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71646_Q[31:16]),
        .sum_in(w_u_hcb_Q7_u_c_procdff_66854_Q[1023:512]),
        .sum_out(w_u_hcb_Q7_ot_hbm_hc_bank128_pair1_sum_out),
        .weight_addr(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71648_Q[9:0]),
        .weight_read(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71669_Q[0]),
        .weight_we0(w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54677_Y[0]),
        .weight_we1(w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54679_Y[0]),
        .write_addr(w_u_hcb_Q7_u_c_u_b_procdff_71774_Q[9:0]),
        .write_data(w_u_hcb_Q7_u_c_u_b_procdff_71775_Q[1023:512]),
        .x_addr(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71649_Q[6:0]),
        .x_read(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71674_Q[0]),
        .x_write(w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54707_Y[0])
    );
     
    ot_hbm_hc_bank128_pair_core u_u_hcb_Q7_ot_hbm_hc_bank128_pair2 (
        .clk(clk),
        .fault(w_u_hcb_Q7_ot_hbm_hc_bank128_pair2_fault),
        .go(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71644_Q[0]),
        .lane_valid(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71645_Q[47:32]),
        .rst_n(w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0]),
        .square(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71646_Q[47:32]),
        .sum_in(w_u_hcb_Q7_u_c_procdff_66854_Q[1535:1024]),
        .sum_out(w_u_hcb_Q7_ot_hbm_hc_bank128_pair2_sum_out),
        .weight_addr(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71648_Q[9:0]),
        .weight_read(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71669_Q[0]),
        .weight_we0(w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54681_Y[0]),
        .weight_we1(w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54683_Y[0]),
        .write_addr(w_u_hcb_Q7_u_c_u_b_procdff_71774_Q[9:0]),
        .write_data(w_u_hcb_Q7_u_c_u_b_procdff_71775_Q[511:0]),
        .x_addr(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71649_Q[6:0]),
        .x_read(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71674_Q[0]),
        .x_write(w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54709_Y[0])
    );
     
    ot_hbm_hc_bank128_pair_core u_u_hcb_Q7_ot_hbm_hc_bank128_pair3 (
        .clk(clk),
        .fault(w_u_hcb_Q7_ot_hbm_hc_bank128_pair3_fault),
        .go(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71644_Q[0]),
        .lane_valid(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71645_Q[63:48]),
        .rst_n(w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0]),
        .square(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71646_Q[63:48]),
        .sum_in(w_u_hcb_Q7_u_c_procdff_66854_Q[2047:1536]),
        .sum_out(w_u_hcb_Q7_ot_hbm_hc_bank128_pair3_sum_out),
        .weight_addr(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71648_Q[9:0]),
        .weight_read(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71669_Q[0]),
        .weight_we0(w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54685_Y[0]),
        .weight_we1(w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54687_Y[0]),
        .write_addr(w_u_hcb_Q7_u_c_u_b_procdff_71774_Q[9:0]),
        .write_data(w_u_hcb_Q7_u_c_u_b_procdff_71775_Q[1023:512]),
        .x_addr(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71649_Q[6:0]),
        .x_read(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71674_Q[0]),
        .x_write(w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54711_Y[0])
    );
     
    ot_hbm_hc_bank128_pair_core u_u_hcb_Q7_ot_hbm_hc_bank128_pair4 (
        .clk(clk),
        .fault(w_u_hcb_Q7_ot_hbm_hc_bank128_pair4_fault),
        .go(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71644_Q[0]),
        .lane_valid(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71645_Q[79:64]),
        .rst_n(w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0]),
        .square(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71646_Q[79:64]),
        .sum_in(w_u_hcb_Q7_u_c_procdff_66854_Q[2559:2048]),
        .sum_out(w_u_hcb_Q7_ot_hbm_hc_bank128_pair4_sum_out),
        .weight_addr(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71648_Q[9:0]),
        .weight_read(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71669_Q[0]),
        .weight_we0(w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54689_Y[0]),
        .weight_we1(w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54691_Y[0]),
        .write_addr(w_u_hcb_Q7_u_c_u_b_procdff_71774_Q[9:0]),
        .write_data(w_u_hcb_Q7_u_c_u_b_procdff_71775_Q[511:0]),
        .x_addr(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71649_Q[6:0]),
        .x_read(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71674_Q[0]),
        .x_write(w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54713_Y[0])
    );
     
    ot_hbm_hc_bank128_pair_core u_u_hcb_Q7_ot_hbm_hc_bank128_pair5 (
        .clk(clk),
        .fault(w_u_hcb_Q7_ot_hbm_hc_bank128_pair5_fault),
        .go(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71644_Q[0]),
        .lane_valid(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71645_Q[95:80]),
        .rst_n(w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0]),
        .square(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71646_Q[95:80]),
        .sum_in(w_u_hcb_Q7_u_c_procdff_66854_Q[3071:2560]),
        .sum_out(w_u_hcb_Q7_ot_hbm_hc_bank128_pair5_sum_out),
        .weight_addr(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71648_Q[9:0]),
        .weight_read(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71669_Q[0]),
        .weight_we0(w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54693_Y[0]),
        .weight_we1(w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54695_Y[0]),
        .write_addr(w_u_hcb_Q7_u_c_u_b_procdff_71774_Q[9:0]),
        .write_data(w_u_hcb_Q7_u_c_u_b_procdff_71775_Q[1023:512]),
        .x_addr(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71649_Q[6:0]),
        .x_read(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71674_Q[0]),
        .x_write(w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54715_Y[0])
    );
     
    ot_hbm_hc_bank128_pair_core u_u_hcb_Q7_ot_hbm_hc_bank128_pair6 (
        .clk(clk),
        .fault(w_u_hcb_Q7_ot_hbm_hc_bank128_pair6_fault),
        .go(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71644_Q[0]),
        .lane_valid(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71645_Q[111:96]),
        .rst_n(w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0]),
        .square(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71646_Q[111:96]),
        .sum_in(w_u_hcb_Q7_u_c_procdff_66854_Q[3583:3072]),
        .sum_out(w_u_hcb_Q7_ot_hbm_hc_bank128_pair6_sum_out),
        .weight_addr(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71648_Q[9:0]),
        .weight_read(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71669_Q[0]),
        .weight_we0(w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54697_Y[0]),
        .weight_we1(w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54699_Y[0]),
        .write_addr(w_u_hcb_Q7_u_c_u_b_procdff_71774_Q[9:0]),
        .write_data(w_u_hcb_Q7_u_c_u_b_procdff_71775_Q[511:0]),
        .x_addr(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71649_Q[6:0]),
        .x_read(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71674_Q[0]),
        .x_write(w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54717_Y[0])
    );
     
    ot_hbm_hc_bank128_pair_core u_u_hcb_Q7_ot_hbm_hc_bank128_pair7 (
        .clk(clk),
        .fault(w_u_hcb_Q7_ot_hbm_hc_bank128_pair7_fault),
        .go(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71644_Q[0]),
        .lane_valid(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71645_Q[127:112]),
        .rst_n(w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0]),
        .square(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71646_Q[127:112]),
        .sum_in(w_u_hcb_Q7_u_c_procdff_66854_Q[4095:3584]),
        .sum_out(w_u_hcb_Q7_ot_hbm_hc_bank128_pair7_sum_out),
        .weight_addr(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71648_Q[9:0]),
        .weight_read(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71669_Q[0]),
        .weight_we0(w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54701_Y[0]),
        .weight_we1(w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54703_Y[0]),
        .write_addr(w_u_hcb_Q7_u_c_u_b_procdff_71774_Q[9:0]),
        .write_data(w_u_hcb_Q7_u_c_u_b_procdff_71775_Q[1023:512]),
        .x_addr(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71649_Q[6:0]),
        .x_read(w_u_hcb_Q7_u_c_u_b_u_st_procdff_71674_Q[0]),
        .x_write(w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54719_Y[0])
    );
    assign w_u_hcb_Q7_u_c_auto_proc_dff_cc_220_proc_dff_66845_Y = ~w_u_hcb_Q7_u_c_u_rst_rst_n[0];
    assign w_u_hcb_Q7_u_c_auto_proc_dff_cc_220_proc_dff_66855_Y = ~w_u_hcb_Q7_u_c_u_rst_rst_n[0];
    assign w_u_hcb_Q7_u_c_auto_proc_dff_cc_220_proc_dff_66860_Y = ~w_u_hcb_Q7_u_c_u_rst_rst_n[0];
    assign w_u_hcb_Q7_u_c_auto_proc_dff_cc_220_proc_dff_66865_Y = ~w_u_hcb_Q7_u_c_u_rst_rst_n[0];
    assign w_u_hcb_Q7_u_c_auto_proc_dff_cc_220_proc_dff_66870_Y = ~w_u_hcb_Q7_u_c_u_rst_rst_n[0];
    assign w_u_hcb_Q7_u_c_auto_proc_dff_cc_220_proc_dff_66882_Y = ~w_u_hcb_Q7_u_c_u_rst_rst_n[0];
    assign w_u_hcb_Q7_u_c_eq_ot_hbm_hc_bankq_static_sv_50_54279_Y = !w_u_hcb_Q7_u_c_procdff_66877_Q[1:0];   
    assign w_u_hcb_Q7_u_c_eq_ot_hbm_hc_bankq_static_sv_50_54281_Y = w_u_hcb_Q7_u_c_procdff_66877_Q[1:0] == 2'b01;   
    assign w_u_hcb_Q7_u_c_eq_ot_hbm_hc_bankq_static_sv_50_54283_Y = w_u_hcb_Q7_u_c_procdff_66877_Q[1:0] == 2'b10;   
    assign w_u_hcb_Q7_u_c_logic_and_ot_hbm_hc_bankq_static_sv_50_54280_Y = w_u_hcb_Q7_u_c_procdff_66886_Q[0] && w_u_hcb_Q7_u_c_eq_ot_hbm_hc_bankq_static_sv_50_54279_Y[0];   
    assign w_u_hcb_Q7_u_c_logic_and_ot_hbm_hc_bankq_static_sv_50_54282_Y = w_u_hcb_Q7_u_c_procdff_66886_Q[0] && w_u_hcb_Q7_u_c_eq_ot_hbm_hc_bankq_static_sv_50_54281_Y[0];   
    assign w_u_hcb_Q7_u_c_logic_and_ot_hbm_hc_bankq_static_sv_50_54284_Y = w_u_hcb_Q7_u_c_procdff_66886_Q[0] && w_u_hcb_Q7_u_c_eq_ot_hbm_hc_bankq_static_sv_50_54283_Y[0];   
    assign w_u_hcb_Q7_u_c_logic_and_ot_hbm_hc_bankq_static_sv_61_54321_Y = w_u_hcb_Q7_u_c_procdff_66874_Q[0] && w_u_hcb_Q7_u_c_procdff_66875_Q[0];   
    assign w_u_hcb_Q7_u_c_logic_not_ot_hbm_hc_bankq_static_sv_47_54276_Y = !w_u_hcb_Q7_u_c_u_rst_rst_n[0];   
    assign w_u_hcb_Q7_u_c_logic_not_ot_hbm_hc_bankq_static_sv_60_54320_Y = !w_u_hcb_Q7_u_c_u_rst_rst_n[0];   
    assign w_u_hcb_Q7_u_c_logic_not_ot_hbm_hc_bankq_static_sv_67_54323_Y = !w_u_hcb_Q7_u_c_u_rst_rst_n[0];   
    assign w_u_hcb_Q7_u_c_logic_not_ot_hbm_hc_bankq_static_sv_76_54326_Y = !w_u_hcb_Q7_u_c_u_rst_rst_n[0];   
    reg [4095:0] g_u_hcb_Q7_u_c_procdff_66844_q;
    assign w_u_hcb_Q7_u_c_procdff_66844_Q = g_u_hcb_Q7_u_c_procdff_66844_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_procdff_66844_q <= {w_u_hcb_Q7_ot_hbm_hc_bank128_pair7_sum_out[511:0], w_u_hcb_Q7_ot_hbm_hc_bank128_pair6_sum_out[511:0], w_u_hcb_Q7_ot_hbm_hc_bank128_pair5_sum_out[511:0], w_u_hcb_Q7_ot_hbm_hc_bank128_pair4_sum_out[511:0], w_u_hcb_Q7_ot_hbm_hc_bank128_pair3_sum_out[511:0], w_u_hcb_Q7_ot_hbm_hc_bank128_pair2_sum_out[511:0], w_u_hcb_Q7_ot_hbm_hc_bank128_pair1_sum_out[511:0], w_u_hcb_Q7_ot_hbm_hc_bank128_pair0_sum_out[511:0]};   
    reg [0:0] g_u_hcb_Q7_u_c_procdff_66849_q;
    assign w_u_hcb_Q7_u_c_procdff_66849_Q = g_u_hcb_Q7_u_c_procdff_66849_q;
    always @(posedge clk or negedge w_u_hcb_Q7_u_c_u_rst_rst_n[0])
        if (!w_u_hcb_Q7_u_c_u_rst_rst_n[0]) g_u_hcb_Q7_u_c_procdff_66849_q <= 1'b0; else g_u_hcb_Q7_u_c_procdff_66849_q <= w_u_hcb_Q7_u_c_u_b_u_st_procdff_71664_Q[0];   
    reg [0:0] g_u_hcb_Q7_u_c_procdff_66850_q;
    assign w_u_hcb_Q7_u_c_procdff_66850_Q = g_u_hcb_Q7_u_c_procdff_66850_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_procdff_66850_q <= L11_i_q[4397];   
    reg [7:0] g_u_hcb_Q7_u_c_procdff_66851_q;
    assign w_u_hcb_Q7_u_c_procdff_66851_Q = g_u_hcb_Q7_u_c_procdff_66851_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_procdff_66851_q <= L11_i_q[4396:4389];   
    reg [9:0] g_u_hcb_Q7_u_c_procdff_66852_q;
    assign w_u_hcb_Q7_u_c_procdff_66852_Q = g_u_hcb_Q7_u_c_procdff_66852_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_procdff_66852_q <= L11_i_q[4388:4379];   
    reg [9:0] g_u_hcb_Q7_u_c_procdff_66853_q;
    assign w_u_hcb_Q7_u_c_procdff_66853_Q = g_u_hcb_Q7_u_c_procdff_66853_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_procdff_66853_q <= L11_i_q[4378:4369];   
    reg [4095:0] g_u_hcb_Q7_u_c_procdff_66854_q;
    assign w_u_hcb_Q7_u_c_procdff_66854_Q = g_u_hcb_Q7_u_c_procdff_66854_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_procdff_66854_q <= L11_i_q[4368:273];   
    reg [0:0] g_u_hcb_Q7_u_c_procdff_66859_q;
    assign w_u_hcb_Q7_u_c_procdff_66859_Q = g_u_hcb_Q7_u_c_procdff_66859_q;
    always @(posedge clk or negedge w_u_hcb_Q7_u_c_u_rst_rst_n[0])
        if (!w_u_hcb_Q7_u_c_u_rst_rst_n[0]) g_u_hcb_Q7_u_c_procdff_66859_q <= 1'b0; else g_u_hcb_Q7_u_c_procdff_66859_q <= L11_i_q[4399];   
    reg [0:0] g_u_hcb_Q7_u_c_procdff_66864_q;
    assign w_u_hcb_Q7_u_c_procdff_66864_Q = g_u_hcb_Q7_u_c_procdff_66864_q;
    always @(posedge clk or negedge w_u_hcb_Q7_u_c_u_rst_rst_n[0])
        if (!w_u_hcb_Q7_u_c_u_rst_rst_n[0]) g_u_hcb_Q7_u_c_procdff_66864_q <= 1'b0; else g_u_hcb_Q7_u_c_procdff_66864_q <= L11_i_q[4398];   
    reg [0:0] g_u_hcb_Q7_u_c_procdff_66869_q;
    assign w_u_hcb_Q7_u_c_procdff_66869_Q = g_u_hcb_Q7_u_c_procdff_66869_q;
    always @(posedge clk or negedge w_u_hcb_Q7_u_c_u_rst_rst_n[0])
        if (!w_u_hcb_Q7_u_c_u_rst_rst_n[0]) g_u_hcb_Q7_u_c_procdff_66869_q <= 1'b0; else g_u_hcb_Q7_u_c_procdff_66869_q <= w_u_hcb_Q7_u_c_procmux_55781_Y[0];   
    reg [0:0] g_u_hcb_Q7_u_c_procdff_66874_q;
    assign w_u_hcb_Q7_u_c_procdff_66874_Q = g_u_hcb_Q7_u_c_procdff_66874_q;
    always @(posedge clk or negedge w_u_hcb_Q7_u_c_u_rst_rst_n[0])
        if (!w_u_hcb_Q7_u_c_u_rst_rst_n[0]) g_u_hcb_Q7_u_c_procdff_66874_q <= 1'b0; else g_u_hcb_Q7_u_c_procdff_66874_q <= L11_i_q[272];   
    reg [0:0] g_u_hcb_Q7_u_c_procdff_66875_q;
    assign w_u_hcb_Q7_u_c_procdff_66875_Q = g_u_hcb_Q7_u_c_procdff_66875_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_procdff_66875_q <= w_u_hcb_Q7_u_c_procmux_55845_Y[0];   
    reg [31:0] g_u_hcb_Q7_u_c_procdff_66876_q;
    assign w_u_hcb_Q7_u_c_procdff_66876_Q = g_u_hcb_Q7_u_c_procdff_66876_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_procdff_66876_q <= 32'b00000000000000000000000000100000;   
    reg [1:0] g_u_hcb_Q7_u_c_procdff_66877_q;
    assign w_u_hcb_Q7_u_c_procdff_66877_Q = g_u_hcb_Q7_u_c_procdff_66877_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_procdff_66877_q <= L11_i_q[1:0];   
    reg [255:0] g_u_hcb_Q7_u_c_procdff_66878_q;
    assign w_u_hcb_Q7_u_c_procdff_66878_Q = g_u_hcb_Q7_u_c_procdff_66878_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_procdff_66878_q <= L11_i_q[257:2];   
    reg [767:0] g_u_hcb_Q7_u_c_procdff_66879_q;
    assign w_u_hcb_Q7_u_c_procdff_66879_Q = g_u_hcb_Q7_u_c_procdff_66879_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_procdff_66879_q <= {w_u_hcb_Q7_u_c_procmux_55847_Y[255:0], w_u_hcb_Q7_u_c_procmux_55849_Y[255:0], w_u_hcb_Q7_u_c_procmux_55851_Y[255:0]};   
    reg [1023:0] g_u_hcb_Q7_u_c_procdff_66880_q;
    assign w_u_hcb_Q7_u_c_procdff_66880_Q = g_u_hcb_Q7_u_c_procdff_66880_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_procdff_66880_q <= {w_u_hcb_Q7_u_c_procdff_66878_Q[255:0], w_u_hcb_Q7_u_c_procdff_66879_Q[767:0]};   
    reg [31:0] g_u_hcb_Q7_u_c_procdff_66881_q;
    assign w_u_hcb_Q7_u_c_procdff_66881_Q = g_u_hcb_Q7_u_c_procdff_66881_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_procdff_66881_q <= 32'b00000000000000000000000000000011;   
    reg [0:0] g_u_hcb_Q7_u_c_procdff_66886_q;
    assign w_u_hcb_Q7_u_c_procdff_66886_Q = g_u_hcb_Q7_u_c_procdff_66886_q;
    always @(posedge clk or negedge w_u_hcb_Q7_u_c_u_rst_rst_n[0])
        if (!w_u_hcb_Q7_u_c_u_rst_rst_n[0]) g_u_hcb_Q7_u_c_procdff_66886_q <= 1'b0; else g_u_hcb_Q7_u_c_procdff_66886_q <= L11_i_q[270];   
    assign w_u_hcb_Q7_u_c_procmux_55781_Y = w_u_hcb_Q7_u_c_logic_and_ot_hbm_hc_bankq_static_sv_61_54321_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procdff_66869_Q[0];   
    assign w_u_hcb_Q7_u_c_procmux_55783_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54287_Y[0] ? 1'b1 : 1'b0;   
    assign w_u_hcb_Q7_u_c_procmux_55785_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54288_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55783_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55787_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54289_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55785_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55789_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54290_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55787_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55791_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54291_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55789_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55793_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54292_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55791_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55795_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54293_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55793_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55797_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54294_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55795_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55799_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54295_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55797_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55801_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54296_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55799_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55803_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54297_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55801_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55805_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54298_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55803_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55807_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54299_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55805_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55809_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54300_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55807_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55811_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54301_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55809_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55813_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54302_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55811_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55815_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54303_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55813_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55817_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54304_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55815_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55819_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54305_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55817_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55821_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54306_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55819_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55823_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54307_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55821_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55825_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54308_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55823_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55827_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54309_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55825_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55829_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54310_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55827_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55831_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54311_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55829_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55833_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54312_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55831_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55835_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54313_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55833_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55837_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54314_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55835_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55839_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54315_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55837_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55841_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54316_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55839_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55843_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54317_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55841_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55845_Y = w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54318_Y[0] ? 1'b1 : w_u_hcb_Q7_u_c_procmux_55843_Y[0];   
    assign w_u_hcb_Q7_u_c_procmux_55847_Y = w_u_hcb_Q7_u_c_logic_and_ot_hbm_hc_bankq_static_sv_50_54284_Y[0] ? w_u_hcb_Q7_u_c_procdff_66878_Q[255:0] : w_u_hcb_Q7_u_c_procdff_66879_Q[767:512];   
    assign w_u_hcb_Q7_u_c_procmux_55849_Y = w_u_hcb_Q7_u_c_logic_and_ot_hbm_hc_bankq_static_sv_50_54282_Y[0] ? w_u_hcb_Q7_u_c_procdff_66878_Q[255:0] : w_u_hcb_Q7_u_c_procdff_66879_Q[511:256];   
    assign w_u_hcb_Q7_u_c_procmux_55851_Y = w_u_hcb_Q7_u_c_logic_and_ot_hbm_hc_bankq_static_sv_50_54280_Y[0] ? w_u_hcb_Q7_u_c_procdff_66878_Q[255:0] : w_u_hcb_Q7_u_c_procdff_66879_Q[255:0];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54287_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[15:0];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54288_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[47:32];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54289_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[79:64];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54290_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[111:96];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54291_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[143:128];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54292_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[175:160];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54293_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[207:192];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54294_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[239:224];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54295_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[271:256];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54296_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[303:288];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54297_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[335:320];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54298_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[367:352];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54299_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[399:384];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54300_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[431:416];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54301_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[463:448];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54302_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[495:480];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54303_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[527:512];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54304_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[559:544];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54305_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[591:576];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54306_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[623:608];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54307_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[655:640];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54308_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[687:672];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54309_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[719:704];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54310_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[751:736];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54311_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[783:768];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54312_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[815:800];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54313_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[847:832];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54314_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[879:864];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54315_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[911:896];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54316_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[943:928];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54317_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[975:960];   
    assign w_u_hcb_Q7_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54318_Y = |w_u_hcb_Q7_u_c_procdff_66880_Q[1007:992];   
    assign w_u_hcb_Q7_u_c_u_b_auto_proc_dff_cc_220_proc_dff_71776_Y = ~w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[1];
    assign w_u_hcb_Q7_u_c_u_b_auto_proc_dff_cc_220_proc_dff_71781_Y = ~w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[1];
    assign w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54672_Y = !w_u_hcb_Q7_u_c_u_b_procdff_71773_Q[1:0];   
    assign w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54674_Y = !w_u_hcb_Q7_u_c_u_b_procdff_71773_Q[1:0];   
    assign w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54676_Y = !w_u_hcb_Q7_u_c_u_b_procdff_71773_Q[1:0];   
    assign w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54678_Y = !w_u_hcb_Q7_u_c_u_b_procdff_71773_Q[1:0];   
    assign w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54680_Y = w_u_hcb_Q7_u_c_u_b_procdff_71773_Q[1:0] == 2'b01;   
    assign w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54682_Y = w_u_hcb_Q7_u_c_u_b_procdff_71773_Q[1:0] == 2'b01;   
    assign w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54684_Y = w_u_hcb_Q7_u_c_u_b_procdff_71773_Q[1:0] == 2'b01;   
    assign w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54686_Y = w_u_hcb_Q7_u_c_u_b_procdff_71773_Q[1:0] == 2'b01;   
    assign w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54688_Y = w_u_hcb_Q7_u_c_u_b_procdff_71773_Q[1:0] == 2'b10;   
    assign w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54690_Y = w_u_hcb_Q7_u_c_u_b_procdff_71773_Q[1:0] == 2'b10;   
    assign w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54692_Y = w_u_hcb_Q7_u_c_u_b_procdff_71773_Q[1:0] == 2'b10;   
    assign w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54694_Y = w_u_hcb_Q7_u_c_u_b_procdff_71773_Q[1:0] == 2'b10;   
    assign w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54696_Y = w_u_hcb_Q7_u_c_u_b_procdff_71773_Q[1:0] == {2{1'b1}};   
    assign w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54698_Y = w_u_hcb_Q7_u_c_u_b_procdff_71773_Q[1:0] == {2{1'b1}};   
    assign w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54700_Y = w_u_hcb_Q7_u_c_u_b_procdff_71773_Q[1:0] == {2{1'b1}};   
    assign w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54702_Y = w_u_hcb_Q7_u_c_u_b_procdff_71773_Q[1:0] == {2{1'b1}};   
    assign w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54704_Y = !w_u_hcb_Q7_u_c_u_b_procdff_71773_Q[1:0];   
    assign w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54706_Y = !w_u_hcb_Q7_u_c_u_b_procdff_71773_Q[1:0];   
    assign w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54708_Y = w_u_hcb_Q7_u_c_u_b_procdff_71773_Q[1:0] == 2'b01;   
    assign w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54710_Y = w_u_hcb_Q7_u_c_u_b_procdff_71773_Q[1:0] == 2'b01;   
    assign w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54712_Y = w_u_hcb_Q7_u_c_u_b_procdff_71773_Q[1:0] == 2'b10;   
    assign w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54714_Y = w_u_hcb_Q7_u_c_u_b_procdff_71773_Q[1:0] == 2'b10;   
    assign w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54716_Y = w_u_hcb_Q7_u_c_u_b_procdff_71773_Q[1:0] == {2{1'b1}};   
    assign w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54718_Y = w_u_hcb_Q7_u_c_u_b_procdff_71773_Q[1:0] == {2{1'b1}};   
    assign w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54673_Y = w_u_hcb_Q7_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54672_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54675_Y = w_u_hcb_Q7_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54674_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54677_Y = w_u_hcb_Q7_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54676_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54679_Y = w_u_hcb_Q7_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54678_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54681_Y = w_u_hcb_Q7_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54680_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54683_Y = w_u_hcb_Q7_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54682_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54685_Y = w_u_hcb_Q7_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54684_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54687_Y = w_u_hcb_Q7_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54686_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54689_Y = w_u_hcb_Q7_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54688_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54691_Y = w_u_hcb_Q7_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54690_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54693_Y = w_u_hcb_Q7_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54692_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54695_Y = w_u_hcb_Q7_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54694_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54697_Y = w_u_hcb_Q7_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54696_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54699_Y = w_u_hcb_Q7_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54698_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54701_Y = w_u_hcb_Q7_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54700_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54703_Y = w_u_hcb_Q7_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54702_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54705_Y = w_u_hcb_Q7_u_c_u_b_procdff_71785_Q[0] && w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54704_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54707_Y = w_u_hcb_Q7_u_c_u_b_procdff_71785_Q[0] && w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54706_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54709_Y = w_u_hcb_Q7_u_c_u_b_procdff_71785_Q[0] && w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54708_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54711_Y = w_u_hcb_Q7_u_c_u_b_procdff_71785_Q[0] && w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54710_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54713_Y = w_u_hcb_Q7_u_c_u_b_procdff_71785_Q[0] && w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54712_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54715_Y = w_u_hcb_Q7_u_c_u_b_procdff_71785_Q[0] && w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54714_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54717_Y = w_u_hcb_Q7_u_c_u_b_procdff_71785_Q[0] && w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54716_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54719_Y = w_u_hcb_Q7_u_c_u_b_procdff_71785_Q[0] && w_u_hcb_Q7_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54718_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_logic_not_ot_hbm_hc_bank_static_sv_59_54669_Y = !w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[1];   
    reg [1:0] g_u_hcb_Q7_u_c_u_b_procdff_71773_q;
    assign w_u_hcb_Q7_u_c_u_b_procdff_71773_Q = g_u_hcb_Q7_u_c_u_b_procdff_71773_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_u_b_procdff_71773_q <= L11_i_q[259:258];   
    reg [9:0] g_u_hcb_Q7_u_c_u_b_procdff_71774_q;
    assign w_u_hcb_Q7_u_c_u_b_procdff_71774_Q = g_u_hcb_Q7_u_c_u_b_procdff_71774_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_u_b_procdff_71774_q <= L11_i_q[269:260];   
    reg [1023:0] g_u_hcb_Q7_u_c_u_b_procdff_71775_q;
    assign w_u_hcb_Q7_u_c_u_b_procdff_71775_Q = g_u_hcb_Q7_u_c_u_b_procdff_71775_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_u_b_procdff_71775_q <= w_u_hcb_Q7_u_c_procdff_66880_Q[1023:0];   
    reg [0:0] g_u_hcb_Q7_u_c_u_b_procdff_71780_q;
    assign w_u_hcb_Q7_u_c_u_b_procdff_71780_Q = g_u_hcb_Q7_u_c_u_b_procdff_71780_q;
    always @(posedge clk or negedge w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[1])
        if (!w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[1]) g_u_hcb_Q7_u_c_u_b_procdff_71780_q <= 1'b0; else g_u_hcb_Q7_u_c_u_b_procdff_71780_q <= L11_i_q[271];   
    reg [0:0] g_u_hcb_Q7_u_c_u_b_procdff_71785_q;
    assign w_u_hcb_Q7_u_c_u_b_procdff_71785_Q = g_u_hcb_Q7_u_c_u_b_procdff_71785_q;
    always @(posedge clk or negedge w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[1])
        if (!w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[1]) g_u_hcb_Q7_u_c_u_b_procdff_71785_q <= 1'b0; else g_u_hcb_Q7_u_c_u_b_procdff_71785_q <= L11_i_q[272];   
     
    ot_rst_relay #(.REGIONS(2)) u_u_hcb_Q7_u_c_u_b_g_rr_u_rst (
        .clk(clk),
        .rst_n(w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n),
        .rst_n_in(L11_i_q[4400])
    );
    assign w_u_hcb_Q7_u_c_u_b_u_st_auto_proc_dff_cc_220_proc_dff_71640_Y = ~w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0];
    assign w_u_hcb_Q7_u_c_u_b_u_st_auto_proc_dff_cc_220_proc_dff_71660_Y = ~w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0];
    assign w_u_hcb_Q7_u_c_u_b_u_st_auto_proc_dff_cc_220_proc_dff_71665_Y = ~w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0];
    assign w_u_hcb_Q7_u_c_u_b_u_st_auto_proc_dff_cc_220_proc_dff_71670_Y = ~w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0];
    assign w_u_hcb_Q7_u_c_u_b_u_st_auto_proc_dff_cc_220_proc_dff_71675_Y = ~w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0];
    assign w_u_hcb_Q7_u_c_u_b_u_st_auto_proc_dff_cc_220_proc_dff_71680_Y = ~w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0];
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_669_55081_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[0] && w_u_hcb_Q7_u_c_u_b_u_st_logic_not_ot_hdc_v41x_hcp_sv_669_55080_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55088_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55087_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55090_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55089_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55092_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55091_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55094_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55093_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55096_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55095_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55098_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55097_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55100_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55099_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55102_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55101_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55104_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55103_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55106_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55105_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55108_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55107_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55110_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55109_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55112_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55111_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55114_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55113_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55116_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55115_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55118_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55117_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55120_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55119_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55122_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55121_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55124_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55123_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55126_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55125_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55128_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55127_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55130_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55129_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55132_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55131_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55134_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55133_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55136_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55135_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55138_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55137_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55140_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55139_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55142_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55141_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55144_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55143_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55146_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55145_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55148_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55147_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55150_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55149_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55152_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55151_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55154_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55153_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55156_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55155_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55158_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55157_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55160_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55159_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55162_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55161_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55164_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55163_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55166_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55165_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55168_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55167_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55170_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55169_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55172_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55171_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55174_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55173_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55176_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55175_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55178_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55177_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55180_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55179_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55182_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55181_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55184_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55183_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55186_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55185_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55188_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55187_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55190_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55189_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55192_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55191_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55194_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55193_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55196_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55195_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55198_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55197_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55200_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55199_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55202_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55201_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55204_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55203_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55206_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55205_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55208_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55207_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55210_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55209_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55212_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55211_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55214_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55213_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55216_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55215_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55218_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55217_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55220_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55219_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55222_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55221_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55224_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55223_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55226_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55225_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55228_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55227_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55230_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55229_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55232_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55231_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55234_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55233_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55236_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55235_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55238_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55237_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55240_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55239_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55242_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55241_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55244_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55243_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55246_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55245_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55248_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55247_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55250_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55249_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55252_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55251_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55254_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55253_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55256_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55255_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55258_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55257_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55260_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55259_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55262_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55261_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55264_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55263_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55266_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55265_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55268_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55267_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55270_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55269_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55272_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55271_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55274_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55273_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55276_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55275_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55278_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55277_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55280_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55279_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55282_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55281_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55284_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55283_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55286_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55285_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55288_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55287_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55290_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55289_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55292_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55291_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55294_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55293_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55296_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55295_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55298_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55297_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55300_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55299_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55302_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55301_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55304_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55303_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55306_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55305_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55308_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55307_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55310_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55309_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55312_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55311_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55314_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55313_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55316_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55315_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55318_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55317_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55320_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55319_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55322_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55321_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55324_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55323_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55326_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55325_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55328_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55327_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55330_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55329_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55332_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55331_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55334_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55333_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55336_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55335_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55338_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55337_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55340_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55339_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55342_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55341_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_not_ot_hdc_v41x_hcp_sv_666_55079_Y = !w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_not_ot_hdc_v41x_hcp_sv_669_55080_Y = !w_u_hcb_Q7_u_c_u_b_u_st_procdff_71651_Q[28];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_not_ot_hdc_v41x_hcp_sv_741_55344_Y = !w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_logic_or_ot_hdc_v41x_hcp_sv_672_55082_Y = w_u_hcb_Q7_u_c_u_b_u_st_procdff_71684_Q[0] || w_u_hcb_Q7_u_c_u_b_u_st_reduce_or_ot_hdc_v41x_hcp_sv_750_55345_Y[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55087_Y = {32{1'b0}} < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55089_Y = 32'b00000000000000000000000000000001 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55091_Y = 32'b00000000000000000000000000000010 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55093_Y = 32'b00000000000000000000000000000011 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55095_Y = 32'b00000000000000000000000000000100 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55097_Y = 32'b00000000000000000000000000000101 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55099_Y = 32'b00000000000000000000000000000110 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55101_Y = 32'b00000000000000000000000000000111 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55103_Y = 32'b00000000000000000000000000001000 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55105_Y = 32'b00000000000000000000000000001001 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55107_Y = 32'b00000000000000000000000000001010 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55109_Y = 32'b00000000000000000000000000001011 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55111_Y = 32'b00000000000000000000000000001100 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55113_Y = 32'b00000000000000000000000000001101 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55115_Y = 32'b00000000000000000000000000001110 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55117_Y = 32'b00000000000000000000000000001111 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55119_Y = 32'b00000000000000000000000000010000 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55121_Y = 32'b00000000000000000000000000010001 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55123_Y = 32'b00000000000000000000000000010010 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55125_Y = 32'b00000000000000000000000000010011 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55127_Y = 32'b00000000000000000000000000010100 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55129_Y = 32'b00000000000000000000000000010101 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55131_Y = 32'b00000000000000000000000000010110 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55133_Y = 32'b00000000000000000000000000010111 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55135_Y = 32'b00000000000000000000000000011000 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55137_Y = 32'b00000000000000000000000000011001 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55139_Y = 32'b00000000000000000000000000011010 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55141_Y = 32'b00000000000000000000000000011011 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55143_Y = 32'b00000000000000000000000000011100 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55145_Y = 32'b00000000000000000000000000011101 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55147_Y = 32'b00000000000000000000000000011110 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55149_Y = 32'b00000000000000000000000000011111 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55151_Y = 32'b00000000000000000000000000100000 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55153_Y = 32'b00000000000000000000000000100001 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55155_Y = 32'b00000000000000000000000000100010 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55157_Y = 32'b00000000000000000000000000100011 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55159_Y = 32'b00000000000000000000000000100100 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55161_Y = 32'b00000000000000000000000000100101 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55163_Y = 32'b00000000000000000000000000100110 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55165_Y = 32'b00000000000000000000000000100111 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55167_Y = 32'b00000000000000000000000000101000 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55169_Y = 32'b00000000000000000000000000101001 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55171_Y = 32'b00000000000000000000000000101010 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55173_Y = 32'b00000000000000000000000000101011 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55175_Y = 32'b00000000000000000000000000101100 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55177_Y = 32'b00000000000000000000000000101101 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55179_Y = 32'b00000000000000000000000000101110 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55181_Y = 32'b00000000000000000000000000101111 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55183_Y = 32'b00000000000000000000000000110000 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55185_Y = 32'b00000000000000000000000000110001 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55187_Y = 32'b00000000000000000000000000110010 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55189_Y = 32'b00000000000000000000000000110011 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55191_Y = 32'b00000000000000000000000000110100 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55193_Y = 32'b00000000000000000000000000110101 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55195_Y = 32'b00000000000000000000000000110110 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55197_Y = 32'b00000000000000000000000000110111 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55199_Y = 32'b00000000000000000000000000111000 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55201_Y = 32'b00000000000000000000000000111001 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55203_Y = 32'b00000000000000000000000000111010 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55205_Y = 32'b00000000000000000000000000111011 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55207_Y = 32'b00000000000000000000000000111100 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55209_Y = 32'b00000000000000000000000000111101 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55211_Y = 32'b00000000000000000000000000111110 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55213_Y = 32'b00000000000000000000000000111111 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55215_Y = 32'b00000000000000000000000001000000 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55217_Y = 32'b00000000000000000000000001000001 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55219_Y = 32'b00000000000000000000000001000010 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55221_Y = 32'b00000000000000000000000001000011 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55223_Y = 32'b00000000000000000000000001000100 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55225_Y = 32'b00000000000000000000000001000101 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55227_Y = 32'b00000000000000000000000001000110 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55229_Y = 32'b00000000000000000000000001000111 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55231_Y = 32'b00000000000000000000000001001000 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55233_Y = 32'b00000000000000000000000001001001 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55235_Y = 32'b00000000000000000000000001001010 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55237_Y = 32'b00000000000000000000000001001011 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55239_Y = 32'b00000000000000000000000001001100 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55241_Y = 32'b00000000000000000000000001001101 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55243_Y = 32'b00000000000000000000000001001110 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55245_Y = 32'b00000000000000000000000001001111 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55247_Y = 32'b00000000000000000000000001010000 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55249_Y = 32'b00000000000000000000000001010001 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55251_Y = 32'b00000000000000000000000001010010 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55253_Y = 32'b00000000000000000000000001010011 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55255_Y = 32'b00000000000000000000000001010100 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55257_Y = 32'b00000000000000000000000001010101 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55259_Y = 32'b00000000000000000000000001010110 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55261_Y = 32'b00000000000000000000000001010111 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55263_Y = 32'b00000000000000000000000001011000 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55265_Y = 32'b00000000000000000000000001011001 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55267_Y = 32'b00000000000000000000000001011010 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55269_Y = 32'b00000000000000000000000001011011 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55271_Y = 32'b00000000000000000000000001011100 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55273_Y = 32'b00000000000000000000000001011101 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55275_Y = 32'b00000000000000000000000001011110 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55277_Y = 32'b00000000000000000000000001011111 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55279_Y = 32'b00000000000000000000000001100000 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55281_Y = 32'b00000000000000000000000001100001 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55283_Y = 32'b00000000000000000000000001100010 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55285_Y = 32'b00000000000000000000000001100011 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55287_Y = 32'b00000000000000000000000001100100 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55289_Y = 32'b00000000000000000000000001100101 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55291_Y = 32'b00000000000000000000000001100110 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55293_Y = 32'b00000000000000000000000001100111 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55295_Y = 32'b00000000000000000000000001101000 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55297_Y = 32'b00000000000000000000000001101001 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55299_Y = 32'b00000000000000000000000001101010 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55301_Y = 32'b00000000000000000000000001101011 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55303_Y = 32'b00000000000000000000000001101100 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55305_Y = 32'b00000000000000000000000001101101 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55307_Y = 32'b00000000000000000000000001101110 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55309_Y = 32'b00000000000000000000000001101111 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55311_Y = 32'b00000000000000000000000001110000 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55313_Y = 32'b00000000000000000000000001110001 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55315_Y = 32'b00000000000000000000000001110010 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55317_Y = 32'b00000000000000000000000001110011 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55319_Y = 32'b00000000000000000000000001110100 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55321_Y = 32'b00000000000000000000000001110101 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55323_Y = 32'b00000000000000000000000001110110 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55325_Y = 32'b00000000000000000000000001110111 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55327_Y = 32'b00000000000000000000000001111000 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55329_Y = 32'b00000000000000000000000001111001 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55331_Y = 32'b00000000000000000000000001111010 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55333_Y = 32'b00000000000000000000000001111011 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55335_Y = 32'b00000000000000000000000001111100 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55337_Y = 32'b00000000000000000000000001111101 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55339_Y = 32'b00000000000000000000000001111110 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55341_Y = 32'b00000000000000000000000001111111 < w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    reg [0:0] g_u_hcb_Q7_u_c_u_b_u_st_procdff_71644_q;
    assign w_u_hcb_Q7_u_c_u_b_u_st_procdff_71644_Q = g_u_hcb_Q7_u_c_u_b_u_st_procdff_71644_q;
    always @(posedge clk or negedge w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0])
        if (!w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0]) g_u_hcb_Q7_u_c_u_b_u_st_procdff_71644_q <= 1'b0; else g_u_hcb_Q7_u_c_u_b_u_st_procdff_71644_q <= w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[3];   
    reg [127:0] g_u_hcb_Q7_u_c_u_b_u_st_procdff_71645_q;
    assign w_u_hcb_Q7_u_c_u_b_u_st_procdff_71645_Q = g_u_hcb_Q7_u_c_u_b_u_st_procdff_71645_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_u_b_u_st_procdff_71645_q <= {w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55342_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55340_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55338_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55336_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55334_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55332_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55330_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55328_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55326_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55324_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55322_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55320_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55318_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55316_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55314_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55312_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55310_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55308_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55306_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55304_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55302_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55300_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55298_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55296_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55294_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55292_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55290_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55288_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55286_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55284_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55282_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55280_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55278_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55276_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55274_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55272_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55270_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55268_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55266_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55264_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55262_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55260_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55258_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55256_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55254_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55252_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55250_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55248_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55246_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55244_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55242_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55240_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55238_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55236_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55234_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55232_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55230_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55228_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55226_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55224_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55222_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55220_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55218_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55216_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55214_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55212_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55210_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55208_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55206_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55204_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55202_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55200_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55198_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55196_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55194_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55192_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55190_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55188_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55186_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55184_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55182_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55180_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55178_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55176_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55174_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55172_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55170_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55168_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55166_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55164_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55162_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55160_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55158_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55156_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55154_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55152_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55150_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55148_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55146_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55144_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55142_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55140_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55138_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55136_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55134_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55132_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55130_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55128_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55126_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55124_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55122_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55120_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55118_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55116_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55114_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55112_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55110_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55108_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55106_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55104_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55102_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55100_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55098_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55096_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55094_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55092_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55090_Y[0], w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55088_Y[0]};   
    reg [127:0] g_u_hcb_Q7_u_c_u_b_u_st_procdff_71646_q;
    assign w_u_hcb_Q7_u_c_u_b_u_st_procdff_71646_Q = g_u_hcb_Q7_u_c_u_b_u_st_procdff_71646_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_u_b_u_st_procdff_71646_q <= {w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28]};   
    reg [31:0] g_u_hcb_Q7_u_c_u_b_u_st_procdff_71647_q;
    assign w_u_hcb_Q7_u_c_u_b_u_st_procdff_71647_Q = g_u_hcb_Q7_u_c_u_b_u_st_procdff_71647_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_u_b_u_st_procdff_71647_q <= 32'b00000000000000000000000010000000;   
    reg [9:0] g_u_hcb_Q7_u_c_u_b_u_st_procdff_71648_q;
    assign w_u_hcb_Q7_u_c_u_b_u_st_procdff_71648_Q = g_u_hcb_Q7_u_c_u_b_u_st_procdff_71648_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_u_b_u_st_procdff_71648_q <= w_u_hcb_Q7_u_c_u_b_u_st_procdff_71651_Q[19:10];   
    reg [9:0] g_u_hcb_Q7_u_c_u_b_u_st_procdff_71649_q;
    assign w_u_hcb_Q7_u_c_u_b_u_st_procdff_71649_Q = g_u_hcb_Q7_u_c_u_b_u_st_procdff_71649_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_u_b_u_st_procdff_71649_q <= w_u_hcb_Q7_u_c_u_b_u_st_procdff_71651_Q[9:0];   
    reg [31:0] g_u_hcb_Q7_u_c_u_b_u_st_procdff_71650_q;
    assign w_u_hcb_Q7_u_c_u_b_u_st_procdff_71650_Q = g_u_hcb_Q7_u_c_u_b_u_st_procdff_71650_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_u_b_u_st_procdff_71650_q <= 32'b00000000000000000000000000001001;   
    reg [28:0] g_u_hcb_Q7_u_c_u_b_u_st_procdff_71651_q;
    assign w_u_hcb_Q7_u_c_u_b_u_st_procdff_71651_Q = g_u_hcb_Q7_u_c_u_b_u_st_procdff_71651_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_u_b_u_st_procdff_71651_q <= {w_u_hcb_Q7_u_c_procdff_66850_Q[0], w_u_hcb_Q7_u_c_procdff_66851_Q[7:0], w_u_hcb_Q7_u_c_procdff_66852_Q[9:0], w_u_hcb_Q7_u_c_procdff_66853_Q[9:0]};   
    reg [28:0] g_u_hcb_Q7_u_c_u_b_u_st_procdff_71652_q;
    assign w_u_hcb_Q7_u_c_u_b_u_st_procdff_71652_Q = g_u_hcb_Q7_u_c_u_b_u_st_procdff_71652_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_u_b_u_st_procdff_71652_q <= w_u_hcb_Q7_u_c_u_b_u_st_procdff_71651_Q[28:0];   
    reg [28:0] g_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_q;
    assign w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q = g_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_q <= w_u_hcb_Q7_u_c_u_b_u_st_procdff_71652_Q[28:0];   
    reg [28:0] g_u_hcb_Q7_u_c_u_b_u_st_procdff_71654_q;
    assign w_u_hcb_Q7_u_c_u_b_u_st_procdff_71654_Q = g_u_hcb_Q7_u_c_u_b_u_st_procdff_71654_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_u_b_u_st_procdff_71654_q <= w_u_hcb_Q7_u_c_u_b_u_st_procdff_71653_Q[28:0];   
    reg [28:0] g_u_hcb_Q7_u_c_u_b_u_st_procdff_71655_q;
    assign w_u_hcb_Q7_u_c_u_b_u_st_procdff_71655_Q = g_u_hcb_Q7_u_c_u_b_u_st_procdff_71655_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_u_b_u_st_procdff_71655_q <= w_u_hcb_Q7_u_c_u_b_u_st_procdff_71654_Q[28:0];   
    reg [28:0] g_u_hcb_Q7_u_c_u_b_u_st_procdff_71656_q;
    assign w_u_hcb_Q7_u_c_u_b_u_st_procdff_71656_Q = g_u_hcb_Q7_u_c_u_b_u_st_procdff_71656_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_u_b_u_st_procdff_71656_q <= w_u_hcb_Q7_u_c_u_b_u_st_procdff_71655_Q[28:0];   
    reg [28:0] g_u_hcb_Q7_u_c_u_b_u_st_procdff_71657_q;
    assign w_u_hcb_Q7_u_c_u_b_u_st_procdff_71657_Q = g_u_hcb_Q7_u_c_u_b_u_st_procdff_71657_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_u_b_u_st_procdff_71657_q <= w_u_hcb_Q7_u_c_u_b_u_st_procdff_71656_Q[28:0];   
    reg [28:0] g_u_hcb_Q7_u_c_u_b_u_st_procdff_71658_q;
    assign w_u_hcb_Q7_u_c_u_b_u_st_procdff_71658_Q = g_u_hcb_Q7_u_c_u_b_u_st_procdff_71658_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_u_b_u_st_procdff_71658_q <= w_u_hcb_Q7_u_c_u_b_u_st_procdff_71657_Q[28:0];   
    reg [28:0] g_u_hcb_Q7_u_c_u_b_u_st_procdff_71659_q;
    assign w_u_hcb_Q7_u_c_u_b_u_st_procdff_71659_Q = g_u_hcb_Q7_u_c_u_b_u_st_procdff_71659_q;
    always @(posedge clk) g_u_hcb_Q7_u_c_u_b_u_st_procdff_71659_q <= w_u_hcb_Q7_u_c_u_b_u_st_procdff_71658_Q[28:0];   
    reg [0:0] g_u_hcb_Q7_u_c_u_b_u_st_procdff_71664_q;
    assign w_u_hcb_Q7_u_c_u_b_u_st_procdff_71664_Q = g_u_hcb_Q7_u_c_u_b_u_st_procdff_71664_q;
    always @(posedge clk or negedge w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0])
        if (!w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0]) g_u_hcb_Q7_u_c_u_b_u_st_procdff_71664_q <= 1'b0; else g_u_hcb_Q7_u_c_u_b_u_st_procdff_71664_q <= w_u_hcb_Q7_u_c_u_b_u_st_logic_or_ot_hdc_v41x_hcp_sv_672_55082_Y[0];   
    reg [0:0] g_u_hcb_Q7_u_c_u_b_u_st_procdff_71669_q;
    assign w_u_hcb_Q7_u_c_u_b_u_st_procdff_71669_Q = g_u_hcb_Q7_u_c_u_b_u_st_procdff_71669_q;
    always @(posedge clk or negedge w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0])
        if (!w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0]) g_u_hcb_Q7_u_c_u_b_u_st_procdff_71669_q <= 1'b0; else g_u_hcb_Q7_u_c_u_b_u_st_procdff_71669_q <= w_u_hcb_Q7_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_669_55081_Y[0];   
    reg [0:0] g_u_hcb_Q7_u_c_u_b_u_st_procdff_71674_q;
    assign w_u_hcb_Q7_u_c_u_b_u_st_procdff_71674_Q = g_u_hcb_Q7_u_c_u_b_u_st_procdff_71674_q;
    always @(posedge clk or negedge w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0])
        if (!w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0]) g_u_hcb_Q7_u_c_u_b_u_st_procdff_71674_q <= 1'b0; else g_u_hcb_Q7_u_c_u_b_u_st_procdff_71674_q <= w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[0];   
    reg [8:0] g_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_q;
    assign w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q = g_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_q;
    always @(posedge clk or negedge w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0])
        if (!w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0]) g_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_q <= 9'b000000000; else g_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_q <= {w_u_hcb_Q7_u_c_u_b_u_st_procdff_71679_Q[7:0], w_u_hcb_Q7_u_c_procdff_66859_Q[0]};   
    reg [0:0] g_u_hcb_Q7_u_c_u_b_u_st_procdff_71684_q;
    assign w_u_hcb_Q7_u_c_u_b_u_st_procdff_71684_Q = g_u_hcb_Q7_u_c_u_b_u_st_procdff_71684_q;
    always @(posedge clk or negedge w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0])
        if (!w_u_hcb_Q7_u_c_u_b_g_rr_u_rst_rst_n[0]) g_u_hcb_Q7_u_c_u_b_u_st_procdff_71684_q <= 1'b0; else g_u_hcb_Q7_u_c_u_b_u_st_procdff_71684_q <= w_u_hcb_Q7_u_c_procdff_66864_Q[0];   
    assign w_u_hcb_Q7_u_c_u_b_u_st_reduce_or_ot_hdc_v41x_hcp_sv_750_55345_Y = |{w_u_hcb_Q7_ot_hbm_hc_bank128_pair7_fault[1:0], w_u_hcb_Q7_ot_hbm_hc_bank128_pair6_fault[1:0], w_u_hcb_Q7_ot_hbm_hc_bank128_pair5_fault[1:0], w_u_hcb_Q7_ot_hbm_hc_bank128_pair4_fault[1:0], w_u_hcb_Q7_ot_hbm_hc_bank128_pair3_fault[1:0], w_u_hcb_Q7_ot_hbm_hc_bank128_pair2_fault[1:0], w_u_hcb_Q7_ot_hbm_hc_bank128_pair1_fault[1:0], w_u_hcb_Q7_ot_hbm_hc_bank128_pair0_fault[1:0]};   
     
    ot_rst_relay #(.REGIONS(1)) u_u_hcb_Q7_u_c_u_rst (
        .clk(clk),
        .rst_n(w_u_hcb_Q7_u_c_u_rst_rst_n),
        .rst_n_in(L11_i_q[4400])
    );
endmodule
