module hbm_arch_q_b102 (
    input  wire clk,
    input  wire arst_n,
    input  wire [1:0] xi_gc_0_leaf_procdff_71557_D,    
    input  wire [5:0] xi_gc_0_leaf_procdff_71558_D__0,    
    input  wire [512:0] xi_gc_0_leaf_procdff_71558_D__1,    
    input  wire [32:0] xi_gc_0_leaf_procdff_71558_D__2,    
    input  wire [16:0] xi_gc_0_leaf_procdff_71558_D__3,    
    input  wire [1:0] xi_gc_0_leaf_procdff_71559_D,    
    input  wire [1:0] xi_gc_0_leaf_procdff_71560_D__0,    
    input  wire [1:0] xi_gc_0_leaf_procdff_71560_D__1,    
    input  wire [1:0] xi_gc_0_leaf_procdff_71560_D__2,    
    input  wire [1:0] xi_gc_0_leaf_procdff_71560_D__3,    
    input  wire [2176:0] xi_gc_0_leaf_procdff_71561_D,    
    input  wire [20:0] xi_gc_0_leaf_procdff_71562_D__0,    
    input  wire [1:0] xi_gc_0_leaf_procdff_71562_D__1,    
    input  wire [1:0] xi_gc_0_leaf_procdff_71562_D__2,    
    input  wire [1:0] xi_gc_0_leaf_procdff_71562_D__3,    
    input  wire [1:0] xi_gc_0_leaf_procdff_71562_D__4,    
    input  wire [1:0] xi_gc_0_leaf_procdff_71562_D__5,    
    input  wire [1:0] xi_gc_0_leaf_procdff_71562_D__6,    
    output wire [3332:0] L164_o,    
    input  wire [634:0] L48x1_i,    
    output wire [634:0] L48x1_o,    
    input  wire [612:0] L53x11_i,    
    output wire [612:0] L53x11_o    
);
    wire [0:0] xi_gc_0_leaf_procdff_71557_D_q;
    wire xi_gc_0_leaf_procdff_71557_D_eq;
    wire [4:0] xi_gc_0_leaf_procdff_71558_D__0_q;
    wire xi_gc_0_leaf_procdff_71558_D__0_eq;
    wire [511:0] xi_gc_0_leaf_procdff_71558_D__1_q;
    wire xi_gc_0_leaf_procdff_71558_D__1_eq;
    wire [31:0] xi_gc_0_leaf_procdff_71558_D__2_q;
    wire xi_gc_0_leaf_procdff_71558_D__2_eq;
    wire [15:0] xi_gc_0_leaf_procdff_71558_D__3_q;
    wire xi_gc_0_leaf_procdff_71558_D__3_eq;
    wire [0:0] xi_gc_0_leaf_procdff_71559_D_q;
    wire xi_gc_0_leaf_procdff_71559_D_eq;
    wire [0:0] xi_gc_0_leaf_procdff_71560_D__0_q;
    wire xi_gc_0_leaf_procdff_71560_D__0_eq;
    wire [0:0] xi_gc_0_leaf_procdff_71560_D__1_q;
    wire xi_gc_0_leaf_procdff_71560_D__1_eq;
    wire [0:0] xi_gc_0_leaf_procdff_71560_D__2_q;
    wire xi_gc_0_leaf_procdff_71560_D__2_eq;
    wire [0:0] xi_gc_0_leaf_procdff_71560_D__3_q;
    wire xi_gc_0_leaf_procdff_71560_D__3_eq;
    wire [2175:0] xi_gc_0_leaf_procdff_71561_D_q;
    wire xi_gc_0_leaf_procdff_71561_D_eq;
    wire [19:0] xi_gc_0_leaf_procdff_71562_D__0_q;
    wire xi_gc_0_leaf_procdff_71562_D__0_eq;
    wire [0:0] xi_gc_0_leaf_procdff_71562_D__1_q;
    wire xi_gc_0_leaf_procdff_71562_D__1_eq;
    wire [0:0] xi_gc_0_leaf_procdff_71562_D__2_q;
    wire xi_gc_0_leaf_procdff_71562_D__2_eq;
    wire [0:0] xi_gc_0_leaf_procdff_71562_D__3_q;
    wire xi_gc_0_leaf_procdff_71562_D__3_eq;
    wire [0:0] xi_gc_0_leaf_procdff_71562_D__4_q;
    wire xi_gc_0_leaf_procdff_71562_D__4_eq;
    wire [0:0] xi_gc_0_leaf_procdff_71562_D__5_q;
    wire xi_gc_0_leaf_procdff_71562_D__5_eq;
    wire [0:0] xi_gc_0_leaf_procdff_71562_D__6_q;
    wire xi_gc_0_leaf_procdff_71562_D__6_eq;
    wire [0:0] w_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54724_Y;
    wire [0:0] w_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54726_Y;
    wire [0:0] w_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54728_Y;
    wire [0:0] w_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54730_Y;
    wire [31:0] w_gc_0_leaf_procdff_71548_Q;
    wire [551:0] w_gc_0_leaf_procdff_71549_Q;
    wire [551:0] w_gc_0_leaf_procdff_71550_Q;
    wire [0:0] w_gc_0_leaf_procdff_71551_Q;
    wire [567:0] w_gc_0_leaf_procdff_71552_Q;
    wire [0:0] w_gc_0_leaf_procdff_71553_Q;
    wire [3:0] w_gc_0_leaf_procdff_71554_Q;
    wire [2175:0] w_gc_0_leaf_procdff_71555_Q;
    wire [29:0] w_gc_0_leaf_procdff_71556_Q;
    wire [0:0] w_gc_0_leaf_procdff_71557_Q;
    wire [567:0] w_gc_0_leaf_procdff_71558_Q;
    wire [0:0] w_gc_0_leaf_procdff_71559_Q;
    wire [3:0] w_gc_0_leaf_procdff_71560_Q;
    wire [2175:0] w_gc_0_leaf_procdff_71561_Q;
    wire [29:0] w_gc_0_leaf_procdff_71562_Q;
    wire [7:0] w_gc_0_leaf_procdff_71563_Q;
    wire [137:0] w_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54725_Y;
    wire [137:0] w_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54727_Y;
    wire [137:0] w_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54729_Y;
    wire [137:0] w_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54731_Y;
    wire [7:0] w_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55671_Y;
    wire [7:0] w_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55672_Y;
    wire [7:0] w_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55673_Y;
    wire [7:0] w_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55674_Y;
    wire [7:0] w_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55675_Y;
    wire [7:0] w_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55676_Y;
    wire [7:0] w_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55677_Y;
    wire [7:0] w_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55678_Y;
    wire [0:0] w_gc_0_leaf_core_auto_proc_dff_cc_220_proc_dff_71533_Y;
    wire [0:0] w_gc_0_leaf_core_auto_proc_dff_cc_220_proc_dff_71538_Y;
    wire [0:0] w_gc_0_leaf_core_auto_proc_dff_cc_220_proc_dff_71543_Y;
    wire [0:0] w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y;
    wire [0:0] w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_167_55670_Y;
    wire [0:0] w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y;
    wire [0:0] w_gc_0_leaf_core_logic_not_ot_hbm_idx_chunk_rt_h_sv_154_55666_Y;
    wire [31:0] w_gc_0_leaf_core_procdff_71508_Q;
    wire [0:0] w_gc_0_leaf_core_procdff_71509_Q;
    wire [31:0] w_gc_0_leaf_core_procdff_71510_Q;
    wire [0:0] w_gc_0_leaf_core_procdff_71511_Q;
    wire [31:0] w_gc_0_leaf_core_procdff_71512_Q;
    wire [0:0] w_gc_0_leaf_core_procdff_71513_Q;
    wire [31:0] w_gc_0_leaf_core_procdff_71514_Q;
    wire [0:0] w_gc_0_leaf_core_procdff_71515_Q;
    wire [0:0] w_gc_0_leaf_core_procdff_71516_Q;
    wire [3:0] w_gc_0_leaf_core_procdff_71517_Q;
    wire [31:0] w_gc_0_leaf_core_procdff_71518_Q;
    wire [567:0] w_gc_0_leaf_core_procdff_71519_Q;
    wire [0:0] w_gc_0_leaf_core_procdff_71520_Q;
    wire [7:0] w_gc_0_leaf_core_procdff_71521_Q;
    wire [0:0] w_gc_0_leaf_core_procdff_71522_Q;
    wire [3:0] w_gc_0_leaf_core_procdff_71523_Q;
    wire [2175:0] w_gc_0_leaf_core_procdff_71524_Q;
    wire [7:0] w_gc_0_leaf_core_procdff_71525_Q;
    wire [7:0] w_gc_0_leaf_core_procdff_71526_Q;
    wire [7:0] w_gc_0_leaf_core_procdff_71527_Q;
    wire [7:0] w_gc_0_leaf_core_procdff_71528_Q;
    wire [7:0] w_gc_0_leaf_core_procdff_71529_Q;
    wire [7:0] w_gc_0_leaf_core_procdff_71530_Q;
    wire [7:0] w_gc_0_leaf_core_procdff_71531_Q;
    wire [7:0] w_gc_0_leaf_core_procdff_71532_Q;
    wire [0:0] w_gc_0_leaf_core_procdff_71537_Q;
    wire [15:0] w_gc_0_leaf_core_procdff_71542_Q;
    wire [15:0] w_gc_0_leaf_core_procdff_71547_Q;
    wire [0:0] w_gc_0_leaf_core_reduce_and_ot_hbm_idx_chunk_rt_h_sv_155_55667_Y;
    wire [0:0] w_u_hb_idx_s_Q_r1c0_k0h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r1c0_k0h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r1c0_k0h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r1c0_k0h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r1c0_k0h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r1c0_k0h1_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r1c0_k1h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r1c0_k1h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r1c0_k1h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r1c0_k1h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r1c0_k1h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r1c0_k1h1_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r1c0_k2h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r1c0_k2h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r1c0_k2h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r1c0_k2h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r1c0_k2h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r1c0_k2h1_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r1c0_k3h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r1c0_k3h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r1c0_k3h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r1c0_k3h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r1c0_k3h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r1c0_k3h1_prdy;
    wire [4:0] w_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n;
    wire [568:0] w_gc_0_leaf_core_u_qlate_q;
    wire [4:0] w_gc_0_leaf_core_u_vl_q;
    wire [0:0] w_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54724_Y;
    wire [0:0] w_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54726_Y;
    wire [0:0] w_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54728_Y;
    wire [0:0] w_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54730_Y;
    wire [31:0] w_gc_1_leaf_procdff_71548_Q;
    wire [551:0] w_gc_1_leaf_procdff_71549_Q;
    wire [551:0] w_gc_1_leaf_procdff_71550_Q;
    wire [0:0] w_gc_1_leaf_procdff_71551_Q;
    wire [567:0] w_gc_1_leaf_procdff_71552_Q;
    wire [0:0] w_gc_1_leaf_procdff_71553_Q;
    wire [3:0] w_gc_1_leaf_procdff_71554_Q;
    wire [2175:0] w_gc_1_leaf_procdff_71555_Q;
    wire [29:0] w_gc_1_leaf_procdff_71556_Q;
    wire [0:0] w_gc_1_leaf_procdff_71557_Q;
    wire [567:0] w_gc_1_leaf_procdff_71558_Q;
    wire [0:0] w_gc_1_leaf_procdff_71559_Q;
    wire [3:0] w_gc_1_leaf_procdff_71560_Q;
    wire [2175:0] w_gc_1_leaf_procdff_71561_Q;
    wire [29:0] w_gc_1_leaf_procdff_71562_Q;
    wire [7:0] w_gc_1_leaf_procdff_71563_Q;
    wire [137:0] w_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54725_Y;
    wire [137:0] w_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54727_Y;
    wire [137:0] w_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54729_Y;
    wire [137:0] w_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54731_Y;
    wire [7:0] w_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55671_Y;
    wire [7:0] w_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55672_Y;
    wire [7:0] w_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55673_Y;
    wire [7:0] w_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55674_Y;
    wire [7:0] w_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55675_Y;
    wire [7:0] w_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55676_Y;
    wire [7:0] w_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55677_Y;
    wire [7:0] w_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55678_Y;
    wire [0:0] w_gc_1_leaf_core_auto_proc_dff_cc_220_proc_dff_71533_Y;
    wire [0:0] w_gc_1_leaf_core_auto_proc_dff_cc_220_proc_dff_71538_Y;
    wire [0:0] w_gc_1_leaf_core_auto_proc_dff_cc_220_proc_dff_71543_Y;
    wire [0:0] w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y;
    wire [0:0] w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_167_55670_Y;
    wire [0:0] w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y;
    wire [0:0] w_gc_1_leaf_core_logic_not_ot_hbm_idx_chunk_rt_h_sv_154_55666_Y;
    wire [31:0] w_gc_1_leaf_core_procdff_71508_Q;
    wire [0:0] w_gc_1_leaf_core_procdff_71509_Q;
    wire [31:0] w_gc_1_leaf_core_procdff_71510_Q;
    wire [0:0] w_gc_1_leaf_core_procdff_71511_Q;
    wire [31:0] w_gc_1_leaf_core_procdff_71512_Q;
    wire [0:0] w_gc_1_leaf_core_procdff_71513_Q;
    wire [31:0] w_gc_1_leaf_core_procdff_71514_Q;
    wire [0:0] w_gc_1_leaf_core_procdff_71515_Q;
    wire [0:0] w_gc_1_leaf_core_procdff_71516_Q;
    wire [3:0] w_gc_1_leaf_core_procdff_71517_Q;
    wire [31:0] w_gc_1_leaf_core_procdff_71518_Q;
    wire [567:0] w_gc_1_leaf_core_procdff_71519_Q;
    wire [0:0] w_gc_1_leaf_core_procdff_71520_Q;
    wire [7:0] w_gc_1_leaf_core_procdff_71521_Q;
    wire [0:0] w_gc_1_leaf_core_procdff_71522_Q;
    wire [3:0] w_gc_1_leaf_core_procdff_71523_Q;
    wire [2175:0] w_gc_1_leaf_core_procdff_71524_Q;
    wire [7:0] w_gc_1_leaf_core_procdff_71525_Q;
    wire [7:0] w_gc_1_leaf_core_procdff_71526_Q;
    wire [7:0] w_gc_1_leaf_core_procdff_71527_Q;
    wire [7:0] w_gc_1_leaf_core_procdff_71528_Q;
    wire [7:0] w_gc_1_leaf_core_procdff_71529_Q;
    wire [7:0] w_gc_1_leaf_core_procdff_71530_Q;
    wire [7:0] w_gc_1_leaf_core_procdff_71531_Q;
    wire [7:0] w_gc_1_leaf_core_procdff_71532_Q;
    wire [0:0] w_gc_1_leaf_core_procdff_71537_Q;
    wire [15:0] w_gc_1_leaf_core_procdff_71542_Q;
    wire [15:0] w_gc_1_leaf_core_procdff_71547_Q;
    wire [0:0] w_gc_1_leaf_core_reduce_and_ot_hbm_idx_chunk_rt_h_sv_155_55667_Y;
    wire [0:0] w_u_hb_idx_s_Q_r1c1_k0h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r1c1_k0h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r1c1_k0h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r1c1_k0h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r1c1_k0h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r1c1_k0h1_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r1c1_k1h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r1c1_k1h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r1c1_k1h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r1c1_k1h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r1c1_k1h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r1c1_k1h1_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r1c1_k2h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r1c1_k2h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r1c1_k2h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r1c1_k2h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r1c1_k2h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r1c1_k2h1_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r1c1_k3h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r1c1_k3h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r1c1_k3h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r1c1_k3h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r1c1_k3h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r1c1_k3h1_prdy;
    wire [4:0] w_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n;
    wire [568:0] w_gc_1_leaf_core_u_qlate_q;
    wire [4:0] w_gc_1_leaf_core_u_vl_q;
    wire [634:0] L48x1_o_s0;
    wire [612:0] L53x11_o_s0;
     
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
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_4), .q(rst_n_t7));   
    wire rst_rl_6;
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_root_n), .q(rst_rl_6));   
    wire rst_rl_7;
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_rl_6), .q(rst_rl_7));   
    wire rst_rl_8;
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_rl_7), .q(rst_rl_8));   
    wire rst_rl_9;
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_rl_8), .q(rst_rl_9));   
    wire rst_rl_10;
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_9), .q(rst_rl_10));   
    ot_dp_rrelay u_rrl_11 (.clk(clk), .d(rst_rl_10), .q(rst_n_t1));   
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_10), .q(rst_n_t0));   
    wire rst_rl_13;
    ot_dp_rrelay u_rrl_13 (.clk(clk), .d(rst_rl_6), .q(rst_rl_13));   
    wire rst_rl_14;
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_13), .q(rst_rl_14));   
    wire rst_rl_15;
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_14), .q(rst_rl_15));   
    wire rst_rl_16;
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_15), .q(rst_rl_16));   
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_16), .q(rst_n_t3));   
    wire rst_rl_18;
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_root_n), .q(rst_rl_18));   
    wire rst_rl_19;
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_18), .q(rst_rl_19));   
    wire rst_rl_20;
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_19), .q(rst_rl_20));   
    wire rst_rl_21;
    ot_dp_rrelay u_rrl_21 (.clk(clk), .d(rst_rl_20), .q(rst_rl_21));   
    wire rst_rl_22;
    ot_dp_rrelay u_rrl_22 (.clk(clk), .d(rst_rl_21), .q(rst_rl_22));   
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_22), .q(rst_n_t2));   
    wire rst_rl_24;
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_root_n), .q(rst_rl_24));   
    wire rst_rl_25;
    ot_dp_rrelay u_rrl_25 (.clk(clk), .d(rst_rl_24), .q(rst_rl_25));   
    wire rst_rl_26;
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_rl_25), .q(rst_rl_26));   
    wire rst_rl_27;
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_26), .q(rst_rl_27));   
    wire rst_rl_28;
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_27), .q(rst_rl_28));   
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_rl_28), .q(rst_n_t5));   
    wire rst_rl_30;
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_rl_27), .q(rst_rl_30));   
    ot_dp_rrelay u_rrl_31 (.clk(clk), .d(rst_rl_30), .q(rst_n_t6));   
    wire rst_rl_32;
    ot_dp_rrelay u_rrl_32 (.clk(clk), .d(rst_rl_27), .q(rst_rl_32));   
    ot_dp_rrelay u_rrl_33 (.clk(clk), .d(rst_rl_32), .q(rst_n_t4));   
    wire rst_n = rst_n_t4;
    ot_dp_st #(.W(1)) u_bin_xi_gc_0_leaf_procdff_71557_D (.clk(clk), .rst_n(rst_n), .d(xi_gc_0_leaf_procdff_71557_D[0:0]), .ea(xi_gc_0_leaf_procdff_71557_D[1]), .q(xi_gc_0_leaf_procdff_71557_D_q), .eq(xi_gc_0_leaf_procdff_71557_D_eq));
    ot_dp_st #(.W(5)) u_bin_xi_gc_0_leaf_procdff_71558_D__0 (.clk(clk), .rst_n(rst_n), .d(xi_gc_0_leaf_procdff_71558_D__0[4:0]), .ea(xi_gc_0_leaf_procdff_71558_D__0[5]), .q(xi_gc_0_leaf_procdff_71558_D__0_q), .eq(xi_gc_0_leaf_procdff_71558_D__0_eq));
    ot_dp_st #(.W(512)) u_bin_xi_gc_0_leaf_procdff_71558_D__1 (.clk(clk), .rst_n(rst_n), .d(xi_gc_0_leaf_procdff_71558_D__1[511:0]), .ea(xi_gc_0_leaf_procdff_71558_D__1[512]), .q(xi_gc_0_leaf_procdff_71558_D__1_q), .eq(xi_gc_0_leaf_procdff_71558_D__1_eq));
    ot_dp_st #(.W(32)) u_bin_xi_gc_0_leaf_procdff_71558_D__2 (.clk(clk), .rst_n(rst_n), .d(xi_gc_0_leaf_procdff_71558_D__2[31:0]), .ea(xi_gc_0_leaf_procdff_71558_D__2[32]), .q(xi_gc_0_leaf_procdff_71558_D__2_q), .eq(xi_gc_0_leaf_procdff_71558_D__2_eq));
    ot_dp_st #(.W(16)) u_bin_xi_gc_0_leaf_procdff_71558_D__3 (.clk(clk), .rst_n(rst_n), .d(xi_gc_0_leaf_procdff_71558_D__3[15:0]), .ea(xi_gc_0_leaf_procdff_71558_D__3[16]), .q(xi_gc_0_leaf_procdff_71558_D__3_q), .eq(xi_gc_0_leaf_procdff_71558_D__3_eq));
    ot_dp_st #(.W(1)) u_bin_xi_gc_0_leaf_procdff_71559_D (.clk(clk), .rst_n(rst_n), .d(xi_gc_0_leaf_procdff_71559_D[0:0]), .ea(xi_gc_0_leaf_procdff_71559_D[1]), .q(xi_gc_0_leaf_procdff_71559_D_q), .eq(xi_gc_0_leaf_procdff_71559_D_eq));
    ot_dp_st #(.W(1)) u_bin_xi_gc_0_leaf_procdff_71560_D__0 (.clk(clk), .rst_n(rst_n), .d(xi_gc_0_leaf_procdff_71560_D__0[0:0]), .ea(xi_gc_0_leaf_procdff_71560_D__0[1]), .q(xi_gc_0_leaf_procdff_71560_D__0_q), .eq(xi_gc_0_leaf_procdff_71560_D__0_eq));
    ot_dp_st #(.W(1)) u_bin_xi_gc_0_leaf_procdff_71560_D__1 (.clk(clk), .rst_n(rst_n), .d(xi_gc_0_leaf_procdff_71560_D__1[0:0]), .ea(xi_gc_0_leaf_procdff_71560_D__1[1]), .q(xi_gc_0_leaf_procdff_71560_D__1_q), .eq(xi_gc_0_leaf_procdff_71560_D__1_eq));
    ot_dp_st #(.W(1)) u_bin_xi_gc_0_leaf_procdff_71560_D__2 (.clk(clk), .rst_n(rst_n), .d(xi_gc_0_leaf_procdff_71560_D__2[0:0]), .ea(xi_gc_0_leaf_procdff_71560_D__2[1]), .q(xi_gc_0_leaf_procdff_71560_D__2_q), .eq(xi_gc_0_leaf_procdff_71560_D__2_eq));
    ot_dp_st #(.W(1)) u_bin_xi_gc_0_leaf_procdff_71560_D__3 (.clk(clk), .rst_n(rst_n), .d(xi_gc_0_leaf_procdff_71560_D__3[0:0]), .ea(xi_gc_0_leaf_procdff_71560_D__3[1]), .q(xi_gc_0_leaf_procdff_71560_D__3_q), .eq(xi_gc_0_leaf_procdff_71560_D__3_eq));
    ot_dp_st #(.W(2176)) u_bin_xi_gc_0_leaf_procdff_71561_D (.clk(clk), .rst_n(rst_n), .d(xi_gc_0_leaf_procdff_71561_D[2175:0]), .ea(xi_gc_0_leaf_procdff_71561_D[2176]), .q(xi_gc_0_leaf_procdff_71561_D_q), .eq(xi_gc_0_leaf_procdff_71561_D_eq));
    ot_dp_st #(.W(20)) u_bin_xi_gc_0_leaf_procdff_71562_D__0 (.clk(clk), .rst_n(rst_n), .d(xi_gc_0_leaf_procdff_71562_D__0[19:0]), .ea(xi_gc_0_leaf_procdff_71562_D__0[20]), .q(xi_gc_0_leaf_procdff_71562_D__0_q), .eq(xi_gc_0_leaf_procdff_71562_D__0_eq));
    ot_dp_st #(.W(1)) u_bin_xi_gc_0_leaf_procdff_71562_D__1 (.clk(clk), .rst_n(rst_n), .d(xi_gc_0_leaf_procdff_71562_D__1[0:0]), .ea(xi_gc_0_leaf_procdff_71562_D__1[1]), .q(xi_gc_0_leaf_procdff_71562_D__1_q), .eq(xi_gc_0_leaf_procdff_71562_D__1_eq));
    ot_dp_st #(.W(1)) u_bin_xi_gc_0_leaf_procdff_71562_D__2 (.clk(clk), .rst_n(rst_n), .d(xi_gc_0_leaf_procdff_71562_D__2[0:0]), .ea(xi_gc_0_leaf_procdff_71562_D__2[1]), .q(xi_gc_0_leaf_procdff_71562_D__2_q), .eq(xi_gc_0_leaf_procdff_71562_D__2_eq));
    ot_dp_st #(.W(1)) u_bin_xi_gc_0_leaf_procdff_71562_D__3 (.clk(clk), .rst_n(rst_n), .d(xi_gc_0_leaf_procdff_71562_D__3[0:0]), .ea(xi_gc_0_leaf_procdff_71562_D__3[1]), .q(xi_gc_0_leaf_procdff_71562_D__3_q), .eq(xi_gc_0_leaf_procdff_71562_D__3_eq));
    ot_dp_st #(.W(1)) u_bin_xi_gc_0_leaf_procdff_71562_D__4 (.clk(clk), .rst_n(rst_n), .d(xi_gc_0_leaf_procdff_71562_D__4[0:0]), .ea(xi_gc_0_leaf_procdff_71562_D__4[1]), .q(xi_gc_0_leaf_procdff_71562_D__4_q), .eq(xi_gc_0_leaf_procdff_71562_D__4_eq));
    ot_dp_st #(.W(1)) u_bin_xi_gc_0_leaf_procdff_71562_D__5 (.clk(clk), .rst_n(rst_n), .d(xi_gc_0_leaf_procdff_71562_D__5[0:0]), .ea(xi_gc_0_leaf_procdff_71562_D__5[1]), .q(xi_gc_0_leaf_procdff_71562_D__5_q), .eq(xi_gc_0_leaf_procdff_71562_D__5_eq));
    ot_dp_st #(.W(1)) u_bin_xi_gc_0_leaf_procdff_71562_D__6 (.clk(clk), .rst_n(rst_n), .d(xi_gc_0_leaf_procdff_71562_D__6[0:0]), .ea(xi_gc_0_leaf_procdff_71562_D__6[1]), .q(xi_gc_0_leaf_procdff_71562_D__6_q), .eq(xi_gc_0_leaf_procdff_71562_D__6_eq));
    ot_dp_st #(.W(3332)) u_bout_L164_o (.clk(clk), .rst_n(rst_n), .d({w_gc_1_leaf_procdff_71556_Q[29:0], w_gc_1_leaf_procdff_71555_Q[2175:0], w_gc_1_leaf_procdff_71554_Q[3:0], w_gc_1_leaf_procdff_71553_Q[0], w_gc_1_leaf_procdff_71552_Q[567:0], w_gc_1_leaf_procdff_71551_Q[0], w_gc_1_leaf_procdff_71549_Q[551:0]}), .ea(rst_n), .q(L164_o[3331:0]), .eq(L164_o[3332]));
    ot_dp_st #(.W(634)) u_ft_L48x1_o_0 (.clk(clk), .rst_n(rst_n), .d(L48x1_i[633:0]), .ea(L48x1_i[634]), .q(L48x1_o_s0[633:0]), .eq(L48x1_o_s0[634]));
    ot_dp_st #(.W(634)) u_ft_L48x1_o_1 (.clk(clk), .rst_n(rst_n), .d(L48x1_o_s0[633:0]), .ea(L48x1_o_s0[634]), .q(L48x1_o[633:0]), .eq(L48x1_o[634]));
    ot_dp_st #(.W(612)) u_ft_L53x11_o_0 (.clk(clk), .rst_n(rst_n), .d(L53x11_i[611:0]), .ea(L53x11_i[612]), .q(L53x11_o_s0[611:0]), .eq(L53x11_o_s0[612]));
    ot_dp_st #(.W(612)) u_ft_L53x11_o_1 (.clk(clk), .rst_n(rst_n), .d(L53x11_o_s0[611:0]), .ea(L53x11_o_s0[612]), .q(L53x11_o[611:0]), .eq(L53x11_o[612]));
    assign w_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54724_Y = !w_gc_0_leaf_procdff_71563_Q[4:3];   
    assign w_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54726_Y = 2'b01 == w_gc_0_leaf_procdff_71563_Q[4:3];   
    assign w_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54728_Y = 2'b10 == w_gc_0_leaf_procdff_71563_Q[4:3];   
    assign w_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54730_Y = {2{1'b1}} == w_gc_0_leaf_procdff_71563_Q[4:3];   
    reg [31:0] g_gc_0_leaf_procdff_71548_q;
    assign w_gc_0_leaf_procdff_71548_Q = g_gc_0_leaf_procdff_71548_q;
    always @(posedge clk) g_gc_0_leaf_procdff_71548_q <= 32'b00000000000000000000000000000100;   
    reg [551:0] g_gc_0_leaf_procdff_71549_q;
    assign w_gc_0_leaf_procdff_71549_Q = g_gc_0_leaf_procdff_71549_q;
    always @(posedge clk) g_gc_0_leaf_procdff_71549_q <= w_gc_0_leaf_procdff_71550_Q[551:0];   
    reg [551:0] g_gc_0_leaf_procdff_71550_q;
    assign w_gc_0_leaf_procdff_71550_Q = g_gc_0_leaf_procdff_71550_q;
    always @(posedge clk) g_gc_0_leaf_procdff_71550_q <= {w_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54731_Y[137:0], w_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54729_Y[137:0], w_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54727_Y[137:0], w_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54725_Y[137:0]};   
    reg [0:0] g_gc_0_leaf_procdff_71551_q;
    assign w_gc_0_leaf_procdff_71551_Q = g_gc_0_leaf_procdff_71551_q;
    always @(posedge clk) g_gc_0_leaf_procdff_71551_q <= w_gc_0_leaf_procdff_71557_Q[0];   
    reg [567:0] g_gc_0_leaf_procdff_71552_q;
    assign w_gc_0_leaf_procdff_71552_Q = g_gc_0_leaf_procdff_71552_q;
    always @(posedge clk) g_gc_0_leaf_procdff_71552_q <= w_gc_0_leaf_procdff_71558_Q[567:0];   
    reg [0:0] g_gc_0_leaf_procdff_71553_q;
    assign w_gc_0_leaf_procdff_71553_Q = g_gc_0_leaf_procdff_71553_q;
    always @(posedge clk) g_gc_0_leaf_procdff_71553_q <= w_gc_0_leaf_procdff_71559_Q[0];   
    reg [3:0] g_gc_0_leaf_procdff_71554_q;
    assign w_gc_0_leaf_procdff_71554_Q = g_gc_0_leaf_procdff_71554_q;
    always @(posedge clk) g_gc_0_leaf_procdff_71554_q <= w_gc_0_leaf_procdff_71560_Q[3:0];   
    reg [2175:0] g_gc_0_leaf_procdff_71555_q;
    assign w_gc_0_leaf_procdff_71555_Q = g_gc_0_leaf_procdff_71555_q;
    always @(posedge clk) g_gc_0_leaf_procdff_71555_q <= w_gc_0_leaf_procdff_71561_Q[2175:0];   
    reg [29:0] g_gc_0_leaf_procdff_71556_q;
    assign w_gc_0_leaf_procdff_71556_Q = g_gc_0_leaf_procdff_71556_q;
    always @(posedge clk) g_gc_0_leaf_procdff_71556_q <= w_gc_0_leaf_procdff_71562_Q[29:0];   
    reg [0:0] g_gc_0_leaf_procdff_71557_q;
    assign w_gc_0_leaf_procdff_71557_Q = g_gc_0_leaf_procdff_71557_q;
    always @(posedge clk) g_gc_0_leaf_procdff_71557_q <= xi_gc_0_leaf_procdff_71557_D_q[0];   
    reg [567:0] g_gc_0_leaf_procdff_71558_q;
    assign w_gc_0_leaf_procdff_71558_Q = g_gc_0_leaf_procdff_71558_q;
    always @(posedge clk) g_gc_0_leaf_procdff_71558_q <= {3'b000,xi_gc_0_leaf_procdff_71558_D__0_q[4:0], xi_gc_0_leaf_procdff_71558_D__1_q[511:0], xi_gc_0_leaf_procdff_71558_D__2_q[31:0], xi_gc_0_leaf_procdff_71558_D__3_q[15:0]};   
    reg [0:0] g_gc_0_leaf_procdff_71559_q;
    assign w_gc_0_leaf_procdff_71559_Q = g_gc_0_leaf_procdff_71559_q;
    always @(posedge clk) g_gc_0_leaf_procdff_71559_q <= xi_gc_0_leaf_procdff_71559_D_q[0];   
    reg [3:0] g_gc_0_leaf_procdff_71560_q;
    assign w_gc_0_leaf_procdff_71560_Q = g_gc_0_leaf_procdff_71560_q;
    always @(posedge clk) g_gc_0_leaf_procdff_71560_q <= {xi_gc_0_leaf_procdff_71560_D__3_q[0], xi_gc_0_leaf_procdff_71560_D__2_q[0], xi_gc_0_leaf_procdff_71560_D__1_q[0], xi_gc_0_leaf_procdff_71560_D__0_q[0]};   
    reg [2175:0] g_gc_0_leaf_procdff_71561_q;
    assign w_gc_0_leaf_procdff_71561_Q = g_gc_0_leaf_procdff_71561_q;
    always @(posedge clk) g_gc_0_leaf_procdff_71561_q <= xi_gc_0_leaf_procdff_71561_D_q[2175:0];   
    reg [29:0] g_gc_0_leaf_procdff_71562_q;
    assign w_gc_0_leaf_procdff_71562_Q = g_gc_0_leaf_procdff_71562_q;
    always @(posedge clk) g_gc_0_leaf_procdff_71562_q <= {xi_gc_0_leaf_procdff_71562_D__6_q[0], xi_gc_0_leaf_procdff_71562_D__1_q[0], xi_gc_0_leaf_procdff_71562_D__0_q[19:0], {4{1'b0}}, xi_gc_0_leaf_procdff_71562_D__5_q[0], xi_gc_0_leaf_procdff_71562_D__4_q[0], xi_gc_0_leaf_procdff_71562_D__3_q[0], xi_gc_0_leaf_procdff_71562_D__2_q[0]};   
    reg [7:0] g_gc_0_leaf_procdff_71563_q;
    assign w_gc_0_leaf_procdff_71563_Q = g_gc_0_leaf_procdff_71563_q;
    always @(posedge clk) g_gc_0_leaf_procdff_71563_q <= {8{1'b0}};   
    assign w_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54725_Y = w_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54724_Y[0] ? {w_gc_0_leaf_core_procdff_71537_Q[0], w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_gc_0_leaf_core_u_vl_q[4:1], w_u_hb_idx_s_Q_r1c0_k3h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c0_k2h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c0_k1h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c0_k0h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c0_k3h1_cf_out[0], w_u_hb_idx_s_Q_r1c0_k2h1_cf_out[0], w_u_hb_idx_s_Q_r1c0_k1h1_cf_out[0], w_u_hb_idx_s_Q_r1c0_k0h1_cf_out[0]} : {138{1'b0}};   
    assign w_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54727_Y = w_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54726_Y[0] ? {w_gc_0_leaf_core_procdff_71537_Q[0], w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_gc_0_leaf_core_u_vl_q[4:1], w_u_hb_idx_s_Q_r1c0_k3h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c0_k2h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c0_k1h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c0_k0h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c0_k3h1_cf_out[0], w_u_hb_idx_s_Q_r1c0_k2h1_cf_out[0], w_u_hb_idx_s_Q_r1c0_k1h1_cf_out[0], w_u_hb_idx_s_Q_r1c0_k0h1_cf_out[0]} : {138{1'b0}};   
    assign w_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54729_Y = w_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54728_Y[0] ? {w_gc_0_leaf_core_procdff_71537_Q[0], w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_gc_0_leaf_core_u_vl_q[4:1], w_u_hb_idx_s_Q_r1c0_k3h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c0_k2h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c0_k1h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c0_k0h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c0_k3h1_cf_out[0], w_u_hb_idx_s_Q_r1c0_k2h1_cf_out[0], w_u_hb_idx_s_Q_r1c0_k1h1_cf_out[0], w_u_hb_idx_s_Q_r1c0_k0h1_cf_out[0]} : {138{1'b0}};   
    assign w_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54731_Y = w_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54730_Y[0] ? {w_gc_0_leaf_core_procdff_71537_Q[0], w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_gc_0_leaf_core_u_vl_q[4:1], w_u_hb_idx_s_Q_r1c0_k3h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c0_k2h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c0_k1h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c0_k0h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c0_k3h1_cf_out[0], w_u_hb_idx_s_Q_r1c0_k2h1_cf_out[0], w_u_hb_idx_s_Q_r1c0_k1h1_cf_out[0], w_u_hb_idx_s_Q_r1c0_k0h1_cf_out[0]} : {138{1'b0}};   
    assign w_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55671_Y = w_gc_0_leaf_core_procdff_71521_Q[7:0] + {8{1'b0}};   
    assign w_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55672_Y = w_gc_0_leaf_core_procdff_71521_Q[7:0] + 8'b00000001;   
    assign w_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55673_Y = w_gc_0_leaf_core_procdff_71521_Q[7:0] + 8'b00000010;   
    assign w_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55674_Y = w_gc_0_leaf_core_procdff_71521_Q[7:0] + 8'b00000011;   
    assign w_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55675_Y = w_gc_0_leaf_core_procdff_71521_Q[7:0] + 8'b00000100;   
    assign w_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55676_Y = w_gc_0_leaf_core_procdff_71521_Q[7:0] + 8'b00000101;   
    assign w_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55677_Y = w_gc_0_leaf_core_procdff_71521_Q[7:0] + 8'b00000110;   
    assign w_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55678_Y = w_gc_0_leaf_core_procdff_71521_Q[7:0] + 8'b00000111;   
    assign w_gc_0_leaf_core_auto_proc_dff_cc_220_proc_dff_71533_Y = ~rst_n;
    assign w_gc_0_leaf_core_auto_proc_dff_cc_220_proc_dff_71538_Y = ~rst_n;
    assign w_gc_0_leaf_core_auto_proc_dff_cc_220_proc_dff_71543_Y = ~rst_n;
    assign w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y = w_gc_0_leaf_procdff_71557_Q[0] && w_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[4];   
    assign w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_167_55670_Y = w_gc_0_leaf_procdff_71559_Q[0] && w_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[4];   
    assign w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y = w_gc_0_leaf_core_u_vl_q[0] && w_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[4];   
    assign w_gc_0_leaf_core_logic_not_ot_hbm_idx_chunk_rt_h_sv_154_55666_Y = !rst_n;   
    reg [31:0] g_gc_0_leaf_core_procdff_71508_q;
    assign w_gc_0_leaf_core_procdff_71508_Q = g_gc_0_leaf_core_procdff_71508_q;
    always @(posedge clk) g_gc_0_leaf_core_procdff_71508_q <= w_u_hb_idx_s_Q_r1c0_k3h1_cs_out[31:0];   
    reg [0:0] g_gc_0_leaf_core_procdff_71509_q;
    assign w_gc_0_leaf_core_procdff_71509_Q = g_gc_0_leaf_core_procdff_71509_q;
    always @(posedge clk) g_gc_0_leaf_core_procdff_71509_q <= w_u_hb_idx_s_Q_r1c0_k3h1_cf_out[0];   
    reg [31:0] g_gc_0_leaf_core_procdff_71510_q;
    assign w_gc_0_leaf_core_procdff_71510_Q = g_gc_0_leaf_core_procdff_71510_q;
    always @(posedge clk) g_gc_0_leaf_core_procdff_71510_q <= w_u_hb_idx_s_Q_r1c0_k2h1_cs_out[31:0];   
    reg [0:0] g_gc_0_leaf_core_procdff_71511_q;
    assign w_gc_0_leaf_core_procdff_71511_Q = g_gc_0_leaf_core_procdff_71511_q;
    always @(posedge clk) g_gc_0_leaf_core_procdff_71511_q <= w_u_hb_idx_s_Q_r1c0_k2h1_cf_out[0];   
    reg [31:0] g_gc_0_leaf_core_procdff_71512_q;
    assign w_gc_0_leaf_core_procdff_71512_Q = g_gc_0_leaf_core_procdff_71512_q;
    always @(posedge clk) g_gc_0_leaf_core_procdff_71512_q <= w_u_hb_idx_s_Q_r1c0_k1h1_cs_out[31:0];   
    reg [0:0] g_gc_0_leaf_core_procdff_71513_q;
    assign w_gc_0_leaf_core_procdff_71513_Q = g_gc_0_leaf_core_procdff_71513_q;
    always @(posedge clk) g_gc_0_leaf_core_procdff_71513_q <= w_u_hb_idx_s_Q_r1c0_k1h1_cf_out[0];   
    reg [31:0] g_gc_0_leaf_core_procdff_71514_q;
    assign w_gc_0_leaf_core_procdff_71514_Q = g_gc_0_leaf_core_procdff_71514_q;
    always @(posedge clk) g_gc_0_leaf_core_procdff_71514_q <= w_u_hb_idx_s_Q_r1c0_k0h1_cs_out[31:0];   
    reg [0:0] g_gc_0_leaf_core_procdff_71515_q;
    assign w_gc_0_leaf_core_procdff_71515_Q = g_gc_0_leaf_core_procdff_71515_q;
    always @(posedge clk) g_gc_0_leaf_core_procdff_71515_q <= w_u_hb_idx_s_Q_r1c0_k0h1_cf_out[0];   
    reg [0:0] g_gc_0_leaf_core_procdff_71516_q;
    assign w_gc_0_leaf_core_procdff_71516_Q = g_gc_0_leaf_core_procdff_71516_q;
    always @(posedge clk) g_gc_0_leaf_core_procdff_71516_q <= w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0];   
    reg [3:0] g_gc_0_leaf_core_procdff_71517_q;
    assign w_gc_0_leaf_core_procdff_71517_Q = g_gc_0_leaf_core_procdff_71517_q;
    always @(posedge clk) g_gc_0_leaf_core_procdff_71517_q <= w_gc_0_leaf_core_u_vl_q[4:1];   
    reg [31:0] g_gc_0_leaf_core_procdff_71518_q;
    assign w_gc_0_leaf_core_procdff_71518_Q = g_gc_0_leaf_core_procdff_71518_q;
    always @(posedge clk) g_gc_0_leaf_core_procdff_71518_q <= 32'b00000000000000000000000000001000;   
    reg [567:0] g_gc_0_leaf_core_procdff_71519_q;
    assign w_gc_0_leaf_core_procdff_71519_Q = g_gc_0_leaf_core_procdff_71519_q;
    always @(posedge clk) g_gc_0_leaf_core_procdff_71519_q <= w_gc_0_leaf_procdff_71558_Q[567:0];   
    reg [0:0] g_gc_0_leaf_core_procdff_71520_q;
    assign w_gc_0_leaf_core_procdff_71520_Q = g_gc_0_leaf_core_procdff_71520_q;
    always @(posedge clk) g_gc_0_leaf_core_procdff_71520_q <= w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_167_55670_Y[0];   
    reg [7:0] g_gc_0_leaf_core_procdff_71521_q;
    assign w_gc_0_leaf_core_procdff_71521_Q = g_gc_0_leaf_core_procdff_71521_q;
    always @(posedge clk) g_gc_0_leaf_core_procdff_71521_q <= w_gc_0_leaf_procdff_71563_Q[7:0];   
    reg [0:0] g_gc_0_leaf_core_procdff_71522_q;
    assign w_gc_0_leaf_core_procdff_71522_Q = g_gc_0_leaf_core_procdff_71522_q;
    always @(posedge clk) g_gc_0_leaf_core_procdff_71522_q <= w_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0];   
    reg [3:0] g_gc_0_leaf_core_procdff_71523_q;
    assign w_gc_0_leaf_core_procdff_71523_Q = g_gc_0_leaf_core_procdff_71523_q;
    always @(posedge clk) g_gc_0_leaf_core_procdff_71523_q <= w_gc_0_leaf_procdff_71560_Q[3:0];   
    reg [2175:0] g_gc_0_leaf_core_procdff_71524_q;
    assign w_gc_0_leaf_core_procdff_71524_Q = g_gc_0_leaf_core_procdff_71524_q;
    always @(posedge clk) g_gc_0_leaf_core_procdff_71524_q <= w_gc_0_leaf_procdff_71561_Q[2175:0];   
    reg [7:0] g_gc_0_leaf_core_procdff_71525_q;
    assign w_gc_0_leaf_core_procdff_71525_Q = g_gc_0_leaf_core_procdff_71525_q;
    always @(posedge clk) g_gc_0_leaf_core_procdff_71525_q <= w_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55671_Y[7:0];   
    reg [7:0] g_gc_0_leaf_core_procdff_71526_q;
    assign w_gc_0_leaf_core_procdff_71526_Q = g_gc_0_leaf_core_procdff_71526_q;
    always @(posedge clk) g_gc_0_leaf_core_procdff_71526_q <= w_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55672_Y[7:0];   
    reg [7:0] g_gc_0_leaf_core_procdff_71527_q;
    assign w_gc_0_leaf_core_procdff_71527_Q = g_gc_0_leaf_core_procdff_71527_q;
    always @(posedge clk) g_gc_0_leaf_core_procdff_71527_q <= w_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55673_Y[7:0];   
    reg [7:0] g_gc_0_leaf_core_procdff_71528_q;
    assign w_gc_0_leaf_core_procdff_71528_Q = g_gc_0_leaf_core_procdff_71528_q;
    always @(posedge clk) g_gc_0_leaf_core_procdff_71528_q <= w_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55674_Y[7:0];   
    reg [7:0] g_gc_0_leaf_core_procdff_71529_q;
    assign w_gc_0_leaf_core_procdff_71529_Q = g_gc_0_leaf_core_procdff_71529_q;
    always @(posedge clk) g_gc_0_leaf_core_procdff_71529_q <= w_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55675_Y[7:0];   
    reg [7:0] g_gc_0_leaf_core_procdff_71530_q;
    assign w_gc_0_leaf_core_procdff_71530_Q = g_gc_0_leaf_core_procdff_71530_q;
    always @(posedge clk) g_gc_0_leaf_core_procdff_71530_q <= w_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55676_Y[7:0];   
    reg [7:0] g_gc_0_leaf_core_procdff_71531_q;
    assign w_gc_0_leaf_core_procdff_71531_Q = g_gc_0_leaf_core_procdff_71531_q;
    always @(posedge clk) g_gc_0_leaf_core_procdff_71531_q <= w_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55677_Y[7:0];   
    reg [7:0] g_gc_0_leaf_core_procdff_71532_q;
    assign w_gc_0_leaf_core_procdff_71532_Q = g_gc_0_leaf_core_procdff_71532_q;
    always @(posedge clk) g_gc_0_leaf_core_procdff_71532_q <= w_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55678_Y[7:0];   
    reg [0:0] g_gc_0_leaf_core_procdff_71537_q;
    assign w_gc_0_leaf_core_procdff_71537_Q = g_gc_0_leaf_core_procdff_71537_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) g_gc_0_leaf_core_procdff_71537_q <= 1'b0; else g_gc_0_leaf_core_procdff_71537_q <= w_gc_0_leaf_core_reduce_and_ot_hbm_idx_chunk_rt_h_sv_155_55667_Y[0];   
    reg [15:0] g_gc_0_leaf_core_procdff_71542_q;
    assign w_gc_0_leaf_core_procdff_71542_Q = g_gc_0_leaf_core_procdff_71542_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) g_gc_0_leaf_core_procdff_71542_q <= 16'b0000000000000000; else g_gc_0_leaf_core_procdff_71542_q <= {w_u_hb_idx_s_Q_r1c0_k3h1_prdy[1:0], w_u_hb_idx_s_Q_r1c0_k3h0_prdy[1:0], w_u_hb_idx_s_Q_r1c0_k2h1_prdy[1:0], w_u_hb_idx_s_Q_r1c0_k2h0_prdy[1:0], w_u_hb_idx_s_Q_r1c0_k1h1_prdy[1:0], w_u_hb_idx_s_Q_r1c0_k1h0_prdy[1:0], w_u_hb_idx_s_Q_r1c0_k0h1_prdy[1:0], w_u_hb_idx_s_Q_r1c0_k0h0_prdy[1:0]};   
    reg [15:0] g_gc_0_leaf_core_procdff_71547_q;
    assign w_gc_0_leaf_core_procdff_71547_Q = g_gc_0_leaf_core_procdff_71547_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) g_gc_0_leaf_core_procdff_71547_q <= 16'b0000000000000000; else g_gc_0_leaf_core_procdff_71547_q <= w_gc_0_leaf_core_procdff_71542_Q[15:0];   
    assign w_gc_0_leaf_core_reduce_and_ot_hbm_idx_chunk_rt_h_sv_155_55667_Y = &w_gc_0_leaf_core_procdff_71547_Q[15:0];   
    assign w_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54724_Y = !w_gc_1_leaf_procdff_71563_Q[4:3];   
    assign w_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54726_Y = 2'b01 == w_gc_1_leaf_procdff_71563_Q[4:3];   
    assign w_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54728_Y = 2'b10 == w_gc_1_leaf_procdff_71563_Q[4:3];   
    assign w_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54730_Y = {2{1'b1}} == w_gc_1_leaf_procdff_71563_Q[4:3];   
    reg [31:0] g_gc_1_leaf_procdff_71548_q;
    assign w_gc_1_leaf_procdff_71548_Q = g_gc_1_leaf_procdff_71548_q;
    always @(posedge clk) g_gc_1_leaf_procdff_71548_q <= 32'b00000000000000000000000000000100;   
    reg [551:0] g_gc_1_leaf_procdff_71549_q;
    assign w_gc_1_leaf_procdff_71549_Q = g_gc_1_leaf_procdff_71549_q;
    always @(posedge clk) g_gc_1_leaf_procdff_71549_q <= w_gc_1_leaf_procdff_71550_Q[551:0];   
    reg [551:0] g_gc_1_leaf_procdff_71550_q;
    assign w_gc_1_leaf_procdff_71550_Q = g_gc_1_leaf_procdff_71550_q;
    always @(posedge clk) g_gc_1_leaf_procdff_71550_q <= {w_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54731_Y[137:0], w_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54729_Y[137:0], w_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54727_Y[137:0], w_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54725_Y[137:0]};   
    reg [0:0] g_gc_1_leaf_procdff_71551_q;
    assign w_gc_1_leaf_procdff_71551_Q = g_gc_1_leaf_procdff_71551_q;
    always @(posedge clk) g_gc_1_leaf_procdff_71551_q <= w_gc_1_leaf_procdff_71557_Q[0];   
    reg [567:0] g_gc_1_leaf_procdff_71552_q;
    assign w_gc_1_leaf_procdff_71552_Q = g_gc_1_leaf_procdff_71552_q;
    always @(posedge clk) g_gc_1_leaf_procdff_71552_q <= w_gc_1_leaf_procdff_71558_Q[567:0];   
    reg [0:0] g_gc_1_leaf_procdff_71553_q;
    assign w_gc_1_leaf_procdff_71553_Q = g_gc_1_leaf_procdff_71553_q;
    always @(posedge clk) g_gc_1_leaf_procdff_71553_q <= w_gc_1_leaf_procdff_71559_Q[0];   
    reg [3:0] g_gc_1_leaf_procdff_71554_q;
    assign w_gc_1_leaf_procdff_71554_Q = g_gc_1_leaf_procdff_71554_q;
    always @(posedge clk) g_gc_1_leaf_procdff_71554_q <= w_gc_1_leaf_procdff_71560_Q[3:0];   
    reg [2175:0] g_gc_1_leaf_procdff_71555_q;
    assign w_gc_1_leaf_procdff_71555_Q = g_gc_1_leaf_procdff_71555_q;
    always @(posedge clk) g_gc_1_leaf_procdff_71555_q <= w_gc_1_leaf_procdff_71561_Q[2175:0];   
    reg [29:0] g_gc_1_leaf_procdff_71556_q;
    assign w_gc_1_leaf_procdff_71556_Q = g_gc_1_leaf_procdff_71556_q;
    always @(posedge clk) g_gc_1_leaf_procdff_71556_q <= w_gc_1_leaf_procdff_71562_Q[29:0];   
    reg [0:0] g_gc_1_leaf_procdff_71557_q;
    assign w_gc_1_leaf_procdff_71557_Q = g_gc_1_leaf_procdff_71557_q;
    always @(posedge clk) g_gc_1_leaf_procdff_71557_q <= w_gc_0_leaf_procdff_71551_Q[0];   
    reg [567:0] g_gc_1_leaf_procdff_71558_q;
    assign w_gc_1_leaf_procdff_71558_Q = g_gc_1_leaf_procdff_71558_q;
    always @(posedge clk) g_gc_1_leaf_procdff_71558_q <= w_gc_0_leaf_procdff_71552_Q[567:0];   
    reg [0:0] g_gc_1_leaf_procdff_71559_q;
    assign w_gc_1_leaf_procdff_71559_Q = g_gc_1_leaf_procdff_71559_q;
    always @(posedge clk) g_gc_1_leaf_procdff_71559_q <= w_gc_0_leaf_procdff_71553_Q[0];   
    reg [3:0] g_gc_1_leaf_procdff_71560_q;
    assign w_gc_1_leaf_procdff_71560_Q = g_gc_1_leaf_procdff_71560_q;
    always @(posedge clk) g_gc_1_leaf_procdff_71560_q <= w_gc_0_leaf_procdff_71554_Q[3:0];   
    reg [2175:0] g_gc_1_leaf_procdff_71561_q;
    assign w_gc_1_leaf_procdff_71561_Q = g_gc_1_leaf_procdff_71561_q;
    always @(posedge clk) g_gc_1_leaf_procdff_71561_q <= w_gc_0_leaf_procdff_71555_Q[2175:0];   
    reg [29:0] g_gc_1_leaf_procdff_71562_q;
    assign w_gc_1_leaf_procdff_71562_Q = g_gc_1_leaf_procdff_71562_q;
    always @(posedge clk) g_gc_1_leaf_procdff_71562_q <= w_gc_0_leaf_procdff_71556_Q[29:0];   
    reg [7:0] g_gc_1_leaf_procdff_71563_q;
    assign w_gc_1_leaf_procdff_71563_Q = g_gc_1_leaf_procdff_71563_q;
    always @(posedge clk) g_gc_1_leaf_procdff_71563_q <= 8'b00001000;   
    assign w_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54725_Y = w_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54724_Y[0] ? {w_gc_1_leaf_core_procdff_71537_Q[0], w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_gc_1_leaf_core_u_vl_q[4:1], w_u_hb_idx_s_Q_r1c1_k3h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c1_k2h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c1_k1h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c1_k0h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c1_k3h1_cf_out[0], w_u_hb_idx_s_Q_r1c1_k2h1_cf_out[0], w_u_hb_idx_s_Q_r1c1_k1h1_cf_out[0], w_u_hb_idx_s_Q_r1c1_k0h1_cf_out[0]} : w_gc_0_leaf_procdff_71549_Q[137:0];   
    assign w_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54727_Y = w_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54726_Y[0] ? {w_gc_1_leaf_core_procdff_71537_Q[0], w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_gc_1_leaf_core_u_vl_q[4:1], w_u_hb_idx_s_Q_r1c1_k3h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c1_k2h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c1_k1h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c1_k0h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c1_k3h1_cf_out[0], w_u_hb_idx_s_Q_r1c1_k2h1_cf_out[0], w_u_hb_idx_s_Q_r1c1_k1h1_cf_out[0], w_u_hb_idx_s_Q_r1c1_k0h1_cf_out[0]} : w_gc_0_leaf_procdff_71549_Q[275:138];   
    assign w_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54729_Y = w_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54728_Y[0] ? {w_gc_1_leaf_core_procdff_71537_Q[0], w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_gc_1_leaf_core_u_vl_q[4:1], w_u_hb_idx_s_Q_r1c1_k3h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c1_k2h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c1_k1h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c1_k0h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c1_k3h1_cf_out[0], w_u_hb_idx_s_Q_r1c1_k2h1_cf_out[0], w_u_hb_idx_s_Q_r1c1_k1h1_cf_out[0], w_u_hb_idx_s_Q_r1c1_k0h1_cf_out[0]} : w_gc_0_leaf_procdff_71549_Q[413:276];   
    assign w_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54731_Y = w_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54730_Y[0] ? {w_gc_1_leaf_core_procdff_71537_Q[0], w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_gc_1_leaf_core_u_vl_q[4:1], w_u_hb_idx_s_Q_r1c1_k3h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c1_k2h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c1_k1h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c1_k0h1_cs_out[31:0], w_u_hb_idx_s_Q_r1c1_k3h1_cf_out[0], w_u_hb_idx_s_Q_r1c1_k2h1_cf_out[0], w_u_hb_idx_s_Q_r1c1_k1h1_cf_out[0], w_u_hb_idx_s_Q_r1c1_k0h1_cf_out[0]} : w_gc_0_leaf_procdff_71549_Q[551:414];   
    assign w_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55671_Y = w_gc_1_leaf_core_procdff_71521_Q[7:0] + {8{1'b0}};   
    assign w_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55672_Y = w_gc_1_leaf_core_procdff_71521_Q[7:0] + 8'b00000001;   
    assign w_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55673_Y = w_gc_1_leaf_core_procdff_71521_Q[7:0] + 8'b00000010;   
    assign w_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55674_Y = w_gc_1_leaf_core_procdff_71521_Q[7:0] + 8'b00000011;   
    assign w_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55675_Y = w_gc_1_leaf_core_procdff_71521_Q[7:0] + 8'b00000100;   
    assign w_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55676_Y = w_gc_1_leaf_core_procdff_71521_Q[7:0] + 8'b00000101;   
    assign w_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55677_Y = w_gc_1_leaf_core_procdff_71521_Q[7:0] + 8'b00000110;   
    assign w_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55678_Y = w_gc_1_leaf_core_procdff_71521_Q[7:0] + 8'b00000111;   
    assign w_gc_1_leaf_core_auto_proc_dff_cc_220_proc_dff_71533_Y = ~rst_n;
    assign w_gc_1_leaf_core_auto_proc_dff_cc_220_proc_dff_71538_Y = ~rst_n;
    assign w_gc_1_leaf_core_auto_proc_dff_cc_220_proc_dff_71543_Y = ~rst_n;
    assign w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y = w_gc_1_leaf_procdff_71557_Q[0] && w_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[4];   
    assign w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_167_55670_Y = w_gc_1_leaf_procdff_71559_Q[0] && w_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[4];   
    assign w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y = w_gc_1_leaf_core_u_vl_q[0] && w_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[4];   
    assign w_gc_1_leaf_core_logic_not_ot_hbm_idx_chunk_rt_h_sv_154_55666_Y = !rst_n;   
    reg [31:0] g_gc_1_leaf_core_procdff_71508_q;
    assign w_gc_1_leaf_core_procdff_71508_Q = g_gc_1_leaf_core_procdff_71508_q;
    always @(posedge clk) g_gc_1_leaf_core_procdff_71508_q <= w_u_hb_idx_s_Q_r1c1_k3h1_cs_out[31:0];   
    reg [0:0] g_gc_1_leaf_core_procdff_71509_q;
    assign w_gc_1_leaf_core_procdff_71509_Q = g_gc_1_leaf_core_procdff_71509_q;
    always @(posedge clk) g_gc_1_leaf_core_procdff_71509_q <= w_u_hb_idx_s_Q_r1c1_k3h1_cf_out[0];   
    reg [31:0] g_gc_1_leaf_core_procdff_71510_q;
    assign w_gc_1_leaf_core_procdff_71510_Q = g_gc_1_leaf_core_procdff_71510_q;
    always @(posedge clk) g_gc_1_leaf_core_procdff_71510_q <= w_u_hb_idx_s_Q_r1c1_k2h1_cs_out[31:0];   
    reg [0:0] g_gc_1_leaf_core_procdff_71511_q;
    assign w_gc_1_leaf_core_procdff_71511_Q = g_gc_1_leaf_core_procdff_71511_q;
    always @(posedge clk) g_gc_1_leaf_core_procdff_71511_q <= w_u_hb_idx_s_Q_r1c1_k2h1_cf_out[0];   
    reg [31:0] g_gc_1_leaf_core_procdff_71512_q;
    assign w_gc_1_leaf_core_procdff_71512_Q = g_gc_1_leaf_core_procdff_71512_q;
    always @(posedge clk) g_gc_1_leaf_core_procdff_71512_q <= w_u_hb_idx_s_Q_r1c1_k1h1_cs_out[31:0];   
    reg [0:0] g_gc_1_leaf_core_procdff_71513_q;
    assign w_gc_1_leaf_core_procdff_71513_Q = g_gc_1_leaf_core_procdff_71513_q;
    always @(posedge clk) g_gc_1_leaf_core_procdff_71513_q <= w_u_hb_idx_s_Q_r1c1_k1h1_cf_out[0];   
    reg [31:0] g_gc_1_leaf_core_procdff_71514_q;
    assign w_gc_1_leaf_core_procdff_71514_Q = g_gc_1_leaf_core_procdff_71514_q;
    always @(posedge clk) g_gc_1_leaf_core_procdff_71514_q <= w_u_hb_idx_s_Q_r1c1_k0h1_cs_out[31:0];   
    reg [0:0] g_gc_1_leaf_core_procdff_71515_q;
    assign w_gc_1_leaf_core_procdff_71515_Q = g_gc_1_leaf_core_procdff_71515_q;
    always @(posedge clk) g_gc_1_leaf_core_procdff_71515_q <= w_u_hb_idx_s_Q_r1c1_k0h1_cf_out[0];   
    reg [0:0] g_gc_1_leaf_core_procdff_71516_q;
    assign w_gc_1_leaf_core_procdff_71516_Q = g_gc_1_leaf_core_procdff_71516_q;
    always @(posedge clk) g_gc_1_leaf_core_procdff_71516_q <= w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0];   
    reg [3:0] g_gc_1_leaf_core_procdff_71517_q;
    assign w_gc_1_leaf_core_procdff_71517_Q = g_gc_1_leaf_core_procdff_71517_q;
    always @(posedge clk) g_gc_1_leaf_core_procdff_71517_q <= w_gc_1_leaf_core_u_vl_q[4:1];   
    reg [31:0] g_gc_1_leaf_core_procdff_71518_q;
    assign w_gc_1_leaf_core_procdff_71518_Q = g_gc_1_leaf_core_procdff_71518_q;
    always @(posedge clk) g_gc_1_leaf_core_procdff_71518_q <= 32'b00000000000000000000000000001000;   
    reg [567:0] g_gc_1_leaf_core_procdff_71519_q;
    assign w_gc_1_leaf_core_procdff_71519_Q = g_gc_1_leaf_core_procdff_71519_q;
    always @(posedge clk) g_gc_1_leaf_core_procdff_71519_q <= w_gc_1_leaf_procdff_71558_Q[567:0];   
    reg [0:0] g_gc_1_leaf_core_procdff_71520_q;
    assign w_gc_1_leaf_core_procdff_71520_Q = g_gc_1_leaf_core_procdff_71520_q;
    always @(posedge clk) g_gc_1_leaf_core_procdff_71520_q <= w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_167_55670_Y[0];   
    reg [7:0] g_gc_1_leaf_core_procdff_71521_q;
    assign w_gc_1_leaf_core_procdff_71521_Q = g_gc_1_leaf_core_procdff_71521_q;
    always @(posedge clk) g_gc_1_leaf_core_procdff_71521_q <= w_gc_1_leaf_procdff_71563_Q[7:0];   
    reg [0:0] g_gc_1_leaf_core_procdff_71522_q;
    assign w_gc_1_leaf_core_procdff_71522_Q = g_gc_1_leaf_core_procdff_71522_q;
    always @(posedge clk) g_gc_1_leaf_core_procdff_71522_q <= w_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0];   
    reg [3:0] g_gc_1_leaf_core_procdff_71523_q;
    assign w_gc_1_leaf_core_procdff_71523_Q = g_gc_1_leaf_core_procdff_71523_q;
    always @(posedge clk) g_gc_1_leaf_core_procdff_71523_q <= w_gc_1_leaf_procdff_71560_Q[3:0];   
    reg [2175:0] g_gc_1_leaf_core_procdff_71524_q;
    assign w_gc_1_leaf_core_procdff_71524_Q = g_gc_1_leaf_core_procdff_71524_q;
    always @(posedge clk) g_gc_1_leaf_core_procdff_71524_q <= w_gc_1_leaf_procdff_71561_Q[2175:0];   
    reg [7:0] g_gc_1_leaf_core_procdff_71525_q;
    assign w_gc_1_leaf_core_procdff_71525_Q = g_gc_1_leaf_core_procdff_71525_q;
    always @(posedge clk) g_gc_1_leaf_core_procdff_71525_q <= w_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55671_Y[7:0];   
    reg [7:0] g_gc_1_leaf_core_procdff_71526_q;
    assign w_gc_1_leaf_core_procdff_71526_Q = g_gc_1_leaf_core_procdff_71526_q;
    always @(posedge clk) g_gc_1_leaf_core_procdff_71526_q <= w_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55672_Y[7:0];   
    reg [7:0] g_gc_1_leaf_core_procdff_71527_q;
    assign w_gc_1_leaf_core_procdff_71527_Q = g_gc_1_leaf_core_procdff_71527_q;
    always @(posedge clk) g_gc_1_leaf_core_procdff_71527_q <= w_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55673_Y[7:0];   
    reg [7:0] g_gc_1_leaf_core_procdff_71528_q;
    assign w_gc_1_leaf_core_procdff_71528_Q = g_gc_1_leaf_core_procdff_71528_q;
    always @(posedge clk) g_gc_1_leaf_core_procdff_71528_q <= w_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55674_Y[7:0];   
    reg [7:0] g_gc_1_leaf_core_procdff_71529_q;
    assign w_gc_1_leaf_core_procdff_71529_Q = g_gc_1_leaf_core_procdff_71529_q;
    always @(posedge clk) g_gc_1_leaf_core_procdff_71529_q <= w_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55675_Y[7:0];   
    reg [7:0] g_gc_1_leaf_core_procdff_71530_q;
    assign w_gc_1_leaf_core_procdff_71530_Q = g_gc_1_leaf_core_procdff_71530_q;
    always @(posedge clk) g_gc_1_leaf_core_procdff_71530_q <= w_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55676_Y[7:0];   
    reg [7:0] g_gc_1_leaf_core_procdff_71531_q;
    assign w_gc_1_leaf_core_procdff_71531_Q = g_gc_1_leaf_core_procdff_71531_q;
    always @(posedge clk) g_gc_1_leaf_core_procdff_71531_q <= w_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55677_Y[7:0];   
    reg [7:0] g_gc_1_leaf_core_procdff_71532_q;
    assign w_gc_1_leaf_core_procdff_71532_Q = g_gc_1_leaf_core_procdff_71532_q;
    always @(posedge clk) g_gc_1_leaf_core_procdff_71532_q <= w_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55678_Y[7:0];   
    reg [0:0] g_gc_1_leaf_core_procdff_71537_q;
    assign w_gc_1_leaf_core_procdff_71537_Q = g_gc_1_leaf_core_procdff_71537_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) g_gc_1_leaf_core_procdff_71537_q <= 1'b0; else g_gc_1_leaf_core_procdff_71537_q <= w_gc_1_leaf_core_reduce_and_ot_hbm_idx_chunk_rt_h_sv_155_55667_Y[0];   
    reg [15:0] g_gc_1_leaf_core_procdff_71542_q;
    assign w_gc_1_leaf_core_procdff_71542_Q = g_gc_1_leaf_core_procdff_71542_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) g_gc_1_leaf_core_procdff_71542_q <= 16'b0000000000000000; else g_gc_1_leaf_core_procdff_71542_q <= {w_u_hb_idx_s_Q_r1c1_k3h1_prdy[1:0], w_u_hb_idx_s_Q_r1c1_k3h0_prdy[1:0], w_u_hb_idx_s_Q_r1c1_k2h1_prdy[1:0], w_u_hb_idx_s_Q_r1c1_k2h0_prdy[1:0], w_u_hb_idx_s_Q_r1c1_k1h1_prdy[1:0], w_u_hb_idx_s_Q_r1c1_k1h0_prdy[1:0], w_u_hb_idx_s_Q_r1c1_k0h1_prdy[1:0], w_u_hb_idx_s_Q_r1c1_k0h0_prdy[1:0]};   
    reg [15:0] g_gc_1_leaf_core_procdff_71547_q;
    assign w_gc_1_leaf_core_procdff_71547_Q = g_gc_1_leaf_core_procdff_71547_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) g_gc_1_leaf_core_procdff_71547_q <= 16'b0000000000000000; else g_gc_1_leaf_core_procdff_71547_q <= w_gc_1_leaf_core_procdff_71542_Q[15:0];   
    assign w_gc_1_leaf_core_reduce_and_ot_hbm_idx_chunk_rt_h_sv_155_55667_Y = &w_gc_1_leaf_core_procdff_71547_Q[15:0];   
     
    ot_rst_delivered3 #(.REGIONS(5)) u_gc_0_leaf_core_g_delivered_reset_u_rr (
        .clk(clk),
        .rst_n(w_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n),
        .rst_n_in(rst_n)
    );
     
    ot_hdc_delay #(.D(0), .W(569)) u_gc_0_leaf_core_u_qlate (
        .clk(clk),
        .d({w_gc_0_leaf_core_procdff_71522_Q[0], w_gc_0_leaf_core_procdff_71519_Q[567:0]}),
        .q(w_gc_0_leaf_core_u_qlate_q),
        .rst_n(1'b1)
    );
     
    ot_hdc_delay #(.D(104), .RESET(1), .W(5)) u_gc_0_leaf_core_u_vl (
        .clk(clk),
        .d({w_gc_0_leaf_core_procdff_71523_Q[3:0], w_gc_0_leaf_core_procdff_71520_Q[0]}),
        .q(w_gc_0_leaf_core_u_vl_q),
        .rst_n(w_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[4])
    );
     
    ot_rst_delivered3 #(.REGIONS(5)) u_gc_1_leaf_core_g_delivered_reset_u_rr (
        .clk(clk),
        .rst_n(w_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n),
        .rst_n_in(rst_n)
    );
     
    ot_hdc_delay #(.D(0), .W(569)) u_gc_1_leaf_core_u_qlate (
        .clk(clk),
        .d({w_gc_1_leaf_core_procdff_71522_Q[0], w_gc_1_leaf_core_procdff_71519_Q[567:0]}),
        .q(w_gc_1_leaf_core_u_qlate_q),
        .rst_n(1'b1)
    );
     
    ot_hdc_delay #(.D(104), .RESET(1), .W(5)) u_gc_1_leaf_core_u_vl (
        .clk(clk),
        .d({w_gc_1_leaf_core_procdff_71523_Q[3:0], w_gc_1_leaf_core_procdff_71520_Q[0]}),
        .q(w_gc_1_leaf_core_u_vl_q),
        .rst_n(w_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[4])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r1c0_k0h0 (
        .cf_out(w_u_hb_idx_s_Q_r1c0_k0h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q_r1c0_k0h0_cs_out),
        .hid4({w_gc_0_leaf_core_procdff_71528_Q[7:0], w_gc_0_leaf_core_procdff_71527_Q[7:0], w_gc_0_leaf_core_procdff_71526_Q[7:0], w_gc_0_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_gc_0_leaf_core_procdff_71524_Q[543:0]),
        .prdy(w_u_hb_idx_s_Q_r1c0_k0h0_prdy),
        .q_b(w_gc_0_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_gc_0_leaf_core_u_qlate_q[568]),
        .rst_col(w_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[0])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r1c0_k0h1 (
        .cf_in(w_u_hb_idx_s_Q_r1c0_k0h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q_r1c0_k0h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q_r1c0_k0h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q_r1c0_k0h1_cs_out),
        .hid4({w_gc_0_leaf_core_procdff_71532_Q[7:0], w_gc_0_leaf_core_procdff_71531_Q[7:0], w_gc_0_leaf_core_procdff_71530_Q[7:0], w_gc_0_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_gc_0_leaf_core_procdff_71524_Q[543:0]),
        .prdy(w_u_hb_idx_s_Q_r1c0_k0h1_prdy),
        .q_b(w_gc_0_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_gc_0_leaf_core_u_qlate_q[568]),
        .rst_col(w_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[0])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r1c0_k1h0 (
        .cf_out(w_u_hb_idx_s_Q_r1c0_k1h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q_r1c0_k1h0_cs_out),
        .hid4({w_gc_0_leaf_core_procdff_71528_Q[7:0], w_gc_0_leaf_core_procdff_71527_Q[7:0], w_gc_0_leaf_core_procdff_71526_Q[7:0], w_gc_0_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_gc_0_leaf_core_procdff_71524_Q[1087:544]),
        .prdy(w_u_hb_idx_s_Q_r1c0_k1h0_prdy),
        .q_b(w_gc_0_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_gc_0_leaf_core_u_qlate_q[568]),
        .rst_col(w_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[1])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r1c0_k1h1 (
        .cf_in(w_u_hb_idx_s_Q_r1c0_k1h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q_r1c0_k1h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q_r1c0_k1h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q_r1c0_k1h1_cs_out),
        .hid4({w_gc_0_leaf_core_procdff_71532_Q[7:0], w_gc_0_leaf_core_procdff_71531_Q[7:0], w_gc_0_leaf_core_procdff_71530_Q[7:0], w_gc_0_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_gc_0_leaf_core_procdff_71524_Q[1087:544]),
        .prdy(w_u_hb_idx_s_Q_r1c0_k1h1_prdy),
        .q_b(w_gc_0_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_gc_0_leaf_core_u_qlate_q[568]),
        .rst_col(w_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[1])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r1c0_k2h0 (
        .cf_out(w_u_hb_idx_s_Q_r1c0_k2h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q_r1c0_k2h0_cs_out),
        .hid4({w_gc_0_leaf_core_procdff_71528_Q[7:0], w_gc_0_leaf_core_procdff_71527_Q[7:0], w_gc_0_leaf_core_procdff_71526_Q[7:0], w_gc_0_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_gc_0_leaf_core_procdff_71524_Q[1631:1088]),
        .prdy(w_u_hb_idx_s_Q_r1c0_k2h0_prdy),
        .q_b(w_gc_0_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_gc_0_leaf_core_u_qlate_q[568]),
        .rst_col(w_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[2])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r1c0_k2h1 (
        .cf_in(w_u_hb_idx_s_Q_r1c0_k2h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q_r1c0_k2h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q_r1c0_k2h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q_r1c0_k2h1_cs_out),
        .hid4({w_gc_0_leaf_core_procdff_71532_Q[7:0], w_gc_0_leaf_core_procdff_71531_Q[7:0], w_gc_0_leaf_core_procdff_71530_Q[7:0], w_gc_0_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_gc_0_leaf_core_procdff_71524_Q[1631:1088]),
        .prdy(w_u_hb_idx_s_Q_r1c0_k2h1_prdy),
        .q_b(w_gc_0_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_gc_0_leaf_core_u_qlate_q[568]),
        .rst_col(w_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[2])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r1c0_k3h0 (
        .cf_out(w_u_hb_idx_s_Q_r1c0_k3h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q_r1c0_k3h0_cs_out),
        .hid4({w_gc_0_leaf_core_procdff_71528_Q[7:0], w_gc_0_leaf_core_procdff_71527_Q[7:0], w_gc_0_leaf_core_procdff_71526_Q[7:0], w_gc_0_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_gc_0_leaf_core_procdff_71524_Q[2175:1632]),
        .prdy(w_u_hb_idx_s_Q_r1c0_k3h0_prdy),
        .q_b(w_gc_0_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_gc_0_leaf_core_u_qlate_q[568]),
        .rst_col(w_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[3])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r1c0_k3h1 (
        .cf_in(w_u_hb_idx_s_Q_r1c0_k3h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q_r1c0_k3h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q_r1c0_k3h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q_r1c0_k3h1_cs_out),
        .hid4({w_gc_0_leaf_core_procdff_71532_Q[7:0], w_gc_0_leaf_core_procdff_71531_Q[7:0], w_gc_0_leaf_core_procdff_71530_Q[7:0], w_gc_0_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_gc_0_leaf_core_procdff_71524_Q[2175:1632]),
        .prdy(w_u_hb_idx_s_Q_r1c0_k3h1_prdy),
        .q_b(w_gc_0_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_gc_0_leaf_core_u_qlate_q[568]),
        .rst_col(w_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[3])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r1c1_k0h0 (
        .cf_out(w_u_hb_idx_s_Q_r1c1_k0h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q_r1c1_k0h0_cs_out),
        .hid4({w_gc_1_leaf_core_procdff_71528_Q[7:0], w_gc_1_leaf_core_procdff_71527_Q[7:0], w_gc_1_leaf_core_procdff_71526_Q[7:0], w_gc_1_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_gc_1_leaf_core_procdff_71524_Q[543:0]),
        .prdy(w_u_hb_idx_s_Q_r1c1_k0h0_prdy),
        .q_b(w_gc_1_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_gc_1_leaf_core_u_qlate_q[568]),
        .rst_col(w_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[0])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r1c1_k0h1 (
        .cf_in(w_u_hb_idx_s_Q_r1c1_k0h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q_r1c1_k0h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q_r1c1_k0h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q_r1c1_k0h1_cs_out),
        .hid4({w_gc_1_leaf_core_procdff_71532_Q[7:0], w_gc_1_leaf_core_procdff_71531_Q[7:0], w_gc_1_leaf_core_procdff_71530_Q[7:0], w_gc_1_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_gc_1_leaf_core_procdff_71524_Q[543:0]),
        .prdy(w_u_hb_idx_s_Q_r1c1_k0h1_prdy),
        .q_b(w_gc_1_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_gc_1_leaf_core_u_qlate_q[568]),
        .rst_col(w_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[0])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r1c1_k1h0 (
        .cf_out(w_u_hb_idx_s_Q_r1c1_k1h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q_r1c1_k1h0_cs_out),
        .hid4({w_gc_1_leaf_core_procdff_71528_Q[7:0], w_gc_1_leaf_core_procdff_71527_Q[7:0], w_gc_1_leaf_core_procdff_71526_Q[7:0], w_gc_1_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_gc_1_leaf_core_procdff_71524_Q[1087:544]),
        .prdy(w_u_hb_idx_s_Q_r1c1_k1h0_prdy),
        .q_b(w_gc_1_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_gc_1_leaf_core_u_qlate_q[568]),
        .rst_col(w_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[1])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r1c1_k1h1 (
        .cf_in(w_u_hb_idx_s_Q_r1c1_k1h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q_r1c1_k1h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q_r1c1_k1h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q_r1c1_k1h1_cs_out),
        .hid4({w_gc_1_leaf_core_procdff_71532_Q[7:0], w_gc_1_leaf_core_procdff_71531_Q[7:0], w_gc_1_leaf_core_procdff_71530_Q[7:0], w_gc_1_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_gc_1_leaf_core_procdff_71524_Q[1087:544]),
        .prdy(w_u_hb_idx_s_Q_r1c1_k1h1_prdy),
        .q_b(w_gc_1_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_gc_1_leaf_core_u_qlate_q[568]),
        .rst_col(w_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[1])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r1c1_k2h0 (
        .cf_out(w_u_hb_idx_s_Q_r1c1_k2h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q_r1c1_k2h0_cs_out),
        .hid4({w_gc_1_leaf_core_procdff_71528_Q[7:0], w_gc_1_leaf_core_procdff_71527_Q[7:0], w_gc_1_leaf_core_procdff_71526_Q[7:0], w_gc_1_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_gc_1_leaf_core_procdff_71524_Q[1631:1088]),
        .prdy(w_u_hb_idx_s_Q_r1c1_k2h0_prdy),
        .q_b(w_gc_1_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_gc_1_leaf_core_u_qlate_q[568]),
        .rst_col(w_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[2])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r1c1_k2h1 (
        .cf_in(w_u_hb_idx_s_Q_r1c1_k2h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q_r1c1_k2h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q_r1c1_k2h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q_r1c1_k2h1_cs_out),
        .hid4({w_gc_1_leaf_core_procdff_71532_Q[7:0], w_gc_1_leaf_core_procdff_71531_Q[7:0], w_gc_1_leaf_core_procdff_71530_Q[7:0], w_gc_1_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_gc_1_leaf_core_procdff_71524_Q[1631:1088]),
        .prdy(w_u_hb_idx_s_Q_r1c1_k2h1_prdy),
        .q_b(w_gc_1_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_gc_1_leaf_core_u_qlate_q[568]),
        .rst_col(w_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[2])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r1c1_k3h0 (
        .cf_out(w_u_hb_idx_s_Q_r1c1_k3h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q_r1c1_k3h0_cs_out),
        .hid4({w_gc_1_leaf_core_procdff_71528_Q[7:0], w_gc_1_leaf_core_procdff_71527_Q[7:0], w_gc_1_leaf_core_procdff_71526_Q[7:0], w_gc_1_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_gc_1_leaf_core_procdff_71524_Q[2175:1632]),
        .prdy(w_u_hb_idx_s_Q_r1c1_k3h0_prdy),
        .q_b(w_gc_1_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_gc_1_leaf_core_u_qlate_q[568]),
        .rst_col(w_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[3])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r1c1_k3h1 (
        .cf_in(w_u_hb_idx_s_Q_r1c1_k3h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q_r1c1_k3h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q_r1c1_k3h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q_r1c1_k3h1_cs_out),
        .hid4({w_gc_1_leaf_core_procdff_71532_Q[7:0], w_gc_1_leaf_core_procdff_71531_Q[7:0], w_gc_1_leaf_core_procdff_71530_Q[7:0], w_gc_1_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_gc_1_leaf_core_procdff_71524_Q[2175:1632]),
        .prdy(w_u_hb_idx_s_Q_r1c1_k3h1_prdy),
        .q_b(w_gc_1_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_gc_1_leaf_core_u_qlate_q[568]),
        .rst_col(w_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[3])
    );
endmodule
