module hbm_arch_q_b100__physical_v1 (
    input  wire clk,
    input  wire arst_n,
    output wire rst_o_0,    
    input  wire [178:0] L203m_i,    
    input  wire [828:0] L6_i,    
    input  wire [828:0] L6b_i,    
    input  wire [828:0] L6c_i,    
    input  wire [2484:0] L7_i,    
    input  wire [20:0] L91_i,    
    output wire [3332:0] L401m_o,    
    output wire [20:0] xo_add_ot_hbm_idx_score_quarter_static_h_sv_91_54986_Y,    
    output wire [1:0] xo_ge_ot_hbm_idx_score_quarter_static_h_sv_92_54989_Y,    
    output wire [1:0] xo_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54959_Y,    
    output wire [1:0] xo_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54967_Y,    
    output wire [1:0] xo_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54975_Y,    
    output wire [1:0] xo_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54983_Y,    
    output wire [1:0] xo_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54956_Y,    
    output wire [1:0] xo_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54964_Y,    
    output wire [1:0] xo_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54972_Y,    
    output wire [1:0] xo_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54980_Y,    
    output wire [1:0] xo_procdff_71763_Q,    
    output wire [8:0] xo_procdff_71764_Q,    
    output wire [512:0] xo_procdff_71765_Q,    
    output wire [32:0] xo_procdff_71766_Q,    
    output wire [16:0] xo_procdff_71767_Q,    
    output wire [1:0] xo_procdff_71768_Q,    
    output wire [2176:0] xo_procdff_71770_Q,    
    output wire [1:0] xo_procmux_66659_Y,    
    input  wire [22:0] L100r0_1_i,    
    output wire [22:0] L100r0_1_o,    
    input  wire [11:0] L117x5_i,    
    output wire [11:0] L117x5_o,    
    input  wire [9:0] L123r0_1_i,    
    output wire [9:0] L123r0_1_o,    
    input  wire [2:0] L138x5_i,    
    output wire [2:0] L138x5_o,    
    input  wire [7:0] L48x8_i,    
    output wire [7:0] L48x8_o,    
    input  wire [268:0] L70r0_1_i,    
    output wire [268:0] L70r0_1_o,    
    input  wire [37:0] L721x1_i,    
    output wire [37:0] L721x1_o    
);
    wire [177:0] L203m_i_q;
    wire L203m_i_eq;
    wire [827:0] L6_i_q;
    wire L6_i_eq;
    wire [827:0] L6_i_b;
    wire L6_i_eb;
    wire [827:0] L6b_i_q;
    wire L6b_i_eq;
    wire [827:0] L6c_i_q;
    wire L6c_i_eq;
    wire [827:0] L6c_i_b;
    wire L6c_i_eb;
    wire [2483:0] L7_i_q;
    wire L7_i_eq;
    wire [19:0] L91_i_q;
    wire L91_i_eq;
    wire [19:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_71_54855_Y;
    wire [19:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_71_54857_Y;
    wire [31:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_77_54866_Y;
    wire [31:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_77_54868_Y;
    wire [31:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_77_54873_Y;
    wire [31:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_77_54875_Y;
    wire [31:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_77_54880_Y;
    wire [31:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_77_54882_Y;
    wire [31:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_77_54887_Y;
    wire [31:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_77_54889_Y;
    wire [11:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54897_Y;
    wire [11:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54899_Y;
    wire [11:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54905_Y;
    wire [11:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54907_Y;
    wire [11:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54913_Y;
    wire [11:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54915_Y;
    wire [11:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54921_Y;
    wire [11:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54923_Y;
    wire [11:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54953_Y;
    wire [11:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54955_Y;
    wire [11:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54961_Y;
    wire [11:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54963_Y;
    wire [11:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54969_Y;
    wire [11:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54971_Y;
    wire [11:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54977_Y;
    wire [11:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54979_Y;
    wire [19:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_91_54929_Y;
    wire [19:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_91_54930_Y;
    wire [19:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_91_54985_Y;
    wire [19:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_91_54986_Y;
    wire [11:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_92_54931_Y;
    wire [11:0] w_add_ot_hbm_idx_score_quarter_static_h_sv_92_54987_Y;
    wire [0:0] w_auto_proc_dff_cc_220_proc_dff_71688_Y;
    wire [0:0] w_auto_proc_dff_cc_220_proc_dff_71693_Y;
    wire [0:0] w_auto_proc_dff_cc_220_proc_dff_71698_Y;
    wire [0:0] w_auto_proc_dff_cc_220_proc_dff_71703_Y;
    wire [0:0] w_auto_proc_dff_cc_220_proc_dff_71708_Y;
    wire [0:0] w_auto_proc_dff_cc_220_proc_dff_71713_Y;
    wire [0:0] w_auto_proc_dff_cc_220_proc_dff_71721_Y;
    wire [0:0] w_auto_proc_dff_cc_220_proc_dff_71726_Y;
    wire [0:0] w_auto_proc_dff_cc_220_proc_dff_71731_Y;
    wire [0:0] w_auto_proc_dff_cc_220_proc_dff_71736_Y;
    wire [0:0] w_auto_proc_dff_cc_220_proc_dff_71741_Y;
    wire [0:0] w_auto_proc_dff_cc_220_proc_dff_71746_Y;
    wire [0:0] w_auto_proc_dff_cc_220_proc_dff_71752_Y;
    wire [0:0] w_ge_ot_hbm_idx_score_quarter_static_h_sv_92_54933_Y;
    wire [0:0] w_ge_ot_hbm_idx_score_quarter_static_h_sv_92_54989_Y;
    wire [0:0] w_gt_ot_hbm_idx_score_quarter_static_h_sv_76_54861_Y;
    wire [0:0] w_gt_ot_hbm_idx_score_quarter_static_h_sv_76_54862_Y;
    wire [0:0] w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_120_54935_Y;
    wire [0:0] w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_120_54991_Y;
    wire [0:0] w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_139_54945_Y;
    wire [0:0] w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_139_55001_Y;
    wire [0:0] w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_153_54893_Y;
    wire [0:0] w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_77_54864_Y;
    wire [0:0] w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_77_54871_Y;
    wire [0:0] w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_77_54878_Y;
    wire [0:0] w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_77_54885_Y;
    wire [0:0] w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54901_Y;
    wire [0:0] w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54909_Y;
    wire [0:0] w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54917_Y;
    wire [0:0] w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54925_Y;
    wire [0:0] w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54957_Y;
    wire [0:0] w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54965_Y;
    wire [0:0] w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54973_Y;
    wire [0:0] w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54981_Y;
    wire [0:0] w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_76_54863_Y;
    wire [0:0] w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_77_54870_Y;
    wire [0:0] w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_77_54877_Y;
    wire [0:0] w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_77_54884_Y;
    wire [0:0] w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_77_54891_Y;
    wire [0:0] w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54903_Y;
    wire [0:0] w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54911_Y;
    wire [0:0] w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54919_Y;
    wire [0:0] w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54927_Y;
    wire [0:0] w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54959_Y;
    wire [0:0] w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54967_Y;
    wire [0:0] w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54975_Y;
    wire [0:0] w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54983_Y;
    wire [0:0] w_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54900_Y;
    wire [0:0] w_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54908_Y;
    wire [0:0] w_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54916_Y;
    wire [0:0] w_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54924_Y;
    wire [0:0] w_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54956_Y;
    wire [0:0] w_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54964_Y;
    wire [0:0] w_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54972_Y;
    wire [0:0] w_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54980_Y;
    wire [19:0] w_mul_ot_hbm_idx_score_quarter_static_h_sv_71_54853_Y;
    wire [19:0] w_mul_ot_hbm_idx_score_quarter_static_h_sv_71_54854_Y;
    wire [19:0] w_mul_ot_hbm_idx_score_quarter_static_h_sv_71_54856_Y;
    wire [31:0] w_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54865_Y;
    wire [31:0] w_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54867_Y;
    wire [31:0] w_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54872_Y;
    wire [31:0] w_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54874_Y;
    wire [31:0] w_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54879_Y;
    wire [31:0] w_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54881_Y;
    wire [31:0] w_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54886_Y;
    wire [31:0] w_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54888_Y;
    wire [11:0] w_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54896_Y;
    wire [11:0] w_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54904_Y;
    wire [11:0] w_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54912_Y;
    wire [11:0] w_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54920_Y;
    wire [11:0] w_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54952_Y;
    wire [11:0] w_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54960_Y;
    wire [11:0] w_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54968_Y;
    wire [11:0] w_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54976_Y;
    wire [11:0] w_mul_ot_hbm_idx_score_quarter_static_h_sv_92_54932_Y;
    wire [11:0] w_mul_ot_hbm_idx_score_quarter_static_h_sv_92_54988_Y;
    wire [0:0] w_nex_ot_hbm_idx_score_quarter_static_h_sv_77_54869_Y;
    wire [0:0] w_nex_ot_hbm_idx_score_quarter_static_h_sv_77_54876_Y;
    wire [0:0] w_nex_ot_hbm_idx_score_quarter_static_h_sv_77_54883_Y;
    wire [0:0] w_nex_ot_hbm_idx_score_quarter_static_h_sv_77_54890_Y;
    wire [0:0] w_procdff_71757_Q;
    wire [7:0] w_procdff_71758_Q;
    wire [10:0] w_procdff_71759_Q;
    wire [11:0] w_procdff_71760_Q;
    wire [0:0] w_procdff_71761_Q;
    wire [170:0] w_procdff_71762_Q;
    wire [0:0] w_procdff_71763_Q;
    wire [7:0] w_procdff_71764_Q;
    wire [511:0] w_procdff_71765_Q;
    wire [31:0] w_procdff_71766_Q;
    wire [15:0] w_procdff_71767_Q;
    wire [0:0] w_procdff_71768_Q;
    wire [7:0] w_procdff_71769_Q;
    wire [4395:0] w_procdff_71770_Q;
    wire [0:0] w_procmux_66627_Y;
    wire [0:0] w_procmux_66629_Y;
    wire [0:0] w_procmux_66633_Y;
    wire [0:0] w_procmux_66635_Y;
    wire [0:0] w_procmux_66639_Y;
    wire [0:0] w_procmux_66641_Y;
    wire [0:0] w_procmux_66645_Y;
    wire [0:0] w_procmux_66647_Y;
    wire [0:0] w_procmux_66651_Y;
    wire [0:0] w_procmux_66653_Y;
    wire [0:0] w_procmux_66659_Y;
    wire [0:0] w_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54902_Y;
    wire [0:0] w_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54910_Y;
    wire [0:0] w_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54918_Y;
    wire [0:0] w_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54926_Y;
    wire [0:0] w_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54958_Y;
    wire [0:0] w_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54966_Y;
    wire [0:0] w_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54974_Y;
    wire [0:0] w_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54982_Y;
    wire [11:0] w_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54898_Y;
    wire [11:0] w_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54906_Y;
    wire [11:0] w_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54914_Y;
    wire [11:0] w_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54922_Y;
    wire [11:0] w_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54954_Y;
    wire [11:0] w_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54962_Y;
    wire [11:0] w_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54970_Y;
    wire [11:0] w_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54978_Y;
    wire [19:0] w_ternary_ot_hbm_idx_score_quarter_static_h_sv_91_54928_Y;
    wire [19:0] w_ternary_ot_hbm_idx_score_quarter_static_h_sv_91_54984_Y;
    wire [0:0] w_g_delivered_reset_u_rr_rst_n;
    wire [0:0] w_ge_0_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54724_Y;
    wire [0:0] w_ge_0_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54726_Y;
    wire [0:0] w_ge_0_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54728_Y;
    wire [0:0] w_ge_0_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54730_Y;
    wire [31:0] w_ge_0_gc_0_leaf_procdff_71548_Q;
    wire [551:0] w_ge_0_gc_0_leaf_procdff_71549_Q;
    wire [551:0] w_ge_0_gc_0_leaf_procdff_71550_Q;
    wire [0:0] w_ge_0_gc_0_leaf_procdff_71551_Q;
    wire [567:0] w_ge_0_gc_0_leaf_procdff_71552_Q;
    wire [0:0] w_ge_0_gc_0_leaf_procdff_71553_Q;
    wire [3:0] w_ge_0_gc_0_leaf_procdff_71554_Q;
    wire [2175:0] w_ge_0_gc_0_leaf_procdff_71555_Q;
    wire [29:0] w_ge_0_gc_0_leaf_procdff_71556_Q;
    wire [0:0] w_ge_0_gc_0_leaf_procdff_71557_Q;
    wire [567:0] w_ge_0_gc_0_leaf_procdff_71558_Q;
    wire [0:0] w_ge_0_gc_0_leaf_procdff_71559_Q;
    wire [3:0] w_ge_0_gc_0_leaf_procdff_71560_Q;
    wire [2175:0] w_ge_0_gc_0_leaf_procdff_71561_Q;
    wire [29:0] w_ge_0_gc_0_leaf_procdff_71562_Q;
    wire [7:0] w_ge_0_gc_0_leaf_procdff_71563_Q;
    wire [137:0] w_ge_0_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54725_Y;
    wire [137:0] w_ge_0_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54727_Y;
    wire [137:0] w_ge_0_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54729_Y;
    wire [137:0] w_ge_0_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54731_Y;
    wire [7:0] w_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55671_Y;
    wire [7:0] w_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55672_Y;
    wire [7:0] w_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55673_Y;
    wire [7:0] w_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55674_Y;
    wire [7:0] w_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55675_Y;
    wire [7:0] w_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55676_Y;
    wire [7:0] w_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55677_Y;
    wire [7:0] w_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55678_Y;
    wire [0:0] w_ge_0_gc_0_leaf_core_auto_proc_dff_cc_220_proc_dff_71533_Y;
    wire [0:0] w_ge_0_gc_0_leaf_core_auto_proc_dff_cc_220_proc_dff_71538_Y;
    wire [0:0] w_ge_0_gc_0_leaf_core_auto_proc_dff_cc_220_proc_dff_71543_Y;
    wire [0:0] w_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y;
    wire [0:0] w_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_167_55670_Y;
    wire [0:0] w_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y;
    wire [0:0] w_ge_0_gc_0_leaf_core_logic_not_ot_hbm_idx_chunk_rt_h_sv_154_55666_Y;
    wire [31:0] w_ge_0_gc_0_leaf_core_procdff_71508_Q;
    wire [0:0] w_ge_0_gc_0_leaf_core_procdff_71509_Q;
    wire [31:0] w_ge_0_gc_0_leaf_core_procdff_71510_Q;
    wire [0:0] w_ge_0_gc_0_leaf_core_procdff_71511_Q;
    wire [31:0] w_ge_0_gc_0_leaf_core_procdff_71512_Q;
    wire [0:0] w_ge_0_gc_0_leaf_core_procdff_71513_Q;
    wire [31:0] w_ge_0_gc_0_leaf_core_procdff_71514_Q;
    wire [0:0] w_ge_0_gc_0_leaf_core_procdff_71515_Q;
    wire [0:0] w_ge_0_gc_0_leaf_core_procdff_71516_Q;
    wire [3:0] w_ge_0_gc_0_leaf_core_procdff_71517_Q;
    wire [31:0] w_ge_0_gc_0_leaf_core_procdff_71518_Q;
    wire [567:0] w_ge_0_gc_0_leaf_core_procdff_71519_Q;
    wire [0:0] w_ge_0_gc_0_leaf_core_procdff_71520_Q;
    wire [7:0] w_ge_0_gc_0_leaf_core_procdff_71521_Q;
    wire [0:0] w_ge_0_gc_0_leaf_core_procdff_71522_Q;
    wire [3:0] w_ge_0_gc_0_leaf_core_procdff_71523_Q;
    wire [2175:0] w_ge_0_gc_0_leaf_core_procdff_71524_Q;
    wire [7:0] w_ge_0_gc_0_leaf_core_procdff_71525_Q;
    wire [7:0] w_ge_0_gc_0_leaf_core_procdff_71526_Q;
    wire [7:0] w_ge_0_gc_0_leaf_core_procdff_71527_Q;
    wire [7:0] w_ge_0_gc_0_leaf_core_procdff_71528_Q;
    wire [7:0] w_ge_0_gc_0_leaf_core_procdff_71529_Q;
    wire [7:0] w_ge_0_gc_0_leaf_core_procdff_71530_Q;
    wire [7:0] w_ge_0_gc_0_leaf_core_procdff_71531_Q;
    wire [7:0] w_ge_0_gc_0_leaf_core_procdff_71532_Q;
    wire [0:0] w_ge_0_gc_0_leaf_core_procdff_71537_Q;
    wire [15:0] w_ge_0_gc_0_leaf_core_procdff_71542_Q;
    wire [15:0] w_ge_0_gc_0_leaf_core_procdff_71547_Q;
    wire [0:0] w_ge_0_gc_0_leaf_core_reduce_and_ot_hbm_idx_chunk_rt_h_sv_155_55667_Y;
    wire [0:0] w_u_hb_idx_s_Q_r0c0_k0h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r0c0_k0h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r0c0_k0h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r0c0_k0h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r0c0_k0h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r0c0_k0h1_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r0c0_k1h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r0c0_k1h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r0c0_k1h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r0c0_k1h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r0c0_k1h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r0c0_k1h1_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r0c0_k2h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r0c0_k2h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r0c0_k2h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r0c0_k2h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r0c0_k2h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r0c0_k2h1_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r0c0_k3h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r0c0_k3h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r0c0_k3h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r0c0_k3h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r0c0_k3h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r0c0_k3h1_prdy;
    wire [4:0] w_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n;
    wire [568:0] w_ge_0_gc_0_leaf_core_u_qlate_q;
    wire [4:0] w_ge_0_gc_0_leaf_core_u_vl_q;
    wire [0:0] w_ge_0_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54724_Y;
    wire [0:0] w_ge_0_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54726_Y;
    wire [0:0] w_ge_0_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54728_Y;
    wire [0:0] w_ge_0_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54730_Y;
    wire [31:0] w_ge_0_gc_1_leaf_procdff_71548_Q;
    wire [551:0] w_ge_0_gc_1_leaf_procdff_71549_Q;
    wire [551:0] w_ge_0_gc_1_leaf_procdff_71550_Q;
    wire [0:0] w_ge_0_gc_1_leaf_procdff_71551_Q;
    wire [567:0] w_ge_0_gc_1_leaf_procdff_71552_Q;
    wire [0:0] w_ge_0_gc_1_leaf_procdff_71553_Q;
    wire [3:0] w_ge_0_gc_1_leaf_procdff_71554_Q;
    wire [2175:0] w_ge_0_gc_1_leaf_procdff_71555_Q;
    wire [29:0] w_ge_0_gc_1_leaf_procdff_71556_Q;
    wire [0:0] w_ge_0_gc_1_leaf_procdff_71557_Q;
    wire [567:0] w_ge_0_gc_1_leaf_procdff_71558_Q;
    wire [0:0] w_ge_0_gc_1_leaf_procdff_71559_Q;
    wire [3:0] w_ge_0_gc_1_leaf_procdff_71560_Q;
    wire [2175:0] w_ge_0_gc_1_leaf_procdff_71561_Q;
    wire [29:0] w_ge_0_gc_1_leaf_procdff_71562_Q;
    wire [7:0] w_ge_0_gc_1_leaf_procdff_71563_Q;
    wire [137:0] w_ge_0_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54725_Y;
    wire [137:0] w_ge_0_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54727_Y;
    wire [137:0] w_ge_0_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54729_Y;
    wire [137:0] w_ge_0_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54731_Y;
    wire [7:0] w_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55671_Y;
    wire [7:0] w_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55672_Y;
    wire [7:0] w_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55673_Y;
    wire [7:0] w_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55674_Y;
    wire [7:0] w_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55675_Y;
    wire [7:0] w_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55676_Y;
    wire [7:0] w_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55677_Y;
    wire [7:0] w_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55678_Y;
    wire [0:0] w_ge_0_gc_1_leaf_core_auto_proc_dff_cc_220_proc_dff_71533_Y;
    wire [0:0] w_ge_0_gc_1_leaf_core_auto_proc_dff_cc_220_proc_dff_71538_Y;
    wire [0:0] w_ge_0_gc_1_leaf_core_auto_proc_dff_cc_220_proc_dff_71543_Y;
    wire [0:0] w_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y;
    wire [0:0] w_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_167_55670_Y;
    wire [0:0] w_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y;
    wire [0:0] w_ge_0_gc_1_leaf_core_logic_not_ot_hbm_idx_chunk_rt_h_sv_154_55666_Y;
    wire [31:0] w_ge_0_gc_1_leaf_core_procdff_71508_Q;
    wire [0:0] w_ge_0_gc_1_leaf_core_procdff_71509_Q;
    wire [31:0] w_ge_0_gc_1_leaf_core_procdff_71510_Q;
    wire [0:0] w_ge_0_gc_1_leaf_core_procdff_71511_Q;
    wire [31:0] w_ge_0_gc_1_leaf_core_procdff_71512_Q;
    wire [0:0] w_ge_0_gc_1_leaf_core_procdff_71513_Q;
    wire [31:0] w_ge_0_gc_1_leaf_core_procdff_71514_Q;
    wire [0:0] w_ge_0_gc_1_leaf_core_procdff_71515_Q;
    wire [0:0] w_ge_0_gc_1_leaf_core_procdff_71516_Q;
    wire [3:0] w_ge_0_gc_1_leaf_core_procdff_71517_Q;
    wire [31:0] w_ge_0_gc_1_leaf_core_procdff_71518_Q;
    wire [567:0] w_ge_0_gc_1_leaf_core_procdff_71519_Q;
    wire [0:0] w_ge_0_gc_1_leaf_core_procdff_71520_Q;
    wire [7:0] w_ge_0_gc_1_leaf_core_procdff_71521_Q;
    wire [0:0] w_ge_0_gc_1_leaf_core_procdff_71522_Q;
    wire [3:0] w_ge_0_gc_1_leaf_core_procdff_71523_Q;
    wire [2175:0] w_ge_0_gc_1_leaf_core_procdff_71524_Q;
    wire [7:0] w_ge_0_gc_1_leaf_core_procdff_71525_Q;
    wire [7:0] w_ge_0_gc_1_leaf_core_procdff_71526_Q;
    wire [7:0] w_ge_0_gc_1_leaf_core_procdff_71527_Q;
    wire [7:0] w_ge_0_gc_1_leaf_core_procdff_71528_Q;
    wire [7:0] w_ge_0_gc_1_leaf_core_procdff_71529_Q;
    wire [7:0] w_ge_0_gc_1_leaf_core_procdff_71530_Q;
    wire [7:0] w_ge_0_gc_1_leaf_core_procdff_71531_Q;
    wire [7:0] w_ge_0_gc_1_leaf_core_procdff_71532_Q;
    wire [0:0] w_ge_0_gc_1_leaf_core_procdff_71537_Q;
    wire [15:0] w_ge_0_gc_1_leaf_core_procdff_71542_Q;
    wire [15:0] w_ge_0_gc_1_leaf_core_procdff_71547_Q;
    wire [0:0] w_ge_0_gc_1_leaf_core_reduce_and_ot_hbm_idx_chunk_rt_h_sv_155_55667_Y;
    wire [0:0] w_u_hb_idx_s_Q_r0c1_k0h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r0c1_k0h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r0c1_k0h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r0c1_k0h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r0c1_k0h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r0c1_k0h1_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r0c1_k1h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r0c1_k1h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r0c1_k1h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r0c1_k1h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r0c1_k1h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r0c1_k1h1_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r0c1_k2h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r0c1_k2h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r0c1_k2h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r0c1_k2h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r0c1_k2h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r0c1_k2h1_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r0c1_k3h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r0c1_k3h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r0c1_k3h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q_r0c1_k3h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q_r0c1_k3h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q_r0c1_k3h1_prdy;
    wire [4:0] w_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n;
    wire [568:0] w_ge_0_gc_1_leaf_core_u_qlate_q;
    wire [4:0] w_ge_0_gc_1_leaf_core_u_vl_q;
    wire [22:0] L100r0_1_o_s0;
    wire [22:0] L100r0_1_o_s1;
    wire [22:0] L100r0_1_o_s2;
    wire [22:0] L100r0_1_o_s3;
    wire [11:0] L117x5_o_s0;
    wire [11:0] L117x5_o_s1;
    wire [9:0] L123r0_1_o_s0;
    wire [9:0] L123r0_1_o_s1;
    wire [9:0] L123r0_1_o_s2;
    wire [9:0] L123r0_1_o_s3;
    wire [2:0] L138x5_o_s0;
    wire [2:0] L138x5_o_s1;
    wire [7:0] L48x8_o_s0;
    wire [7:0] L48x8_o_s1;
    wire [7:0] L48x8_o_s2;
    wire [268:0] L70r0_1_o_s0;
    wire [268:0] L70r0_1_o_s1;
    wire [268:0] L70r0_1_o_s2;
    wire [268:0] L70r0_1_o_s3;
    wire [37:0] L721x1_o_s0;
    wire [37:0] L721x1_o_s1;
    wire [37:0] L721x1_o_s2;
    wire [37:0] L721x1_o_s3;
     
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
    wire rst_rl_0;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));   
    wire rst_rl_1;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));   
    wire rst_rl_2;
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));   
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_n_t0));   
    wire rst_rl_4;
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_root_n), .q(rst_rl_4));   
    wire rst_rl_5;
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_rl_4), .q(rst_rl_5));   
    wire rst_rl_6;
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_rl_5), .q(rst_rl_6));   
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_rl_6), .q(rst_n_t1));   
    wire rst_rl_8;
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_root_n), .q(rst_rl_8));   
    wire rst_rl_9;
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_rl_8), .q(rst_rl_9));   
    wire rst_rl_10;
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_9), .q(rst_rl_10));   
    ot_dp_rrelay u_rrl_11 (.clk(clk), .d(rst_rl_10), .q(rst_n_t2));   
    wire rst_rl_12;
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_root_n), .q(rst_rl_12));   
    wire rst_rl_13;
    ot_dp_rrelay u_rrl_13 (.clk(clk), .d(rst_rl_12), .q(rst_rl_13));   
    wire rst_rl_14;
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_13), .q(rst_rl_14));   
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_14), .q(rst_n_t3));   
    wire rst_rl_16;
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_root_n), .q(rst_rl_16));   
    wire rst_rl_17;
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_16), .q(rst_rl_17));   
    wire rst_rl_18;
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_rl_17), .q(rst_rl_18));   
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_18), .q(rst_n_t4));   
    wire rst_rl_20;
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_root_n), .q(rst_rl_20));   
    wire rst_rl_21;
    ot_dp_rrelay u_rrl_21 (.clk(clk), .d(rst_rl_20), .q(rst_rl_21));   
    wire rst_rl_22;
    ot_dp_rrelay u_rrl_22 (.clk(clk), .d(rst_rl_21), .q(rst_rl_22));   
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_22), .q(rst_n_t5));   
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_22), .q(rst_n_t7));   
    wire rst_rl_25;
    ot_dp_rrelay u_rrl_25 (.clk(clk), .d(rst_rl_20), .q(rst_rl_25));   
    wire rst_rl_26;
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_rl_25), .q(rst_rl_26));   
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_26), .q(rst_n_t6));   
    wire rst_rl_28;
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_root_n), .q(rst_rl_28));   
    wire rst_rl_29;
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_rl_28), .q(rst_rl_29));   
    wire rst_rl_30;
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_rl_29), .q(rst_rl_30));   
    ot_dp_rrelay u_rrl_31 (.clk(clk), .d(rst_rl_30), .q(rst_o_0));   
    ot_dp_rrelay u_rrl_31_t (.clk(clk), .d(rst_rl_30), .q(rst_n_t8));   
    wire rst_n = rst_n_t2;
    ot_dp_st #(.W(178)) u_bin_L203m_i (.clk(clk), .rst_n(rst_n), .d(L203m_i[177:0]), .ea(L203m_i[178]), .q(L203m_i_q), .eq(L203m_i_eq));
    ot_dp_st #(.W(828)) u_bin_L6_i (.clk(clk), .rst_n(rst_n), .d(L6_i[827:0]), .ea(L6_i[828]), .q(L6_i_b), .eq(L6_i_eb));
    ot_dp_dly #(.W(829), .D(6)) u_lpad_L6_i (.clk(clk), .d({L6_i_eb, L6_i_b}), .q({L6_i_eq, L6_i_q}));   
    ot_dp_st #(.W(828)) u_bin_L6b_i (.clk(clk), .rst_n(rst_n), .d(L6b_i[827:0]), .ea(L6b_i[828]), .q(L6b_i_q), .eq(L6b_i_eq));
    ot_dp_st #(.W(828)) u_bin_L6c_i (.clk(clk), .rst_n(rst_n), .d(L6c_i[827:0]), .ea(L6c_i[828]), .q(L6c_i_b), .eq(L6c_i_eb));
    ot_dp_dly #(.W(829), .D(4)) u_lpad_L6c_i (.clk(clk), .d({L6c_i_eb, L6c_i_b}), .q({L6c_i_eq, L6c_i_q}));   
    ot_dp_st #(.W(2484)) u_bin_L7_i (.clk(clk), .rst_n(rst_n), .d(L7_i[2483:0]), .ea(L7_i[2484]), .q(L7_i_q), .eq(L7_i_eq));
    ot_dp_st #(.W(20)) u_bin_L91_i (.clk(clk), .rst_n(rst_n), .d(L91_i[19:0]), .ea(L91_i[20]), .q(L91_i_q), .eq(L91_i_eq));
    ot_dp_st #(.W(3332)) u_bout_L401m_o (.clk(clk), .rst_n(rst_n), .d({w_ge_0_gc_1_leaf_procdff_71556_Q[29:0], w_ge_0_gc_1_leaf_procdff_71555_Q[2175:0], w_ge_0_gc_1_leaf_procdff_71554_Q[3:0], w_ge_0_gc_1_leaf_procdff_71553_Q[0], w_ge_0_gc_1_leaf_procdff_71552_Q[567:0], w_ge_0_gc_1_leaf_procdff_71551_Q[0], w_ge_0_gc_1_leaf_procdff_71549_Q[551:0]}), .ea(rst_n), .q(L401m_o[3331:0]), .eq(L401m_o[3332]));
    ot_dp_st #(.W(20)) u_bout_xo_add_ot_hbm_idx_score_quarter_static_h_sv_91_54986_Y (.clk(clk), .rst_n(rst_n), .d(w_add_ot_hbm_idx_score_quarter_static_h_sv_91_54986_Y[19:0]), .ea(rst_n), .q(xo_add_ot_hbm_idx_score_quarter_static_h_sv_91_54986_Y[19:0]), .eq(xo_add_ot_hbm_idx_score_quarter_static_h_sv_91_54986_Y[20]));
    ot_dp_st #(.W(1)) u_bout_xo_ge_ot_hbm_idx_score_quarter_static_h_sv_92_54989_Y (.clk(clk), .rst_n(rst_n), .d(w_ge_ot_hbm_idx_score_quarter_static_h_sv_92_54989_Y[0]), .ea(rst_n), .q(xo_ge_ot_hbm_idx_score_quarter_static_h_sv_92_54989_Y[0:0]), .eq(xo_ge_ot_hbm_idx_score_quarter_static_h_sv_92_54989_Y[1]));
    ot_dp_st #(.W(1)) u_bout_xo_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54959_Y (.clk(clk), .rst_n(rst_n), .d(w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54959_Y[0]), .ea(rst_n), .q(xo_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54959_Y[0:0]), .eq(xo_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54959_Y[1]));
    ot_dp_st #(.W(1)) u_bout_xo_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54967_Y (.clk(clk), .rst_n(rst_n), .d(w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54967_Y[0]), .ea(rst_n), .q(xo_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54967_Y[0:0]), .eq(xo_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54967_Y[1]));
    ot_dp_st #(.W(1)) u_bout_xo_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54975_Y (.clk(clk), .rst_n(rst_n), .d(w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54975_Y[0]), .ea(rst_n), .q(xo_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54975_Y[0:0]), .eq(xo_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54975_Y[1]));
    ot_dp_st #(.W(1)) u_bout_xo_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54983_Y (.clk(clk), .rst_n(rst_n), .d(w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54983_Y[0]), .ea(rst_n), .q(xo_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54983_Y[0:0]), .eq(xo_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54983_Y[1]));
    ot_dp_st #(.W(1)) u_bout_xo_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54956_Y (.clk(clk), .rst_n(rst_n), .d(w_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54956_Y[0]), .ea(rst_n), .q(xo_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54956_Y[0:0]), .eq(xo_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54956_Y[1]));
    ot_dp_st #(.W(1)) u_bout_xo_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54964_Y (.clk(clk), .rst_n(rst_n), .d(w_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54964_Y[0]), .ea(rst_n), .q(xo_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54964_Y[0:0]), .eq(xo_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54964_Y[1]));
    ot_dp_st #(.W(1)) u_bout_xo_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54972_Y (.clk(clk), .rst_n(rst_n), .d(w_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54972_Y[0]), .ea(rst_n), .q(xo_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54972_Y[0:0]), .eq(xo_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54972_Y[1]));
    ot_dp_st #(.W(1)) u_bout_xo_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54980_Y (.clk(clk), .rst_n(rst_n), .d(w_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54980_Y[0]), .ea(rst_n), .q(xo_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54980_Y[0:0]), .eq(xo_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54980_Y[1]));
    ot_dp_st #(.W(1)) u_bout_xo_procdff_71763_Q (.clk(clk), .rst_n(rst_n), .d(w_procdff_71763_Q[0]), .ea(rst_n), .q(xo_procdff_71763_Q[0:0]), .eq(xo_procdff_71763_Q[1]));
    ot_dp_st #(.W(8)) u_bout_xo_procdff_71764_Q (.clk(clk), .rst_n(rst_n), .d(w_procdff_71764_Q[7:0]), .ea(rst_n), .q(xo_procdff_71764_Q[7:0]), .eq(xo_procdff_71764_Q[8]));
    ot_dp_st #(.W(512)) u_bout_xo_procdff_71765_Q (.clk(clk), .rst_n(rst_n), .d(w_procdff_71765_Q[511:0]), .ea(rst_n), .q(xo_procdff_71765_Q[511:0]), .eq(xo_procdff_71765_Q[512]));
    ot_dp_st #(.W(32)) u_bout_xo_procdff_71766_Q (.clk(clk), .rst_n(rst_n), .d(w_procdff_71766_Q[31:0]), .ea(rst_n), .q(xo_procdff_71766_Q[31:0]), .eq(xo_procdff_71766_Q[32]));
    ot_dp_st #(.W(16)) u_bout_xo_procdff_71767_Q (.clk(clk), .rst_n(rst_n), .d(w_procdff_71767_Q[15:0]), .ea(rst_n), .q(xo_procdff_71767_Q[15:0]), .eq(xo_procdff_71767_Q[16]));
    ot_dp_st #(.W(1)) u_bout_xo_procdff_71768_Q (.clk(clk), .rst_n(rst_n), .d(w_procdff_71768_Q[0]), .ea(rst_n), .q(xo_procdff_71768_Q[0:0]), .eq(xo_procdff_71768_Q[1]));
    ot_dp_st #(.W(2176)) u_bout_xo_procdff_71770_Q (.clk(clk), .rst_n(rst_n), .d({w_procdff_71770_Q[4395:3308], w_procdff_71770_Q[3296:2209]}), .ea(rst_n), .q(xo_procdff_71770_Q[2175:0]), .eq(xo_procdff_71770_Q[2176]));
    ot_dp_st #(.W(1)) u_bout_xo_procmux_66659_Y (.clk(clk), .rst_n(rst_n), .d(w_procmux_66659_Y[0]), .ea(rst_n), .q(xo_procmux_66659_Y[0:0]), .eq(xo_procmux_66659_Y[1]));
    ot_dp_st #(.W(22)) u_ft_L100r0_1_o_0 (.clk(clk), .rst_n(rst_n), .d(L100r0_1_i[21:0]), .ea(L100r0_1_i[22]), .q(L100r0_1_o_s0[21:0]), .eq(L100r0_1_o_s0[22]));
    ot_dp_st #(.W(22)) u_ft_L100r0_1_o_1 (.clk(clk), .rst_n(rst_n), .d(L100r0_1_o_s0[21:0]), .ea(L100r0_1_o_s0[22]), .q(L100r0_1_o_s1[21:0]), .eq(L100r0_1_o_s1[22]));
    ot_dp_st #(.W(22)) u_ft_L100r0_1_o_2 (.clk(clk), .rst_n(rst_n), .d(L100r0_1_o_s1[21:0]), .ea(L100r0_1_o_s1[22]), .q(L100r0_1_o_s2[21:0]), .eq(L100r0_1_o_s2[22]));
    ot_dp_st #(.W(22)) u_ft_L100r0_1_o_3 (.clk(clk), .rst_n(rst_n), .d(L100r0_1_o_s2[21:0]), .ea(L100r0_1_o_s2[22]), .q(L100r0_1_o_s3[21:0]), .eq(L100r0_1_o_s3[22]));
    ot_dp_st #(.W(22)) u_ft_L100r0_1_o_4 (.clk(clk), .rst_n(rst_n), .d(L100r0_1_o_s3[21:0]), .ea(L100r0_1_o_s3[22]), .q(L100r0_1_o[21:0]), .eq(L100r0_1_o[22]));
    ot_dp_st #(.W(11)) u_ft_L117x5_o_0 (.clk(clk), .rst_n(rst_n), .d(L117x5_i[10:0]), .ea(L117x5_i[11]), .q(L117x5_o_s0[10:0]), .eq(L117x5_o_s0[11]));
    ot_dp_st #(.W(11)) u_ft_L117x5_o_1 (.clk(clk), .rst_n(rst_n), .d(L117x5_o_s0[10:0]), .ea(L117x5_o_s0[11]), .q(L117x5_o_s1[10:0]), .eq(L117x5_o_s1[11]));
    ot_dp_st #(.W(11)) u_ft_L117x5_o_2 (.clk(clk), .rst_n(rst_n), .d(L117x5_o_s1[10:0]), .ea(L117x5_o_s1[11]), .q(L117x5_o[10:0]), .eq(L117x5_o[11]));
    ot_dp_st #(.W(9)) u_ft_L123r0_1_o_0 (.clk(clk), .rst_n(rst_n), .d(L123r0_1_i[8:0]), .ea(L123r0_1_i[9]), .q(L123r0_1_o_s0[8:0]), .eq(L123r0_1_o_s0[9]));
    ot_dp_st #(.W(9)) u_ft_L123r0_1_o_1 (.clk(clk), .rst_n(rst_n), .d(L123r0_1_o_s0[8:0]), .ea(L123r0_1_o_s0[9]), .q(L123r0_1_o_s1[8:0]), .eq(L123r0_1_o_s1[9]));
    ot_dp_st #(.W(9)) u_ft_L123r0_1_o_2 (.clk(clk), .rst_n(rst_n), .d(L123r0_1_o_s1[8:0]), .ea(L123r0_1_o_s1[9]), .q(L123r0_1_o_s2[8:0]), .eq(L123r0_1_o_s2[9]));
    ot_dp_st #(.W(9)) u_ft_L123r0_1_o_3 (.clk(clk), .rst_n(rst_n), .d(L123r0_1_o_s2[8:0]), .ea(L123r0_1_o_s2[9]), .q(L123r0_1_o_s3[8:0]), .eq(L123r0_1_o_s3[9]));
    ot_dp_st #(.W(9)) u_ft_L123r0_1_o_4 (.clk(clk), .rst_n(rst_n), .d(L123r0_1_o_s3[8:0]), .ea(L123r0_1_o_s3[9]), .q(L123r0_1_o[8:0]), .eq(L123r0_1_o[9]));
    ot_dp_st #(.W(2)) u_ft_L138x5_o_0 (.clk(clk), .rst_n(rst_n), .d(L138x5_i[1:0]), .ea(L138x5_i[2]), .q(L138x5_o_s0[1:0]), .eq(L138x5_o_s0[2]));
    ot_dp_st #(.W(2)) u_ft_L138x5_o_1 (.clk(clk), .rst_n(rst_n), .d(L138x5_o_s0[1:0]), .ea(L138x5_o_s0[2]), .q(L138x5_o_s1[1:0]), .eq(L138x5_o_s1[2]));
    ot_dp_st #(.W(2)) u_ft_L138x5_o_2 (.clk(clk), .rst_n(rst_n), .d(L138x5_o_s1[1:0]), .ea(L138x5_o_s1[2]), .q(L138x5_o[1:0]), .eq(L138x5_o[2]));
    ot_dp_st #(.W(7)) u_ft_L48x8_o_0 (.clk(clk), .rst_n(rst_n), .d(L48x8_i[6:0]), .ea(L48x8_i[7]), .q(L48x8_o_s0[6:0]), .eq(L48x8_o_s0[7]));
    ot_dp_st #(.W(7)) u_ft_L48x8_o_1 (.clk(clk), .rst_n(rst_n), .d(L48x8_o_s0[6:0]), .ea(L48x8_o_s0[7]), .q(L48x8_o_s1[6:0]), .eq(L48x8_o_s1[7]));
    ot_dp_st #(.W(7)) u_ft_L48x8_o_2 (.clk(clk), .rst_n(rst_n), .d(L48x8_o_s1[6:0]), .ea(L48x8_o_s1[7]), .q(L48x8_o_s2[6:0]), .eq(L48x8_o_s2[7]));
    ot_dp_st #(.W(7)) u_ft_L48x8_o_3 (.clk(clk), .rst_n(rst_n), .d(L48x8_o_s2[6:0]), .ea(L48x8_o_s2[7]), .q(L48x8_o[6:0]), .eq(L48x8_o[7]));
    ot_dp_st #(.W(268)) u_ft_L70r0_1_o_0 (.clk(clk), .rst_n(rst_n), .d(L70r0_1_i[267:0]), .ea(L70r0_1_i[268]), .q(L70r0_1_o_s0[267:0]), .eq(L70r0_1_o_s0[268]));
    ot_dp_st #(.W(268)) u_ft_L70r0_1_o_1 (.clk(clk), .rst_n(rst_n), .d(L70r0_1_o_s0[267:0]), .ea(L70r0_1_o_s0[268]), .q(L70r0_1_o_s1[267:0]), .eq(L70r0_1_o_s1[268]));
    ot_dp_st #(.W(268)) u_ft_L70r0_1_o_2 (.clk(clk), .rst_n(rst_n), .d(L70r0_1_o_s1[267:0]), .ea(L70r0_1_o_s1[268]), .q(L70r0_1_o_s2[267:0]), .eq(L70r0_1_o_s2[268]));
    ot_dp_st #(.W(268)) u_ft_L70r0_1_o_3 (.clk(clk), .rst_n(rst_n), .d(L70r0_1_o_s2[267:0]), .ea(L70r0_1_o_s2[268]), .q(L70r0_1_o_s3[267:0]), .eq(L70r0_1_o_s3[268]));
    ot_dp_st #(.W(268)) u_ft_L70r0_1_o_4 (.clk(clk), .rst_n(rst_n), .d(L70r0_1_o_s3[267:0]), .ea(L70r0_1_o_s3[268]), .q(L70r0_1_o[267:0]), .eq(L70r0_1_o[268]));
    ot_dp_st #(.W(37)) u_ft_L721x1_o_0 (.clk(clk), .rst_n(rst_n), .d(L721x1_i[36:0]), .ea(L721x1_i[37]), .q(L721x1_o_s0[36:0]), .eq(L721x1_o_s0[37]));
    ot_dp_st #(.W(37)) u_ft_L721x1_o_1 (.clk(clk), .rst_n(rst_n), .d(L721x1_o_s0[36:0]), .ea(L721x1_o_s0[37]), .q(L721x1_o_s1[36:0]), .eq(L721x1_o_s1[37]));
    ot_dp_st #(.W(37)) u_ft_L721x1_o_2 (.clk(clk), .rst_n(rst_n), .d(L721x1_o_s1[36:0]), .ea(L721x1_o_s1[37]), .q(L721x1_o_s2[36:0]), .eq(L721x1_o_s2[37]));
    ot_dp_st #(.W(37)) u_ft_L721x1_o_3 (.clk(clk), .rst_n(rst_n), .d(L721x1_o_s2[36:0]), .ea(L721x1_o_s2[37]), .q(L721x1_o_s3[36:0]), .eq(L721x1_o_s3[37]));
    ot_dp_st #(.W(37)) u_ft_L721x1_o_4 (.clk(clk), .rst_n(rst_n), .d(L721x1_o_s3[36:0]), .ea(L721x1_o_s3[37]), .q(L721x1_o[36:0]), .eq(L721x1_o[37]));
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_71_54855_Y = w_mul_ot_hbm_idx_score_quarter_static_h_sv_71_54853_Y[19:0] + w_mul_ot_hbm_idx_score_quarter_static_h_sv_71_54854_Y[19:0];   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_71_54857_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_71_54855_Y[19:0] + w_mul_ot_hbm_idx_score_quarter_static_h_sv_71_54856_Y[19:0];   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_77_54866_Y = w_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54865_Y[31:0] + {32{1'b0}};   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_77_54868_Y = w_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54867_Y[31:0] + {{24{1'b0}}, w_procdff_71769_Q[7:0]};   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_77_54873_Y = w_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54872_Y[31:0] + 32'b00000000000000000000000000000001;   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_77_54875_Y = w_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54874_Y[31:0] + {{24{1'b0}}, w_procdff_71769_Q[7:0]};   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_77_54880_Y = w_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54879_Y[31:0] + 32'b00000000000000000000000000000010;   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_77_54882_Y = w_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54881_Y[31:0] + {{24{1'b0}}, w_procdff_71769_Q[7:0]};   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_77_54887_Y = w_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54886_Y[31:0] + 32'b00000000000000000000000000000011;   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_77_54889_Y = w_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54888_Y[31:0] + {{24{1'b0}}, w_procdff_71769_Q[7:0]};   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54897_Y = w_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54896_Y[11:0] + {12{1'b0}};   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54899_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54897_Y[11:0] + w_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54898_Y[11:0];   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54905_Y = w_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54904_Y[11:0] + 12'b000000000001;   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54907_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54905_Y[11:0] + w_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54906_Y[11:0];   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54913_Y = w_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54912_Y[11:0] + 12'b000000000010;   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54915_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54913_Y[11:0] + w_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54914_Y[11:0];   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54921_Y = w_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54920_Y[11:0] + 12'b000000000011;   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54923_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54921_Y[11:0] + w_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54922_Y[11:0];   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54953_Y = w_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54952_Y[11:0] + 12'b000000000100;   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54955_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54953_Y[11:0] + w_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54954_Y[11:0];   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54961_Y = w_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54960_Y[11:0] + 12'b000000000101;   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54963_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54961_Y[11:0] + w_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54962_Y[11:0];   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54969_Y = w_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54968_Y[11:0] + 12'b000000000110;   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54971_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54969_Y[11:0] + w_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54970_Y[11:0];   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54977_Y = w_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54976_Y[11:0] + 12'b000000000111;   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54979_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54977_Y[11:0] + w_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54978_Y[11:0];   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_91_54929_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_71_54857_Y[19:0] + w_ternary_ot_hbm_idx_score_quarter_static_h_sv_91_54928_Y[19:0];   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_91_54930_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_91_54929_Y[19:0] + {20{1'b0}};   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_91_54985_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_71_54857_Y[19:0] + w_ternary_ot_hbm_idx_score_quarter_static_h_sv_91_54984_Y[19:0];   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_91_54986_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_91_54985_Y[19:0] + 20'b00000000000000000100;   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_92_54931_Y = {{4{1'b0}}, w_procdff_71769_Q[7:0]} + 12'b000000000001;   
    assign w_add_ot_hbm_idx_score_quarter_static_h_sv_92_54987_Y = {{4{1'b0}}, w_procdff_71769_Q[7:0]} + 12'b000000000001;   
    assign w_auto_proc_dff_cc_220_proc_dff_71688_Y = ~rst_n;
    assign w_auto_proc_dff_cc_220_proc_dff_71693_Y = ~rst_n;
    assign w_auto_proc_dff_cc_220_proc_dff_71698_Y = ~rst_n;
    assign w_auto_proc_dff_cc_220_proc_dff_71703_Y = ~rst_n;
    assign w_auto_proc_dff_cc_220_proc_dff_71708_Y = ~rst_n;
    assign w_auto_proc_dff_cc_220_proc_dff_71713_Y = ~rst_n;
    assign w_auto_proc_dff_cc_220_proc_dff_71721_Y = ~rst_n;
    assign w_auto_proc_dff_cc_220_proc_dff_71726_Y = ~rst_n;
    assign w_auto_proc_dff_cc_220_proc_dff_71731_Y = ~rst_n;
    assign w_auto_proc_dff_cc_220_proc_dff_71736_Y = ~rst_n;
    assign w_auto_proc_dff_cc_220_proc_dff_71741_Y = ~rst_n;
    assign w_auto_proc_dff_cc_220_proc_dff_71746_Y = ~rst_n;
    assign w_auto_proc_dff_cc_220_proc_dff_71752_Y = ~rst_n;
    assign w_ge_ot_hbm_idx_score_quarter_static_h_sv_92_54933_Y = w_mul_ot_hbm_idx_score_quarter_static_h_sv_92_54932_Y[11:0] >= w_procdff_71760_Q[11:0];   
    assign w_ge_ot_hbm_idx_score_quarter_static_h_sv_92_54989_Y = w_mul_ot_hbm_idx_score_quarter_static_h_sv_92_54988_Y[11:0] >= w_procdff_71760_Q[11:0];   
    assign w_gt_ot_hbm_idx_score_quarter_static_h_sv_76_54861_Y = w_procdff_71760_Q[11:0] > 32'b00000000000000000000101010110000;   
    assign w_gt_ot_hbm_idx_score_quarter_static_h_sv_76_54862_Y = w_procdff_71769_Q[7:0] > 32'b00000000000000000000000010101010;   
    assign w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_120_54935_Y = !rst_n;   
    assign w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_120_54991_Y = !rst_n;   
    assign w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_139_54945_Y = !rst_n;   
    assign w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_139_55001_Y = !rst_n;   
    assign w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_153_54893_Y = !rst_n;   
    assign w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_77_54864_Y = !w_procdff_71770_Q[0];   
    assign w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_77_54871_Y = !w_procdff_71770_Q[1099];   
    assign w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_77_54878_Y = !w_procdff_71770_Q[2198];   
    assign w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_77_54885_Y = !w_procdff_71770_Q[3297];   
    assign w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54901_Y = !w_procdff_71761_Q[0];   
    assign w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54909_Y = !w_procdff_71761_Q[0];   
    assign w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54917_Y = !w_procdff_71761_Q[0];   
    assign w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54925_Y = !w_procdff_71761_Q[0];   
    assign w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54957_Y = !w_procdff_71761_Q[0];   
    assign w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54965_Y = !w_procdff_71761_Q[0];   
    assign w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54973_Y = !w_procdff_71761_Q[0];   
    assign w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54981_Y = !w_procdff_71761_Q[0];   
    assign w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_76_54863_Y = w_gt_ot_hbm_idx_score_quarter_static_h_sv_76_54861_Y[0] || w_gt_ot_hbm_idx_score_quarter_static_h_sv_76_54862_Y[0];   
    assign w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_77_54870_Y = w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_77_54864_Y[0] || w_nex_ot_hbm_idx_score_quarter_static_h_sv_77_54869_Y[0];   
    assign w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_77_54877_Y = w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_77_54871_Y[0] || w_nex_ot_hbm_idx_score_quarter_static_h_sv_77_54876_Y[0];   
    assign w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_77_54884_Y = w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_77_54878_Y[0] || w_nex_ot_hbm_idx_score_quarter_static_h_sv_77_54883_Y[0];   
    assign w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_77_54891_Y = w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_77_54885_Y[0] || w_nex_ot_hbm_idx_score_quarter_static_h_sv_77_54890_Y[0];   
    assign w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54903_Y = w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54901_Y[0] || w_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54902_Y[0];   
    assign w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54911_Y = w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54909_Y[0] || w_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54910_Y[0];   
    assign w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54919_Y = w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54917_Y[0] || w_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54918_Y[0];   
    assign w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54927_Y = w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54925_Y[0] || w_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54926_Y[0];   
    assign w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54959_Y = w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54957_Y[0] || w_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54958_Y[0];   
    assign w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54967_Y = w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54965_Y[0] || w_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54966_Y[0];   
    assign w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54975_Y = w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54973_Y[0] || w_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54974_Y[0];   
    assign w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54983_Y = w_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54981_Y[0] || w_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54982_Y[0];   
    assign w_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54900_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54899_Y[11:0] < w_procdff_71760_Q[11:0];   
    assign w_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54908_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54907_Y[11:0] < w_procdff_71760_Q[11:0];   
    assign w_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54916_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54915_Y[11:0] < w_procdff_71760_Q[11:0];   
    assign w_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54924_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54923_Y[11:0] < w_procdff_71760_Q[11:0];   
    assign w_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54956_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54955_Y[11:0] < w_procdff_71760_Q[11:0];   
    assign w_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54964_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54963_Y[11:0] < w_procdff_71760_Q[11:0];   
    assign w_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54972_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54971_Y[11:0] < w_procdff_71760_Q[11:0];   
    assign w_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54980_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_87_54979_Y[11:0] < w_procdff_71760_Q[11:0];   
    assign w_mul_ot_hbm_idx_score_quarter_static_h_sv_71_54853_Y = 20'b00000000011000000000 * {{9{1'b0}}, w_procdff_71759_Q[10:0]};   
    assign w_mul_ot_hbm_idx_score_quarter_static_h_sv_71_54854_Y = 20'b00000000000000001000 * {{12{1'b0}}, w_procdff_71758_Q[7:0]};   
    assign w_mul_ot_hbm_idx_score_quarter_static_h_sv_71_54856_Y = 20'b00000000110000000000 * {{12{1'b0}}, w_procdff_71769_Q[7:0]};   
    assign w_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54865_Y = 32'b00000000000000000000000000000100 * {{31{1'b0}}, w_procdff_71757_Q[0]};   
    assign w_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54867_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_77_54866_Y[31:0] * 32'b00000000000000000000000010000000;   
    assign w_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54872_Y = 32'b00000000000000000000000000000100 * {{31{1'b0}}, w_procdff_71757_Q[0]};   
    assign w_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54874_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_77_54873_Y[31:0] * 32'b00000000000000000000000010000000;   
    assign w_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54879_Y = 32'b00000000000000000000000000000100 * {{31{1'b0}}, w_procdff_71757_Q[0]};   
    assign w_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54881_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_77_54880_Y[31:0] * 32'b00000000000000000000000010000000;   
    assign w_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54886_Y = 32'b00000000000000000000000000000100 * {{31{1'b0}}, w_procdff_71757_Q[0]};   
    assign w_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54888_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_77_54887_Y[31:0] * 32'b00000000000000000000000010000000;   
    assign w_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54896_Y = {{4{1'b0}}, w_procdff_71769_Q[7:0]} * 12'b000000010000;   
    assign w_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54904_Y = {{4{1'b0}}, w_procdff_71769_Q[7:0]} * 12'b000000010000;   
    assign w_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54912_Y = {{4{1'b0}}, w_procdff_71769_Q[7:0]} * 12'b000000010000;   
    assign w_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54920_Y = {{4{1'b0}}, w_procdff_71769_Q[7:0]} * 12'b000000010000;   
    assign w_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54952_Y = {{4{1'b0}}, w_procdff_71769_Q[7:0]} * 12'b000000010000;   
    assign w_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54960_Y = {{4{1'b0}}, w_procdff_71769_Q[7:0]} * 12'b000000010000;   
    assign w_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54968_Y = {{4{1'b0}}, w_procdff_71769_Q[7:0]} * 12'b000000010000;   
    assign w_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54976_Y = {{4{1'b0}}, w_procdff_71769_Q[7:0]} * 12'b000000010000;   
    assign w_mul_ot_hbm_idx_score_quarter_static_h_sv_92_54932_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_92_54931_Y[11:0] * 12'b000000010000;   
    assign w_mul_ot_hbm_idx_score_quarter_static_h_sv_92_54988_Y = w_add_ot_hbm_idx_score_quarter_static_h_sv_92_54987_Y[11:0] * 12'b000000010000;   
    assign w_nex_ot_hbm_idx_score_quarter_static_h_sv_77_54869_Y = w_procdff_71770_Q[10:1] !== w_add_ot_hbm_idx_score_quarter_static_h_sv_77_54868_Y[9:0];   
    assign w_nex_ot_hbm_idx_score_quarter_static_h_sv_77_54876_Y = w_procdff_71770_Q[1109:1100] !== w_add_ot_hbm_idx_score_quarter_static_h_sv_77_54875_Y[9:0];   
    assign w_nex_ot_hbm_idx_score_quarter_static_h_sv_77_54883_Y = w_procdff_71770_Q[2208:2199] !== w_add_ot_hbm_idx_score_quarter_static_h_sv_77_54882_Y[9:0];   
    assign w_nex_ot_hbm_idx_score_quarter_static_h_sv_77_54890_Y = w_procdff_71770_Q[3307:3298] !== w_add_ot_hbm_idx_score_quarter_static_h_sv_77_54889_Y[9:0];   
    reg [0:0] g_procdff_71757_q;
    assign w_procdff_71757_Q = g_procdff_71757_q;
    always @(posedge clk) g_procdff_71757_q <= 1'b1;   
    reg [7:0] g_procdff_71758_q;
    assign w_procdff_71758_Q = g_procdff_71758_q;
    always @(posedge clk) g_procdff_71758_q <= L203m_i_q[8:1];   
    reg [10:0] g_procdff_71759_q;
    assign w_procdff_71759_Q = g_procdff_71759_q;
    always @(posedge clk) g_procdff_71759_q <= 11'b00101010110;   
    reg [11:0] g_procdff_71760_q;
    assign w_procdff_71760_Q = g_procdff_71760_q;
    always @(posedge clk) g_procdff_71760_q <= L6b_i_q[589:578];   
    reg [0:0] g_procdff_71761_q;
    assign w_procdff_71761_Q = g_procdff_71761_q;
    always @(posedge clk) g_procdff_71761_q <= L203m_i_q[0];   
    reg [170:0] g_procdff_71762_q;
    assign w_procdff_71762_Q = g_procdff_71762_q;
    always @(posedge clk) g_procdff_71762_q <= {L91_i_q[19:18], L203m_i_q[177:9]};   
    reg [0:0] g_procdff_71763_q;
    assign w_procdff_71763_Q = g_procdff_71763_q;
    always @(posedge clk) g_procdff_71763_q <= L6b_i_q[552];   
    reg [7:0] g_procdff_71764_q;
    assign w_procdff_71764_Q = g_procdff_71764_q;
    always @(posedge clk) g_procdff_71764_q <= L6b_i_q[519:512];   
    reg [511:0] g_procdff_71765_q;
    assign w_procdff_71765_Q = g_procdff_71765_q;
    always @(posedge clk) g_procdff_71765_q <= L6b_i_q[511:0];   
    reg [31:0] g_procdff_71766_q;
    assign w_procdff_71766_Q = g_procdff_71766_q;
    always @(posedge clk) g_procdff_71766_q <= L6b_i_q[551:520];   
    reg [15:0] g_procdff_71767_q;
    assign w_procdff_71767_Q = g_procdff_71767_q;
    always @(posedge clk) g_procdff_71767_q <= L6b_i_q[568:553];   
    reg [0:0] g_procdff_71768_q;
    assign w_procdff_71768_Q = g_procdff_71768_q;
    always @(posedge clk) g_procdff_71768_q <= L6b_i_q[577];   
    reg [7:0] g_procdff_71769_q;
    assign w_procdff_71769_Q = g_procdff_71769_q;
    always @(posedge clk) g_procdff_71769_q <= L6b_i_q[576:569];   
    reg [4395:0] g_procdff_71770_q;
    assign w_procdff_71770_Q = g_procdff_71770_q;
    always @(posedge clk) g_procdff_71770_q <= {L91_i_q[17:0], L7_i_q[2483:0], L6_i_q[827:0], L6c_i_q[827:0], L6b_i_q[827:590]};   
    assign w_procmux_66627_Y = w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_77_54891_Y[0] ? 1'b1 : w_procmux_66635_Y[0];   
    assign w_procmux_66629_Y = w_procdff_71768_Q[0] ? w_procmux_66627_Y[0] : 1'bx;   
    assign w_procmux_66633_Y = w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_77_54884_Y[0] ? 1'b1 : w_procmux_66641_Y[0];   
    assign w_procmux_66635_Y = w_procdff_71768_Q[0] ? w_procmux_66633_Y[0] : 1'bx;   
    assign w_procmux_66639_Y = w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_77_54877_Y[0] ? 1'b1 : w_procmux_66647_Y[0];   
    assign w_procmux_66641_Y = w_procdff_71768_Q[0] ? w_procmux_66639_Y[0] : 1'bx;   
    assign w_procmux_66645_Y = w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_77_54870_Y[0] ? 1'b1 : w_procmux_66653_Y[0];   
    assign w_procmux_66647_Y = w_procdff_71768_Q[0] ? w_procmux_66645_Y[0] : 1'bx;   
    assign w_procmux_66651_Y = w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_76_54863_Y[0] ? 1'b1 : 1'b0;   
    assign w_procmux_66653_Y = w_procdff_71768_Q[0] ? w_procmux_66651_Y[0] : 1'bx;   
    assign w_procmux_66659_Y = w_procdff_71768_Q[0] ? w_procmux_66629_Y[0] : 1'b0;   
    ot_bind_native_129bb1e301d3931c53ca86a8 g_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54902 (.A(w_procdff_71762_Q[170:0]), .B(w_procdff_71769_Q[7:0]), .Y(w_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54902_Y));
    ot_bind_native_129bb1e301d3931c53ca86a8 g_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54910 (.A(w_procdff_71762_Q[170:0]), .B(w_procdff_71769_Q[7:0]), .Y(w_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54910_Y));
    ot_bind_native_129bb1e301d3931c53ca86a8 g_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54918 (.A(w_procdff_71762_Q[170:0]), .B(w_procdff_71769_Q[7:0]), .Y(w_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54918_Y));
    ot_bind_native_129bb1e301d3931c53ca86a8 g_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54926 (.A(w_procdff_71762_Q[170:0]), .B(w_procdff_71769_Q[7:0]), .Y(w_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54926_Y));
    ot_bind_native_129bb1e301d3931c53ca86a8 g_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54958 (.A(w_procdff_71762_Q[170:0]), .B(w_procdff_71769_Q[7:0]), .Y(w_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54958_Y));
    ot_bind_native_129bb1e301d3931c53ca86a8 g_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54966 (.A(w_procdff_71762_Q[170:0]), .B(w_procdff_71769_Q[7:0]), .Y(w_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54966_Y));
    ot_bind_native_129bb1e301d3931c53ca86a8 g_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54974 (.A(w_procdff_71762_Q[170:0]), .B(w_procdff_71769_Q[7:0]), .Y(w_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54974_Y));
    ot_bind_native_129bb1e301d3931c53ca86a8 g_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54982 (.A(w_procdff_71762_Q[170:0]), .B(w_procdff_71769_Q[7:0]), .Y(w_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54982_Y));
    assign w_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54898_Y = w_procdff_71757_Q[0] ? 12'b000000001000 : {12{1'b0}};   
    assign w_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54906_Y = w_procdff_71757_Q[0] ? 12'b000000001000 : {12{1'b0}};   
    assign w_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54914_Y = w_procdff_71757_Q[0] ? 12'b000000001000 : {12{1'b0}};   
    assign w_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54922_Y = w_procdff_71757_Q[0] ? 12'b000000001000 : {12{1'b0}};   
    assign w_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54954_Y = w_procdff_71757_Q[0] ? 12'b000000001000 : {12{1'b0}};   
    assign w_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54962_Y = w_procdff_71757_Q[0] ? 12'b000000001000 : {12{1'b0}};   
    assign w_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54970_Y = w_procdff_71757_Q[0] ? 12'b000000001000 : {12{1'b0}};   
    assign w_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54978_Y = w_procdff_71757_Q[0] ? 12'b000000001000 : {12{1'b0}};   
    assign w_ternary_ot_hbm_idx_score_quarter_static_h_sv_91_54928_Y = w_procdff_71757_Q[0] ? 20'b00000000011000000000 : {20{1'b0}};   
    assign w_ternary_ot_hbm_idx_score_quarter_static_h_sv_91_54984_Y = w_procdff_71757_Q[0] ? 20'b00000000011000000000 : {20{1'b0}};   
     
    ot_rst_delivered3 #(.REGIONS(1)) u_g_delivered_reset_u_rr (
        .clk(clk),
        .rst_n(w_g_delivered_reset_u_rr_rst_n),
        .rst_n_in(rst_n)
    );
    assign w_ge_0_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54724_Y = !w_ge_0_gc_0_leaf_procdff_71563_Q[4:3];   
    assign w_ge_0_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54726_Y = 2'b01 == w_ge_0_gc_0_leaf_procdff_71563_Q[4:3];   
    assign w_ge_0_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54728_Y = 2'b10 == w_ge_0_gc_0_leaf_procdff_71563_Q[4:3];   
    assign w_ge_0_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54730_Y = {2{1'b1}} == w_ge_0_gc_0_leaf_procdff_71563_Q[4:3];   
    reg [31:0] g_ge_0_gc_0_leaf_procdff_71548_q;
    assign w_ge_0_gc_0_leaf_procdff_71548_Q = g_ge_0_gc_0_leaf_procdff_71548_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_procdff_71548_q <= 32'b00000000000000000000000000000100;   
    reg [551:0] g_ge_0_gc_0_leaf_procdff_71549_q;
    assign w_ge_0_gc_0_leaf_procdff_71549_Q = g_ge_0_gc_0_leaf_procdff_71549_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_procdff_71549_q <= w_ge_0_gc_0_leaf_procdff_71550_Q[551:0];   
    reg [551:0] g_ge_0_gc_0_leaf_procdff_71550_q;
    assign w_ge_0_gc_0_leaf_procdff_71550_Q = g_ge_0_gc_0_leaf_procdff_71550_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_procdff_71550_q <= {w_ge_0_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54731_Y[137:0], w_ge_0_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54729_Y[137:0], w_ge_0_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54727_Y[137:0], w_ge_0_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54725_Y[137:0]};   
    reg [0:0] g_ge_0_gc_0_leaf_procdff_71551_q;
    assign w_ge_0_gc_0_leaf_procdff_71551_Q = g_ge_0_gc_0_leaf_procdff_71551_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_procdff_71551_q <= w_ge_0_gc_0_leaf_procdff_71557_Q[0];   
    reg [567:0] g_ge_0_gc_0_leaf_procdff_71552_q;
    assign w_ge_0_gc_0_leaf_procdff_71552_Q = g_ge_0_gc_0_leaf_procdff_71552_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_procdff_71552_q <= w_ge_0_gc_0_leaf_procdff_71558_Q[567:0];   
    reg [0:0] g_ge_0_gc_0_leaf_procdff_71553_q;
    assign w_ge_0_gc_0_leaf_procdff_71553_Q = g_ge_0_gc_0_leaf_procdff_71553_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_procdff_71553_q <= w_ge_0_gc_0_leaf_procdff_71559_Q[0];   
    reg [3:0] g_ge_0_gc_0_leaf_procdff_71554_q;
    assign w_ge_0_gc_0_leaf_procdff_71554_Q = g_ge_0_gc_0_leaf_procdff_71554_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_procdff_71554_q <= w_ge_0_gc_0_leaf_procdff_71560_Q[3:0];   
    reg [2175:0] g_ge_0_gc_0_leaf_procdff_71555_q;
    assign w_ge_0_gc_0_leaf_procdff_71555_Q = g_ge_0_gc_0_leaf_procdff_71555_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_procdff_71555_q <= w_ge_0_gc_0_leaf_procdff_71561_Q[2175:0];   
    reg [29:0] g_ge_0_gc_0_leaf_procdff_71556_q;
    assign w_ge_0_gc_0_leaf_procdff_71556_Q = g_ge_0_gc_0_leaf_procdff_71556_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_procdff_71556_q <= w_ge_0_gc_0_leaf_procdff_71562_Q[29:0];   
    reg [0:0] g_ge_0_gc_0_leaf_procdff_71557_q;
    assign w_ge_0_gc_0_leaf_procdff_71557_Q = g_ge_0_gc_0_leaf_procdff_71557_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_procdff_71557_q <= w_procdff_71763_Q[0];   
    reg [567:0] g_ge_0_gc_0_leaf_procdff_71558_q;
    assign w_ge_0_gc_0_leaf_procdff_71558_Q = g_ge_0_gc_0_leaf_procdff_71558_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_procdff_71558_q <= {w_procdff_71764_Q[7:0], w_procdff_71765_Q[511:0], w_procdff_71766_Q[31:0], w_procdff_71767_Q[15:0]};   
    reg [0:0] g_ge_0_gc_0_leaf_procdff_71559_q;
    assign w_ge_0_gc_0_leaf_procdff_71559_Q = g_ge_0_gc_0_leaf_procdff_71559_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_procdff_71559_q <= w_procdff_71768_Q[0];   
    reg [3:0] g_ge_0_gc_0_leaf_procdff_71560_q;
    assign w_ge_0_gc_0_leaf_procdff_71560_Q = g_ge_0_gc_0_leaf_procdff_71560_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_procdff_71560_q <= {w_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54924_Y[0], w_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54916_Y[0], w_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54908_Y[0], w_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54900_Y[0]};   
    reg [2175:0] g_ge_0_gc_0_leaf_procdff_71561_q;
    assign w_ge_0_gc_0_leaf_procdff_71561_Q = g_ge_0_gc_0_leaf_procdff_71561_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_procdff_71561_q <= {w_procdff_71770_Q[2197:1110], w_procdff_71770_Q[1098:11]};   
    reg [29:0] g_ge_0_gc_0_leaf_procdff_71562_q;
    assign w_ge_0_gc_0_leaf_procdff_71562_Q = g_ge_0_gc_0_leaf_procdff_71562_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_procdff_71562_q <= {w_procmux_66659_Y[0], w_ge_ot_hbm_idx_score_quarter_static_h_sv_92_54933_Y[0], w_add_ot_hbm_idx_score_quarter_static_h_sv_91_54930_Y[19:0], {4{1'b0}}, w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54927_Y[0], w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54919_Y[0], w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54911_Y[0], w_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54903_Y[0]};   
    reg [7:0] g_ge_0_gc_0_leaf_procdff_71563_q;
    assign w_ge_0_gc_0_leaf_procdff_71563_Q = g_ge_0_gc_0_leaf_procdff_71563_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_procdff_71563_q <= {8{1'b0}};   
    assign w_ge_0_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54725_Y = w_ge_0_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54724_Y[0] ? {w_ge_0_gc_0_leaf_core_procdff_71537_Q[0], w_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_ge_0_gc_0_leaf_core_u_vl_q[4:1], w_u_hb_idx_s_Q_r0c0_k3h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c0_k2h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c0_k1h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c0_k0h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c0_k3h1_cf_out[0], w_u_hb_idx_s_Q_r0c0_k2h1_cf_out[0], w_u_hb_idx_s_Q_r0c0_k1h1_cf_out[0], w_u_hb_idx_s_Q_r0c0_k0h1_cf_out[0]} : {138{1'b0}};   
    assign w_ge_0_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54727_Y = w_ge_0_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54726_Y[0] ? {w_ge_0_gc_0_leaf_core_procdff_71537_Q[0], w_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_ge_0_gc_0_leaf_core_u_vl_q[4:1], w_u_hb_idx_s_Q_r0c0_k3h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c0_k2h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c0_k1h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c0_k0h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c0_k3h1_cf_out[0], w_u_hb_idx_s_Q_r0c0_k2h1_cf_out[0], w_u_hb_idx_s_Q_r0c0_k1h1_cf_out[0], w_u_hb_idx_s_Q_r0c0_k0h1_cf_out[0]} : {138{1'b0}};   
    assign w_ge_0_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54729_Y = w_ge_0_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54728_Y[0] ? {w_ge_0_gc_0_leaf_core_procdff_71537_Q[0], w_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_ge_0_gc_0_leaf_core_u_vl_q[4:1], w_u_hb_idx_s_Q_r0c0_k3h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c0_k2h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c0_k1h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c0_k0h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c0_k3h1_cf_out[0], w_u_hb_idx_s_Q_r0c0_k2h1_cf_out[0], w_u_hb_idx_s_Q_r0c0_k1h1_cf_out[0], w_u_hb_idx_s_Q_r0c0_k0h1_cf_out[0]} : {138{1'b0}};   
    assign w_ge_0_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54731_Y = w_ge_0_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54730_Y[0] ? {w_ge_0_gc_0_leaf_core_procdff_71537_Q[0], w_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_ge_0_gc_0_leaf_core_u_vl_q[4:1], w_u_hb_idx_s_Q_r0c0_k3h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c0_k2h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c0_k1h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c0_k0h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c0_k3h1_cf_out[0], w_u_hb_idx_s_Q_r0c0_k2h1_cf_out[0], w_u_hb_idx_s_Q_r0c0_k1h1_cf_out[0], w_u_hb_idx_s_Q_r0c0_k0h1_cf_out[0]} : {138{1'b0}};   
    assign w_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55671_Y = w_ge_0_gc_0_leaf_core_procdff_71521_Q[7:0] + {8{1'b0}};   
    assign w_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55672_Y = w_ge_0_gc_0_leaf_core_procdff_71521_Q[7:0] + 8'b00000001;   
    assign w_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55673_Y = w_ge_0_gc_0_leaf_core_procdff_71521_Q[7:0] + 8'b00000010;   
    assign w_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55674_Y = w_ge_0_gc_0_leaf_core_procdff_71521_Q[7:0] + 8'b00000011;   
    assign w_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55675_Y = w_ge_0_gc_0_leaf_core_procdff_71521_Q[7:0] + 8'b00000100;   
    assign w_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55676_Y = w_ge_0_gc_0_leaf_core_procdff_71521_Q[7:0] + 8'b00000101;   
    assign w_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55677_Y = w_ge_0_gc_0_leaf_core_procdff_71521_Q[7:0] + 8'b00000110;   
    assign w_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55678_Y = w_ge_0_gc_0_leaf_core_procdff_71521_Q[7:0] + 8'b00000111;   
    assign w_ge_0_gc_0_leaf_core_auto_proc_dff_cc_220_proc_dff_71533_Y = ~rst_n;
    assign w_ge_0_gc_0_leaf_core_auto_proc_dff_cc_220_proc_dff_71538_Y = ~rst_n;
    assign w_ge_0_gc_0_leaf_core_auto_proc_dff_cc_220_proc_dff_71543_Y = ~rst_n;
    assign w_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y = w_ge_0_gc_0_leaf_procdff_71557_Q[0] && w_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[4];   
    assign w_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_167_55670_Y = w_ge_0_gc_0_leaf_procdff_71559_Q[0] && w_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[4];   
    assign w_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y = w_ge_0_gc_0_leaf_core_u_vl_q[0] && w_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[4];   
    assign w_ge_0_gc_0_leaf_core_logic_not_ot_hbm_idx_chunk_rt_h_sv_154_55666_Y = !rst_n;   
    reg [31:0] g_ge_0_gc_0_leaf_core_procdff_71508_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71508_Q = g_ge_0_gc_0_leaf_core_procdff_71508_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_core_procdff_71508_q <= w_u_hb_idx_s_Q_r0c0_k3h1_cs_out[31:0];   
    reg [0:0] g_ge_0_gc_0_leaf_core_procdff_71509_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71509_Q = g_ge_0_gc_0_leaf_core_procdff_71509_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_core_procdff_71509_q <= w_u_hb_idx_s_Q_r0c0_k3h1_cf_out[0];   
    reg [31:0] g_ge_0_gc_0_leaf_core_procdff_71510_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71510_Q = g_ge_0_gc_0_leaf_core_procdff_71510_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_core_procdff_71510_q <= w_u_hb_idx_s_Q_r0c0_k2h1_cs_out[31:0];   
    reg [0:0] g_ge_0_gc_0_leaf_core_procdff_71511_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71511_Q = g_ge_0_gc_0_leaf_core_procdff_71511_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_core_procdff_71511_q <= w_u_hb_idx_s_Q_r0c0_k2h1_cf_out[0];   
    reg [31:0] g_ge_0_gc_0_leaf_core_procdff_71512_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71512_Q = g_ge_0_gc_0_leaf_core_procdff_71512_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_core_procdff_71512_q <= w_u_hb_idx_s_Q_r0c0_k1h1_cs_out[31:0];   
    reg [0:0] g_ge_0_gc_0_leaf_core_procdff_71513_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71513_Q = g_ge_0_gc_0_leaf_core_procdff_71513_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_core_procdff_71513_q <= w_u_hb_idx_s_Q_r0c0_k1h1_cf_out[0];   
    reg [31:0] g_ge_0_gc_0_leaf_core_procdff_71514_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71514_Q = g_ge_0_gc_0_leaf_core_procdff_71514_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_core_procdff_71514_q <= w_u_hb_idx_s_Q_r0c0_k0h1_cs_out[31:0];   
    reg [0:0] g_ge_0_gc_0_leaf_core_procdff_71515_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71515_Q = g_ge_0_gc_0_leaf_core_procdff_71515_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_core_procdff_71515_q <= w_u_hb_idx_s_Q_r0c0_k0h1_cf_out[0];   
    reg [0:0] g_ge_0_gc_0_leaf_core_procdff_71516_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71516_Q = g_ge_0_gc_0_leaf_core_procdff_71516_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_core_procdff_71516_q <= w_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0];   
    reg [3:0] g_ge_0_gc_0_leaf_core_procdff_71517_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71517_Q = g_ge_0_gc_0_leaf_core_procdff_71517_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_core_procdff_71517_q <= w_ge_0_gc_0_leaf_core_u_vl_q[4:1];   
    reg [31:0] g_ge_0_gc_0_leaf_core_procdff_71518_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71518_Q = g_ge_0_gc_0_leaf_core_procdff_71518_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_core_procdff_71518_q <= 32'b00000000000000000000000000001000;   
    reg [567:0] g_ge_0_gc_0_leaf_core_procdff_71519_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71519_Q = g_ge_0_gc_0_leaf_core_procdff_71519_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_core_procdff_71519_q <= w_ge_0_gc_0_leaf_procdff_71558_Q[567:0];   
    reg [0:0] g_ge_0_gc_0_leaf_core_procdff_71520_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71520_Q = g_ge_0_gc_0_leaf_core_procdff_71520_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_core_procdff_71520_q <= w_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_167_55670_Y[0];   
    reg [7:0] g_ge_0_gc_0_leaf_core_procdff_71521_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71521_Q = g_ge_0_gc_0_leaf_core_procdff_71521_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_core_procdff_71521_q <= w_ge_0_gc_0_leaf_procdff_71563_Q[7:0];   
    reg [0:0] g_ge_0_gc_0_leaf_core_procdff_71522_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71522_Q = g_ge_0_gc_0_leaf_core_procdff_71522_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_core_procdff_71522_q <= w_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0];   
    reg [3:0] g_ge_0_gc_0_leaf_core_procdff_71523_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71523_Q = g_ge_0_gc_0_leaf_core_procdff_71523_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_core_procdff_71523_q <= w_ge_0_gc_0_leaf_procdff_71560_Q[3:0];   
    reg [2175:0] g_ge_0_gc_0_leaf_core_procdff_71524_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71524_Q = g_ge_0_gc_0_leaf_core_procdff_71524_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_core_procdff_71524_q <= w_ge_0_gc_0_leaf_procdff_71561_Q[2175:0];   
    reg [7:0] g_ge_0_gc_0_leaf_core_procdff_71525_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71525_Q = g_ge_0_gc_0_leaf_core_procdff_71525_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_core_procdff_71525_q <= w_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55671_Y[7:0];   
    reg [7:0] g_ge_0_gc_0_leaf_core_procdff_71526_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71526_Q = g_ge_0_gc_0_leaf_core_procdff_71526_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_core_procdff_71526_q <= w_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55672_Y[7:0];   
    reg [7:0] g_ge_0_gc_0_leaf_core_procdff_71527_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71527_Q = g_ge_0_gc_0_leaf_core_procdff_71527_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_core_procdff_71527_q <= w_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55673_Y[7:0];   
    reg [7:0] g_ge_0_gc_0_leaf_core_procdff_71528_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71528_Q = g_ge_0_gc_0_leaf_core_procdff_71528_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_core_procdff_71528_q <= w_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55674_Y[7:0];   
    reg [7:0] g_ge_0_gc_0_leaf_core_procdff_71529_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71529_Q = g_ge_0_gc_0_leaf_core_procdff_71529_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_core_procdff_71529_q <= w_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55675_Y[7:0];   
    reg [7:0] g_ge_0_gc_0_leaf_core_procdff_71530_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71530_Q = g_ge_0_gc_0_leaf_core_procdff_71530_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_core_procdff_71530_q <= w_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55676_Y[7:0];   
    reg [7:0] g_ge_0_gc_0_leaf_core_procdff_71531_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71531_Q = g_ge_0_gc_0_leaf_core_procdff_71531_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_core_procdff_71531_q <= w_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55677_Y[7:0];   
    reg [7:0] g_ge_0_gc_0_leaf_core_procdff_71532_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71532_Q = g_ge_0_gc_0_leaf_core_procdff_71532_q;
    always @(posedge clk) g_ge_0_gc_0_leaf_core_procdff_71532_q <= w_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55678_Y[7:0];   
    reg [0:0] g_ge_0_gc_0_leaf_core_procdff_71537_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71537_Q = g_ge_0_gc_0_leaf_core_procdff_71537_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) g_ge_0_gc_0_leaf_core_procdff_71537_q <= 1'b0; else g_ge_0_gc_0_leaf_core_procdff_71537_q <= w_ge_0_gc_0_leaf_core_reduce_and_ot_hbm_idx_chunk_rt_h_sv_155_55667_Y[0];   
    reg [15:0] g_ge_0_gc_0_leaf_core_procdff_71542_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71542_Q = g_ge_0_gc_0_leaf_core_procdff_71542_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) g_ge_0_gc_0_leaf_core_procdff_71542_q <= 16'b0000000000000000; else g_ge_0_gc_0_leaf_core_procdff_71542_q <= {w_u_hb_idx_s_Q_r0c0_k3h1_prdy[1:0], w_u_hb_idx_s_Q_r0c0_k3h0_prdy[1:0], w_u_hb_idx_s_Q_r0c0_k2h1_prdy[1:0], w_u_hb_idx_s_Q_r0c0_k2h0_prdy[1:0], w_u_hb_idx_s_Q_r0c0_k1h1_prdy[1:0], w_u_hb_idx_s_Q_r0c0_k1h0_prdy[1:0], w_u_hb_idx_s_Q_r0c0_k0h1_prdy[1:0], w_u_hb_idx_s_Q_r0c0_k0h0_prdy[1:0]};   
    reg [15:0] g_ge_0_gc_0_leaf_core_procdff_71547_q;
    assign w_ge_0_gc_0_leaf_core_procdff_71547_Q = g_ge_0_gc_0_leaf_core_procdff_71547_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) g_ge_0_gc_0_leaf_core_procdff_71547_q <= 16'b0000000000000000; else g_ge_0_gc_0_leaf_core_procdff_71547_q <= w_ge_0_gc_0_leaf_core_procdff_71542_Q[15:0];   
    assign w_ge_0_gc_0_leaf_core_reduce_and_ot_hbm_idx_chunk_rt_h_sv_155_55667_Y = &w_ge_0_gc_0_leaf_core_procdff_71547_Q[15:0];   
    assign w_ge_0_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54724_Y = !w_ge_0_gc_1_leaf_procdff_71563_Q[4:3];   
    assign w_ge_0_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54726_Y = 2'b01 == w_ge_0_gc_1_leaf_procdff_71563_Q[4:3];   
    assign w_ge_0_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54728_Y = 2'b10 == w_ge_0_gc_1_leaf_procdff_71563_Q[4:3];   
    assign w_ge_0_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54730_Y = {2{1'b1}} == w_ge_0_gc_1_leaf_procdff_71563_Q[4:3];   
    reg [31:0] g_ge_0_gc_1_leaf_procdff_71548_q;
    assign w_ge_0_gc_1_leaf_procdff_71548_Q = g_ge_0_gc_1_leaf_procdff_71548_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_procdff_71548_q <= 32'b00000000000000000000000000000100;   
    reg [551:0] g_ge_0_gc_1_leaf_procdff_71549_q;
    assign w_ge_0_gc_1_leaf_procdff_71549_Q = g_ge_0_gc_1_leaf_procdff_71549_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_procdff_71549_q <= w_ge_0_gc_1_leaf_procdff_71550_Q[551:0];   
    reg [551:0] g_ge_0_gc_1_leaf_procdff_71550_q;
    assign w_ge_0_gc_1_leaf_procdff_71550_Q = g_ge_0_gc_1_leaf_procdff_71550_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_procdff_71550_q <= {w_ge_0_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54731_Y[137:0], w_ge_0_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54729_Y[137:0], w_ge_0_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54727_Y[137:0], w_ge_0_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54725_Y[137:0]};   
    reg [0:0] g_ge_0_gc_1_leaf_procdff_71551_q;
    assign w_ge_0_gc_1_leaf_procdff_71551_Q = g_ge_0_gc_1_leaf_procdff_71551_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_procdff_71551_q <= w_ge_0_gc_1_leaf_procdff_71557_Q[0];   
    reg [567:0] g_ge_0_gc_1_leaf_procdff_71552_q;
    assign w_ge_0_gc_1_leaf_procdff_71552_Q = g_ge_0_gc_1_leaf_procdff_71552_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_procdff_71552_q <= w_ge_0_gc_1_leaf_procdff_71558_Q[567:0];   
    reg [0:0] g_ge_0_gc_1_leaf_procdff_71553_q;
    assign w_ge_0_gc_1_leaf_procdff_71553_Q = g_ge_0_gc_1_leaf_procdff_71553_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_procdff_71553_q <= w_ge_0_gc_1_leaf_procdff_71559_Q[0];   
    reg [3:0] g_ge_0_gc_1_leaf_procdff_71554_q;
    assign w_ge_0_gc_1_leaf_procdff_71554_Q = g_ge_0_gc_1_leaf_procdff_71554_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_procdff_71554_q <= w_ge_0_gc_1_leaf_procdff_71560_Q[3:0];   
    reg [2175:0] g_ge_0_gc_1_leaf_procdff_71555_q;
    assign w_ge_0_gc_1_leaf_procdff_71555_Q = g_ge_0_gc_1_leaf_procdff_71555_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_procdff_71555_q <= w_ge_0_gc_1_leaf_procdff_71561_Q[2175:0];   
    reg [29:0] g_ge_0_gc_1_leaf_procdff_71556_q;
    assign w_ge_0_gc_1_leaf_procdff_71556_Q = g_ge_0_gc_1_leaf_procdff_71556_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_procdff_71556_q <= w_ge_0_gc_1_leaf_procdff_71562_Q[29:0];   
    reg [0:0] g_ge_0_gc_1_leaf_procdff_71557_q;
    assign w_ge_0_gc_1_leaf_procdff_71557_Q = g_ge_0_gc_1_leaf_procdff_71557_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_procdff_71557_q <= w_ge_0_gc_0_leaf_procdff_71551_Q[0];   
    reg [567:0] g_ge_0_gc_1_leaf_procdff_71558_q;
    assign w_ge_0_gc_1_leaf_procdff_71558_Q = g_ge_0_gc_1_leaf_procdff_71558_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_procdff_71558_q <= w_ge_0_gc_0_leaf_procdff_71552_Q[567:0];   
    reg [0:0] g_ge_0_gc_1_leaf_procdff_71559_q;
    assign w_ge_0_gc_1_leaf_procdff_71559_Q = g_ge_0_gc_1_leaf_procdff_71559_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_procdff_71559_q <= w_ge_0_gc_0_leaf_procdff_71553_Q[0];   
    reg [3:0] g_ge_0_gc_1_leaf_procdff_71560_q;
    assign w_ge_0_gc_1_leaf_procdff_71560_Q = g_ge_0_gc_1_leaf_procdff_71560_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_procdff_71560_q <= w_ge_0_gc_0_leaf_procdff_71554_Q[3:0];   
    reg [2175:0] g_ge_0_gc_1_leaf_procdff_71561_q;
    assign w_ge_0_gc_1_leaf_procdff_71561_Q = g_ge_0_gc_1_leaf_procdff_71561_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_procdff_71561_q <= w_ge_0_gc_0_leaf_procdff_71555_Q[2175:0];   
    reg [29:0] g_ge_0_gc_1_leaf_procdff_71562_q;
    assign w_ge_0_gc_1_leaf_procdff_71562_Q = g_ge_0_gc_1_leaf_procdff_71562_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_procdff_71562_q <= w_ge_0_gc_0_leaf_procdff_71556_Q[29:0];   
    reg [7:0] g_ge_0_gc_1_leaf_procdff_71563_q;
    assign w_ge_0_gc_1_leaf_procdff_71563_Q = g_ge_0_gc_1_leaf_procdff_71563_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_procdff_71563_q <= 8'b00001000;   
    assign w_ge_0_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54725_Y = w_ge_0_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54724_Y[0] ? {w_ge_0_gc_1_leaf_core_procdff_71537_Q[0], w_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_ge_0_gc_1_leaf_core_u_vl_q[4:1], w_u_hb_idx_s_Q_r0c1_k3h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c1_k2h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c1_k1h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c1_k0h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c1_k3h1_cf_out[0], w_u_hb_idx_s_Q_r0c1_k2h1_cf_out[0], w_u_hb_idx_s_Q_r0c1_k1h1_cf_out[0], w_u_hb_idx_s_Q_r0c1_k0h1_cf_out[0]} : w_ge_0_gc_0_leaf_procdff_71549_Q[137:0];   
    assign w_ge_0_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54727_Y = w_ge_0_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54726_Y[0] ? {w_ge_0_gc_1_leaf_core_procdff_71537_Q[0], w_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_ge_0_gc_1_leaf_core_u_vl_q[4:1], w_u_hb_idx_s_Q_r0c1_k3h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c1_k2h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c1_k1h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c1_k0h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c1_k3h1_cf_out[0], w_u_hb_idx_s_Q_r0c1_k2h1_cf_out[0], w_u_hb_idx_s_Q_r0c1_k1h1_cf_out[0], w_u_hb_idx_s_Q_r0c1_k0h1_cf_out[0]} : w_ge_0_gc_0_leaf_procdff_71549_Q[275:138];   
    assign w_ge_0_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54729_Y = w_ge_0_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54728_Y[0] ? {w_ge_0_gc_1_leaf_core_procdff_71537_Q[0], w_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_ge_0_gc_1_leaf_core_u_vl_q[4:1], w_u_hb_idx_s_Q_r0c1_k3h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c1_k2h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c1_k1h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c1_k0h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c1_k3h1_cf_out[0], w_u_hb_idx_s_Q_r0c1_k2h1_cf_out[0], w_u_hb_idx_s_Q_r0c1_k1h1_cf_out[0], w_u_hb_idx_s_Q_r0c1_k0h1_cf_out[0]} : w_ge_0_gc_0_leaf_procdff_71549_Q[413:276];   
    assign w_ge_0_gc_1_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv_37_54731_Y = w_ge_0_gc_1_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54730_Y[0] ? {w_ge_0_gc_1_leaf_core_procdff_71537_Q[0], w_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_ge_0_gc_1_leaf_core_u_vl_q[4:1], w_u_hb_idx_s_Q_r0c1_k3h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c1_k2h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c1_k1h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c1_k0h1_cs_out[31:0], w_u_hb_idx_s_Q_r0c1_k3h1_cf_out[0], w_u_hb_idx_s_Q_r0c1_k2h1_cf_out[0], w_u_hb_idx_s_Q_r0c1_k1h1_cf_out[0], w_u_hb_idx_s_Q_r0c1_k0h1_cf_out[0]} : w_ge_0_gc_0_leaf_procdff_71549_Q[551:414];   
    assign w_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55671_Y = w_ge_0_gc_1_leaf_core_procdff_71521_Q[7:0] + {8{1'b0}};   
    assign w_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55672_Y = w_ge_0_gc_1_leaf_core_procdff_71521_Q[7:0] + 8'b00000001;   
    assign w_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55673_Y = w_ge_0_gc_1_leaf_core_procdff_71521_Q[7:0] + 8'b00000010;   
    assign w_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55674_Y = w_ge_0_gc_1_leaf_core_procdff_71521_Q[7:0] + 8'b00000011;   
    assign w_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55675_Y = w_ge_0_gc_1_leaf_core_procdff_71521_Q[7:0] + 8'b00000100;   
    assign w_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55676_Y = w_ge_0_gc_1_leaf_core_procdff_71521_Q[7:0] + 8'b00000101;   
    assign w_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55677_Y = w_ge_0_gc_1_leaf_core_procdff_71521_Q[7:0] + 8'b00000110;   
    assign w_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55678_Y = w_ge_0_gc_1_leaf_core_procdff_71521_Q[7:0] + 8'b00000111;   
    assign w_ge_0_gc_1_leaf_core_auto_proc_dff_cc_220_proc_dff_71533_Y = ~rst_n;
    assign w_ge_0_gc_1_leaf_core_auto_proc_dff_cc_220_proc_dff_71538_Y = ~rst_n;
    assign w_ge_0_gc_1_leaf_core_auto_proc_dff_cc_220_proc_dff_71543_Y = ~rst_n;
    assign w_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y = w_ge_0_gc_1_leaf_procdff_71557_Q[0] && w_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[4];   
    assign w_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_167_55670_Y = w_ge_0_gc_1_leaf_procdff_71559_Q[0] && w_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[4];   
    assign w_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y = w_ge_0_gc_1_leaf_core_u_vl_q[0] && w_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[4];   
    assign w_ge_0_gc_1_leaf_core_logic_not_ot_hbm_idx_chunk_rt_h_sv_154_55666_Y = !rst_n;   
    reg [31:0] g_ge_0_gc_1_leaf_core_procdff_71508_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71508_Q = g_ge_0_gc_1_leaf_core_procdff_71508_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_core_procdff_71508_q <= w_u_hb_idx_s_Q_r0c1_k3h1_cs_out[31:0];   
    reg [0:0] g_ge_0_gc_1_leaf_core_procdff_71509_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71509_Q = g_ge_0_gc_1_leaf_core_procdff_71509_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_core_procdff_71509_q <= w_u_hb_idx_s_Q_r0c1_k3h1_cf_out[0];   
    reg [31:0] g_ge_0_gc_1_leaf_core_procdff_71510_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71510_Q = g_ge_0_gc_1_leaf_core_procdff_71510_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_core_procdff_71510_q <= w_u_hb_idx_s_Q_r0c1_k2h1_cs_out[31:0];   
    reg [0:0] g_ge_0_gc_1_leaf_core_procdff_71511_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71511_Q = g_ge_0_gc_1_leaf_core_procdff_71511_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_core_procdff_71511_q <= w_u_hb_idx_s_Q_r0c1_k2h1_cf_out[0];   
    reg [31:0] g_ge_0_gc_1_leaf_core_procdff_71512_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71512_Q = g_ge_0_gc_1_leaf_core_procdff_71512_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_core_procdff_71512_q <= w_u_hb_idx_s_Q_r0c1_k1h1_cs_out[31:0];   
    reg [0:0] g_ge_0_gc_1_leaf_core_procdff_71513_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71513_Q = g_ge_0_gc_1_leaf_core_procdff_71513_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_core_procdff_71513_q <= w_u_hb_idx_s_Q_r0c1_k1h1_cf_out[0];   
    reg [31:0] g_ge_0_gc_1_leaf_core_procdff_71514_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71514_Q = g_ge_0_gc_1_leaf_core_procdff_71514_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_core_procdff_71514_q <= w_u_hb_idx_s_Q_r0c1_k0h1_cs_out[31:0];   
    reg [0:0] g_ge_0_gc_1_leaf_core_procdff_71515_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71515_Q = g_ge_0_gc_1_leaf_core_procdff_71515_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_core_procdff_71515_q <= w_u_hb_idx_s_Q_r0c1_k0h1_cf_out[0];   
    reg [0:0] g_ge_0_gc_1_leaf_core_procdff_71516_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71516_Q = g_ge_0_gc_1_leaf_core_procdff_71516_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_core_procdff_71516_q <= w_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0];   
    reg [3:0] g_ge_0_gc_1_leaf_core_procdff_71517_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71517_Q = g_ge_0_gc_1_leaf_core_procdff_71517_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_core_procdff_71517_q <= w_ge_0_gc_1_leaf_core_u_vl_q[4:1];   
    reg [31:0] g_ge_0_gc_1_leaf_core_procdff_71518_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71518_Q = g_ge_0_gc_1_leaf_core_procdff_71518_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_core_procdff_71518_q <= 32'b00000000000000000000000000001000;   
    reg [567:0] g_ge_0_gc_1_leaf_core_procdff_71519_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71519_Q = g_ge_0_gc_1_leaf_core_procdff_71519_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_core_procdff_71519_q <= w_ge_0_gc_1_leaf_procdff_71558_Q[567:0];   
    reg [0:0] g_ge_0_gc_1_leaf_core_procdff_71520_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71520_Q = g_ge_0_gc_1_leaf_core_procdff_71520_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_core_procdff_71520_q <= w_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_167_55670_Y[0];   
    reg [7:0] g_ge_0_gc_1_leaf_core_procdff_71521_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71521_Q = g_ge_0_gc_1_leaf_core_procdff_71521_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_core_procdff_71521_q <= w_ge_0_gc_1_leaf_procdff_71563_Q[7:0];   
    reg [0:0] g_ge_0_gc_1_leaf_core_procdff_71522_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71522_Q = g_ge_0_gc_1_leaf_core_procdff_71522_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_core_procdff_71522_q <= w_ge_0_gc_1_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0];   
    reg [3:0] g_ge_0_gc_1_leaf_core_procdff_71523_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71523_Q = g_ge_0_gc_1_leaf_core_procdff_71523_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_core_procdff_71523_q <= w_ge_0_gc_1_leaf_procdff_71560_Q[3:0];   
    reg [2175:0] g_ge_0_gc_1_leaf_core_procdff_71524_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71524_Q = g_ge_0_gc_1_leaf_core_procdff_71524_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_core_procdff_71524_q <= w_ge_0_gc_1_leaf_procdff_71561_Q[2175:0];   
    reg [7:0] g_ge_0_gc_1_leaf_core_procdff_71525_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71525_Q = g_ge_0_gc_1_leaf_core_procdff_71525_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_core_procdff_71525_q <= w_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55671_Y[7:0];   
    reg [7:0] g_ge_0_gc_1_leaf_core_procdff_71526_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71526_Q = g_ge_0_gc_1_leaf_core_procdff_71526_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_core_procdff_71526_q <= w_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55672_Y[7:0];   
    reg [7:0] g_ge_0_gc_1_leaf_core_procdff_71527_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71527_Q = g_ge_0_gc_1_leaf_core_procdff_71527_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_core_procdff_71527_q <= w_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55673_Y[7:0];   
    reg [7:0] g_ge_0_gc_1_leaf_core_procdff_71528_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71528_Q = g_ge_0_gc_1_leaf_core_procdff_71528_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_core_procdff_71528_q <= w_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55674_Y[7:0];   
    reg [7:0] g_ge_0_gc_1_leaf_core_procdff_71529_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71529_Q = g_ge_0_gc_1_leaf_core_procdff_71529_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_core_procdff_71529_q <= w_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55675_Y[7:0];   
    reg [7:0] g_ge_0_gc_1_leaf_core_procdff_71530_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71530_Q = g_ge_0_gc_1_leaf_core_procdff_71530_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_core_procdff_71530_q <= w_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55676_Y[7:0];   
    reg [7:0] g_ge_0_gc_1_leaf_core_procdff_71531_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71531_Q = g_ge_0_gc_1_leaf_core_procdff_71531_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_core_procdff_71531_q <= w_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55677_Y[7:0];   
    reg [7:0] g_ge_0_gc_1_leaf_core_procdff_71532_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71532_Q = g_ge_0_gc_1_leaf_core_procdff_71532_q;
    always @(posedge clk) g_ge_0_gc_1_leaf_core_procdff_71532_q <= w_ge_0_gc_1_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55678_Y[7:0];   
    reg [0:0] g_ge_0_gc_1_leaf_core_procdff_71537_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71537_Q = g_ge_0_gc_1_leaf_core_procdff_71537_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) g_ge_0_gc_1_leaf_core_procdff_71537_q <= 1'b0; else g_ge_0_gc_1_leaf_core_procdff_71537_q <= w_ge_0_gc_1_leaf_core_reduce_and_ot_hbm_idx_chunk_rt_h_sv_155_55667_Y[0];   
    reg [15:0] g_ge_0_gc_1_leaf_core_procdff_71542_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71542_Q = g_ge_0_gc_1_leaf_core_procdff_71542_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) g_ge_0_gc_1_leaf_core_procdff_71542_q <= 16'b0000000000000000; else g_ge_0_gc_1_leaf_core_procdff_71542_q <= {w_u_hb_idx_s_Q_r0c1_k3h1_prdy[1:0], w_u_hb_idx_s_Q_r0c1_k3h0_prdy[1:0], w_u_hb_idx_s_Q_r0c1_k2h1_prdy[1:0], w_u_hb_idx_s_Q_r0c1_k2h0_prdy[1:0], w_u_hb_idx_s_Q_r0c1_k1h1_prdy[1:0], w_u_hb_idx_s_Q_r0c1_k1h0_prdy[1:0], w_u_hb_idx_s_Q_r0c1_k0h1_prdy[1:0], w_u_hb_idx_s_Q_r0c1_k0h0_prdy[1:0]};   
    reg [15:0] g_ge_0_gc_1_leaf_core_procdff_71547_q;
    assign w_ge_0_gc_1_leaf_core_procdff_71547_Q = g_ge_0_gc_1_leaf_core_procdff_71547_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) g_ge_0_gc_1_leaf_core_procdff_71547_q <= 16'b0000000000000000; else g_ge_0_gc_1_leaf_core_procdff_71547_q <= w_ge_0_gc_1_leaf_core_procdff_71542_Q[15:0];   
    assign w_ge_0_gc_1_leaf_core_reduce_and_ot_hbm_idx_chunk_rt_h_sv_155_55667_Y = &w_ge_0_gc_1_leaf_core_procdff_71547_Q[15:0];   
     
    ot_rst_delivered3 #(.REGIONS(5)) u_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr (
        .clk(clk),
        .rst_n(w_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n),
        .rst_n_in(rst_n)
    );
     
    ot_hdc_delay #(.D(0), .W(569)) u_ge_0_gc_0_leaf_core_u_qlate (
        .clk(clk),
        .d({w_ge_0_gc_0_leaf_core_procdff_71522_Q[0], w_ge_0_gc_0_leaf_core_procdff_71519_Q[567:0]}),
        .q(w_ge_0_gc_0_leaf_core_u_qlate_q),
        .rst_n(1'b1)
    );
     
    ot_hdc_delay #(.D(104), .RESET(1), .W(5)) u_ge_0_gc_0_leaf_core_u_vl (
        .clk(clk),
        .d({w_ge_0_gc_0_leaf_core_procdff_71523_Q[3:0], w_ge_0_gc_0_leaf_core_procdff_71520_Q[0]}),
        .q(w_ge_0_gc_0_leaf_core_u_vl_q),
        .rst_n(w_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[4])
    );
     
    ot_rst_delivered3 #(.REGIONS(5)) u_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr (
        .clk(clk),
        .rst_n(w_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n),
        .rst_n_in(rst_n)
    );
     
    ot_hdc_delay #(.D(0), .W(569)) u_ge_0_gc_1_leaf_core_u_qlate (
        .clk(clk),
        .d({w_ge_0_gc_1_leaf_core_procdff_71522_Q[0], w_ge_0_gc_1_leaf_core_procdff_71519_Q[567:0]}),
        .q(w_ge_0_gc_1_leaf_core_u_qlate_q),
        .rst_n(1'b1)
    );
     
    ot_hdc_delay #(.D(104), .RESET(1), .W(5)) u_ge_0_gc_1_leaf_core_u_vl (
        .clk(clk),
        .d({w_ge_0_gc_1_leaf_core_procdff_71523_Q[3:0], w_ge_0_gc_1_leaf_core_procdff_71520_Q[0]}),
        .q(w_ge_0_gc_1_leaf_core_u_vl_q),
        .rst_n(w_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[4])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r0c0_k0h0 (
        .cf_out(w_u_hb_idx_s_Q_r0c0_k0h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q_r0c0_k0h0_cs_out),
        .hid4({w_ge_0_gc_0_leaf_core_procdff_71528_Q[7:0], w_ge_0_gc_0_leaf_core_procdff_71527_Q[7:0], w_ge_0_gc_0_leaf_core_procdff_71526_Q[7:0], w_ge_0_gc_0_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_ge_0_gc_0_leaf_core_procdff_71524_Q[543:0]),
        .prdy(w_u_hb_idx_s_Q_r0c0_k0h0_prdy),
        .q_b(w_ge_0_gc_0_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_ge_0_gc_0_leaf_core_u_qlate_q[568]),
        .rst_col(w_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[0])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r0c0_k0h1 (
        .cf_in(w_u_hb_idx_s_Q_r0c0_k0h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q_r0c0_k0h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q_r0c0_k0h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q_r0c0_k0h1_cs_out),
        .hid4({w_ge_0_gc_0_leaf_core_procdff_71532_Q[7:0], w_ge_0_gc_0_leaf_core_procdff_71531_Q[7:0], w_ge_0_gc_0_leaf_core_procdff_71530_Q[7:0], w_ge_0_gc_0_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_ge_0_gc_0_leaf_core_procdff_71524_Q[543:0]),
        .prdy(w_u_hb_idx_s_Q_r0c0_k0h1_prdy),
        .q_b(w_ge_0_gc_0_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_ge_0_gc_0_leaf_core_u_qlate_q[568]),
        .rst_col(w_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[0])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r0c0_k1h0 (
        .cf_out(w_u_hb_idx_s_Q_r0c0_k1h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q_r0c0_k1h0_cs_out),
        .hid4({w_ge_0_gc_0_leaf_core_procdff_71528_Q[7:0], w_ge_0_gc_0_leaf_core_procdff_71527_Q[7:0], w_ge_0_gc_0_leaf_core_procdff_71526_Q[7:0], w_ge_0_gc_0_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_ge_0_gc_0_leaf_core_procdff_71524_Q[1087:544]),
        .prdy(w_u_hb_idx_s_Q_r0c0_k1h0_prdy),
        .q_b(w_ge_0_gc_0_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_ge_0_gc_0_leaf_core_u_qlate_q[568]),
        .rst_col(w_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[1])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r0c0_k1h1 (
        .cf_in(w_u_hb_idx_s_Q_r0c0_k1h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q_r0c0_k1h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q_r0c0_k1h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q_r0c0_k1h1_cs_out),
        .hid4({w_ge_0_gc_0_leaf_core_procdff_71532_Q[7:0], w_ge_0_gc_0_leaf_core_procdff_71531_Q[7:0], w_ge_0_gc_0_leaf_core_procdff_71530_Q[7:0], w_ge_0_gc_0_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_ge_0_gc_0_leaf_core_procdff_71524_Q[1087:544]),
        .prdy(w_u_hb_idx_s_Q_r0c0_k1h1_prdy),
        .q_b(w_ge_0_gc_0_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_ge_0_gc_0_leaf_core_u_qlate_q[568]),
        .rst_col(w_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[1])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r0c0_k2h0 (
        .cf_out(w_u_hb_idx_s_Q_r0c0_k2h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q_r0c0_k2h0_cs_out),
        .hid4({w_ge_0_gc_0_leaf_core_procdff_71528_Q[7:0], w_ge_0_gc_0_leaf_core_procdff_71527_Q[7:0], w_ge_0_gc_0_leaf_core_procdff_71526_Q[7:0], w_ge_0_gc_0_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_ge_0_gc_0_leaf_core_procdff_71524_Q[1631:1088]),
        .prdy(w_u_hb_idx_s_Q_r0c0_k2h0_prdy),
        .q_b(w_ge_0_gc_0_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_ge_0_gc_0_leaf_core_u_qlate_q[568]),
        .rst_col(w_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[2])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r0c0_k2h1 (
        .cf_in(w_u_hb_idx_s_Q_r0c0_k2h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q_r0c0_k2h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q_r0c0_k2h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q_r0c0_k2h1_cs_out),
        .hid4({w_ge_0_gc_0_leaf_core_procdff_71532_Q[7:0], w_ge_0_gc_0_leaf_core_procdff_71531_Q[7:0], w_ge_0_gc_0_leaf_core_procdff_71530_Q[7:0], w_ge_0_gc_0_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_ge_0_gc_0_leaf_core_procdff_71524_Q[1631:1088]),
        .prdy(w_u_hb_idx_s_Q_r0c0_k2h1_prdy),
        .q_b(w_ge_0_gc_0_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_ge_0_gc_0_leaf_core_u_qlate_q[568]),
        .rst_col(w_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[2])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r0c0_k3h0 (
        .cf_out(w_u_hb_idx_s_Q_r0c0_k3h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q_r0c0_k3h0_cs_out),
        .hid4({w_ge_0_gc_0_leaf_core_procdff_71528_Q[7:0], w_ge_0_gc_0_leaf_core_procdff_71527_Q[7:0], w_ge_0_gc_0_leaf_core_procdff_71526_Q[7:0], w_ge_0_gc_0_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_ge_0_gc_0_leaf_core_procdff_71524_Q[2175:1632]),
        .prdy(w_u_hb_idx_s_Q_r0c0_k3h0_prdy),
        .q_b(w_ge_0_gc_0_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_ge_0_gc_0_leaf_core_u_qlate_q[568]),
        .rst_col(w_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[3])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r0c0_k3h1 (
        .cf_in(w_u_hb_idx_s_Q_r0c0_k3h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q_r0c0_k3h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q_r0c0_k3h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q_r0c0_k3h1_cs_out),
        .hid4({w_ge_0_gc_0_leaf_core_procdff_71532_Q[7:0], w_ge_0_gc_0_leaf_core_procdff_71531_Q[7:0], w_ge_0_gc_0_leaf_core_procdff_71530_Q[7:0], w_ge_0_gc_0_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_ge_0_gc_0_leaf_core_procdff_71524_Q[2175:1632]),
        .prdy(w_u_hb_idx_s_Q_r0c0_k3h1_prdy),
        .q_b(w_ge_0_gc_0_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_ge_0_gc_0_leaf_core_u_qlate_q[568]),
        .rst_col(w_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[3])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r0c1_k0h0 (
        .cf_out(w_u_hb_idx_s_Q_r0c1_k0h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q_r0c1_k0h0_cs_out),
        .hid4({w_ge_0_gc_1_leaf_core_procdff_71528_Q[7:0], w_ge_0_gc_1_leaf_core_procdff_71527_Q[7:0], w_ge_0_gc_1_leaf_core_procdff_71526_Q[7:0], w_ge_0_gc_1_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_ge_0_gc_1_leaf_core_procdff_71524_Q[543:0]),
        .prdy(w_u_hb_idx_s_Q_r0c1_k0h0_prdy),
        .q_b(w_ge_0_gc_1_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_ge_0_gc_1_leaf_core_u_qlate_q[568]),
        .rst_col(w_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[0])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r0c1_k0h1 (
        .cf_in(w_u_hb_idx_s_Q_r0c1_k0h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q_r0c1_k0h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q_r0c1_k0h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q_r0c1_k0h1_cs_out),
        .hid4({w_ge_0_gc_1_leaf_core_procdff_71532_Q[7:0], w_ge_0_gc_1_leaf_core_procdff_71531_Q[7:0], w_ge_0_gc_1_leaf_core_procdff_71530_Q[7:0], w_ge_0_gc_1_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_ge_0_gc_1_leaf_core_procdff_71524_Q[543:0]),
        .prdy(w_u_hb_idx_s_Q_r0c1_k0h1_prdy),
        .q_b(w_ge_0_gc_1_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_ge_0_gc_1_leaf_core_u_qlate_q[568]),
        .rst_col(w_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[0])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r0c1_k1h0 (
        .cf_out(w_u_hb_idx_s_Q_r0c1_k1h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q_r0c1_k1h0_cs_out),
        .hid4({w_ge_0_gc_1_leaf_core_procdff_71528_Q[7:0], w_ge_0_gc_1_leaf_core_procdff_71527_Q[7:0], w_ge_0_gc_1_leaf_core_procdff_71526_Q[7:0], w_ge_0_gc_1_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_ge_0_gc_1_leaf_core_procdff_71524_Q[1087:544]),
        .prdy(w_u_hb_idx_s_Q_r0c1_k1h0_prdy),
        .q_b(w_ge_0_gc_1_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_ge_0_gc_1_leaf_core_u_qlate_q[568]),
        .rst_col(w_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[1])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r0c1_k1h1 (
        .cf_in(w_u_hb_idx_s_Q_r0c1_k1h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q_r0c1_k1h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q_r0c1_k1h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q_r0c1_k1h1_cs_out),
        .hid4({w_ge_0_gc_1_leaf_core_procdff_71532_Q[7:0], w_ge_0_gc_1_leaf_core_procdff_71531_Q[7:0], w_ge_0_gc_1_leaf_core_procdff_71530_Q[7:0], w_ge_0_gc_1_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_ge_0_gc_1_leaf_core_procdff_71524_Q[1087:544]),
        .prdy(w_u_hb_idx_s_Q_r0c1_k1h1_prdy),
        .q_b(w_ge_0_gc_1_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_ge_0_gc_1_leaf_core_u_qlate_q[568]),
        .rst_col(w_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[1])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r0c1_k2h0 (
        .cf_out(w_u_hb_idx_s_Q_r0c1_k2h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q_r0c1_k2h0_cs_out),
        .hid4({w_ge_0_gc_1_leaf_core_procdff_71528_Q[7:0], w_ge_0_gc_1_leaf_core_procdff_71527_Q[7:0], w_ge_0_gc_1_leaf_core_procdff_71526_Q[7:0], w_ge_0_gc_1_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_ge_0_gc_1_leaf_core_procdff_71524_Q[1631:1088]),
        .prdy(w_u_hb_idx_s_Q_r0c1_k2h0_prdy),
        .q_b(w_ge_0_gc_1_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_ge_0_gc_1_leaf_core_u_qlate_q[568]),
        .rst_col(w_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[2])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r0c1_k2h1 (
        .cf_in(w_u_hb_idx_s_Q_r0c1_k2h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q_r0c1_k2h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q_r0c1_k2h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q_r0c1_k2h1_cs_out),
        .hid4({w_ge_0_gc_1_leaf_core_procdff_71532_Q[7:0], w_ge_0_gc_1_leaf_core_procdff_71531_Q[7:0], w_ge_0_gc_1_leaf_core_procdff_71530_Q[7:0], w_ge_0_gc_1_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_ge_0_gc_1_leaf_core_procdff_71524_Q[1631:1088]),
        .prdy(w_u_hb_idx_s_Q_r0c1_k2h1_prdy),
        .q_b(w_ge_0_gc_1_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_ge_0_gc_1_leaf_core_u_qlate_q[568]),
        .rst_col(w_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[2])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r0c1_k3h0 (
        .cf_out(w_u_hb_idx_s_Q_r0c1_k3h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q_r0c1_k3h0_cs_out),
        .hid4({w_ge_0_gc_1_leaf_core_procdff_71528_Q[7:0], w_ge_0_gc_1_leaf_core_procdff_71527_Q[7:0], w_ge_0_gc_1_leaf_core_procdff_71526_Q[7:0], w_ge_0_gc_1_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_ge_0_gc_1_leaf_core_procdff_71524_Q[2175:1632]),
        .prdy(w_u_hb_idx_s_Q_r0c1_k3h0_prdy),
        .q_b(w_ge_0_gc_1_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_ge_0_gc_1_leaf_core_u_qlate_q[568]),
        .rst_col(w_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[3])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q_r0c1_k3h1 (
        .cf_in(w_u_hb_idx_s_Q_r0c1_k3h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q_r0c1_k3h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q_r0c1_k3h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q_r0c1_k3h1_cs_out),
        .hid4({w_ge_0_gc_1_leaf_core_procdff_71532_Q[7:0], w_ge_0_gc_1_leaf_core_procdff_71531_Q[7:0], w_ge_0_gc_1_leaf_core_procdff_71530_Q[7:0], w_ge_0_gc_1_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_ge_0_gc_1_leaf_core_procdff_71524_Q[2175:1632]),
        .prdy(w_u_hb_idx_s_Q_r0c1_k3h1_prdy),
        .q_b(w_ge_0_gc_1_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_ge_0_gc_1_leaf_core_u_qlate_q[568]),
        .rst_col(w_ge_0_gc_1_leaf_core_g_delivered_reset_u_rr_rst_n[3])
    );
endmodule
