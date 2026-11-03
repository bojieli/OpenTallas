module hbm_arch_q_b000__physical_v1 (
    input  wire clk,
    input  wire arst_n,
    output wire rst_o_0,    
    input  wire [4986:0] L160_i,    
    input  wire [35:0] L188_i,    
    input  wire [180:0] L202_i,    
    input  wire [4097:0] L20_i,    
    input  wire [304:0] L65_i,    
    output wire [4127:0] L14_o,    
    output wire [4512:0] L161_o,    
    output wire [1389:0] L167_o,    
    output wire [1388:0] L168_o,    
    output wire [4098:0] L19_o,    
    output wire [1:0] L204_o,    
    output wire [1:0] L205_o,    
    input  wire [21:0] L101x1_i,    
    output wire [21:0] L101x1_o,    
    input  wire [5:0] L126x8_i,    
    output wire [5:0] L126x8_o,    
    input  wire [1615:0] L28x1_i,    
    output wire [1615:0] L28x1_o,    
    input  wire [1329:0] L36x1_i,    
    output wire [1329:0] L36x1_o,    
    input  wire [788:0] L42x1_i,    
    output wire [788:0] L42x1_o,    
    input  wire [788:0] L43x1_i,    
    output wire [788:0] L43x1_o,    
    input  wire [611:0] L51x1_i,    
    output wire [611:0] L51x1_o,    
    input  wire [610:0] L52x8_i,    
    output wire [610:0] L52x8_o,    
    input  wire [4:0] L732x4_i,    
    output wire [4:0] L732x4_o,    
    input  wire [3:0] L733x3_i,    
    output wire [3:0] L733x3_o,    
    input  wire [1:0] L734x7_i,    
    output wire [1:0] L734x7_o,    
    input  wire [274:0] L73x1_i,    
    output wire [274:0] L73x1_o    
);
    wire [4985:0] L160_i_q;
    wire L160_i_eq;
    wire [34:0] L188_i_q;
    wire L188_i_eq;
    wire [179:0] L202_i_q;
    wire L202_i_eq;
    wire [4096:0] L20_i_q;
    wire L20_i_eq;
    wire [303:0] L65_i_q;
    wire L65_i_eq;
    wire [19:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_71_54855_Y;
    wire [19:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_71_54857_Y;
    wire [31:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_77_54866_Y;
    wire [31:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_77_54868_Y;
    wire [31:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_77_54873_Y;
    wire [31:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_77_54875_Y;
    wire [31:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_77_54880_Y;
    wire [31:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_77_54882_Y;
    wire [31:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_77_54887_Y;
    wire [31:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_77_54889_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54897_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54899_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54905_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54907_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54913_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54915_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54921_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54923_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54953_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54955_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54961_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54963_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54969_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54971_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54977_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54979_Y;
    wire [19:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_91_54929_Y;
    wire [19:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_91_54930_Y;
    wire [19:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_91_54985_Y;
    wire [19:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_91_54986_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_92_54931_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_92_54987_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71688_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71693_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71698_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71703_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71708_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71713_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71721_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71726_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71731_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71736_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71741_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71746_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71752_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_ot_hbm_idx_score_quarter_static_h_sv_92_54933_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_ot_hbm_idx_score_quarter_static_h_sv_92_54989_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_gt_ot_hbm_idx_score_quarter_static_h_sv_76_54861_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_gt_ot_hbm_idx_score_quarter_static_h_sv_76_54862_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_120_54935_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_120_54991_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_139_54945_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_139_55001_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_153_54893_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_77_54864_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_77_54871_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_77_54878_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_77_54885_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54901_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54909_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54917_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54925_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54957_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54965_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54973_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54981_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_76_54863_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_77_54870_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_77_54877_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_77_54884_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_77_54891_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54903_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54911_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54919_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54927_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54959_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54967_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54975_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54983_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54900_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54908_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54916_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54924_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54956_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54964_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54972_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54980_Y;
    wire [19:0] w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_71_54853_Y;
    wire [19:0] w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_71_54854_Y;
    wire [19:0] w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_71_54856_Y;
    wire [31:0] w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54865_Y;
    wire [31:0] w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54867_Y;
    wire [31:0] w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54872_Y;
    wire [31:0] w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54874_Y;
    wire [31:0] w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54879_Y;
    wire [31:0] w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54881_Y;
    wire [31:0] w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54886_Y;
    wire [31:0] w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54888_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54896_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54904_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54912_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54920_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54952_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54960_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54968_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54976_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_92_54932_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_92_54988_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_nex_ot_hbm_idx_score_quarter_static_h_sv_77_54869_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_nex_ot_hbm_idx_score_quarter_static_h_sv_77_54876_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_nex_ot_hbm_idx_score_quarter_static_h_sv_77_54883_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_nex_ot_hbm_idx_score_quarter_static_h_sv_77_54890_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_procdff_71757_Q;
    wire [7:0] w_hb_idx_s_SW_scorer_procdff_71758_Q;
    wire [10:0] w_hb_idx_s_SW_scorer_procdff_71759_Q;
    wire [11:0] w_hb_idx_s_SW_scorer_procdff_71760_Q;
    wire [0:0] w_hb_idx_s_SW_scorer_procdff_71761_Q;
    wire [170:0] w_hb_idx_s_SW_scorer_procdff_71762_Q;
    wire [0:0] w_hb_idx_s_SW_scorer_procdff_71763_Q;
    wire [7:0] w_hb_idx_s_SW_scorer_procdff_71764_Q;
    wire [511:0] w_hb_idx_s_SW_scorer_procdff_71765_Q;
    wire [31:0] w_hb_idx_s_SW_scorer_procdff_71766_Q;
    wire [15:0] w_hb_idx_s_SW_scorer_procdff_71767_Q;
    wire [0:0] w_hb_idx_s_SW_scorer_procdff_71768_Q;
    wire [7:0] w_hb_idx_s_SW_scorer_procdff_71769_Q;
    wire [4395:0] w_hb_idx_s_SW_scorer_procdff_71770_Q;
    wire [0:0] w_hb_idx_s_SW_scorer_procmux_66627_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_procmux_66629_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_procmux_66633_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_procmux_66635_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_procmux_66639_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_procmux_66641_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_procmux_66645_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_procmux_66647_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_procmux_66651_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_procmux_66653_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_procmux_66659_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54902_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54910_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54918_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54926_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54958_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54966_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54974_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54982_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54898_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54906_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54914_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54922_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54954_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54962_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54970_Y;
    wire [11:0] w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54978_Y;
    wire [19:0] w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_91_54928_Y;
    wire [19:0] w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_91_54984_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54724_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54726_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54728_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54730_Y;
    wire [31:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71548_Q;
    wire [551:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71549_Q;
    wire [551:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71550_Q;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71551_Q;
    wire [567:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71552_Q;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71553_Q;
    wire [3:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71554_Q;
    wire [2175:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71555_Q;
    wire [29:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71556_Q;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71557_Q;
    wire [567:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71558_Q;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71559_Q;
    wire [3:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71560_Q;
    wire [2175:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71561_Q;
    wire [29:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71562_Q;
    wire [7:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71563_Q;
    wire [137:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__10176855;
    wire [137:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__6a12df79;
    wire [137:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__41fd8e31;
    wire [137:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__905746de;
    wire [7:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55671_Y;
    wire [7:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55672_Y;
    wire [7:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55673_Y;
    wire [7:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55674_Y;
    wire [7:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55675_Y;
    wire [7:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55676_Y;
    wire [7:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55677_Y;
    wire [7:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55678_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_auto_proc_dff_cc_220_proc_dff_71533_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_auto_proc_dff_cc_220_proc_dff_71538_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_auto_proc_dff_cc_220_proc_dff_71543_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_167_55670_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_logic_not_ot_hbm_idx_chunk_rt_h_sv_154_55666_Y;
    wire [31:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71508_Q;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71509_Q;
    wire [31:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71510_Q;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71511_Q;
    wire [31:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71512_Q;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71513_Q;
    wire [31:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71514_Q;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71515_Q;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71516_Q;
    wire [3:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71517_Q;
    wire [31:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71518_Q;
    wire [567:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71519_Q;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71520_Q;
    wire [7:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71521_Q;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71522_Q;
    wire [3:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71523_Q;
    wire [2175:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71524_Q;
    wire [7:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71525_Q;
    wire [7:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71526_Q;
    wire [7:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71527_Q;
    wire [7:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71528_Q;
    wire [7:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71529_Q;
    wire [7:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71530_Q;
    wire [7:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71531_Q;
    wire [7:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71532_Q;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71537_Q;
    wire [15:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71542_Q;
    wire [15:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71547_Q;
    wire [0:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_reduce_and_ot_hbm_idx_chunk_rt_h_sv_155_55667_Y;
    wire [0:0] w_u_hb_idx_s_Q2_r0c0_k0h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c0_k0h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c0_k0h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q2_r0c0_k0h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c0_k0h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c0_k0h1_prdy;
    wire [0:0] w_u_hb_idx_s_Q2_r0c0_k1h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c0_k1h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c0_k1h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q2_r0c0_k1h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c0_k1h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c0_k1h1_prdy;
    wire [0:0] w_u_hb_idx_s_Q2_r0c0_k2h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c0_k2h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c0_k2h0_prdy;
    wire [0:0] w_u_hb_idx_s_Q2_r0c0_k2h1_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c0_k2h1_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c0_k2h1_prdy;
    wire [0:0] w_u_hb_idx_s_Q2_r0c0_k3h0_cf_out;
    wire [31:0] w_u_hb_idx_s_Q2_r0c0_k3h0_cs_out;
    wire [1:0] w_u_hb_idx_s_Q2_r0c0_k3h0_prdy;
    wire [4:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n;
    wire [568:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_qlate_q;
    wire [4:0] w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_vl_q;
    wire [31:0] w_u_hcb_Q0_procdff_69249_Q;
    wire [4096:0] w_u_hcb_Q0_procdff_69250_Q;
    wire [4096:0] w_u_hcb_Q0_procdff_69251_Q;
    wire [0:0] w_u_hcb_Q0_u_c_auto_proc_dff_cc_220_proc_dff_71791_Y;
    wire [0:0] w_u_hcb_Q0_u_c_auto_proc_dff_cc_220_proc_dff_71796_Y;
    wire [0:0] w_u_hcb_Q0_u_c_auto_proc_dff_cc_220_proc_dff_71801_Y;
    wire [0:0] w_u_hcb_Q0_u_c_auto_proc_dff_cc_220_proc_dff_71806_Y;
    wire [0:0] w_u_hcb_Q0_u_c_auto_proc_dff_cc_220_proc_dff_71818_Y;
    wire [0:0] w_u_hcb_Q0_u_c_eq_ot_hbm_hc_bankq_static_sv_50_54435_Y;
    wire [0:0] w_u_hcb_Q0_u_c_eq_ot_hbm_hc_bankq_static_sv_50_54437_Y;
    wire [0:0] w_u_hcb_Q0_u_c_eq_ot_hbm_hc_bankq_static_sv_50_54439_Y;
    wire [0:0] w_u_hcb_Q0_u_c_logic_and_ot_hbm_hc_bankq_static_sv_50_54436_Y;
    wire [0:0] w_u_hcb_Q0_u_c_logic_and_ot_hbm_hc_bankq_static_sv_50_54438_Y;
    wire [0:0] w_u_hcb_Q0_u_c_logic_and_ot_hbm_hc_bankq_static_sv_50_54440_Y;
    wire [0:0] w_u_hcb_Q0_u_c_logic_and_ot_hbm_hc_bankq_static_sv_61_54477_Y;
    wire [0:0] w_u_hcb_Q0_u_c_logic_not_ot_hbm_hc_bankq_static_sv_47_54432_Y;
    wire [0:0] w_u_hcb_Q0_u_c_logic_not_ot_hbm_hc_bankq_static_sv_60_54476_Y;
    wire [0:0] w_u_hcb_Q0_u_c_logic_not_ot_hbm_hc_bankq_static_sv_82_54479_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procdff_71786_Q;
    wire [7:0] w_u_hcb_Q0_u_c_procdff_71787_Q;
    wire [9:0] w_u_hcb_Q0_u_c_procdff_71788_Q;
    wire [9:0] w_u_hcb_Q0_u_c_procdff_71789_Q;
    wire [4095:0] w_u_hcb_Q0_u_c_procdff_71790_Q;
    wire [0:0] w_u_hcb_Q0_u_c_procdff_71795_Q;
    wire [0:0] w_u_hcb_Q0_u_c_procdff_71800_Q;
    wire [0:0] w_u_hcb_Q0_u_c_procdff_71805_Q;
    wire [0:0] w_u_hcb_Q0_u_c_procdff_71810_Q;
    wire [0:0] w_u_hcb_Q0_u_c_procdff_71811_Q;
    wire [31:0] w_u_hcb_Q0_u_c_procdff_71812_Q;
    wire [1:0] w_u_hcb_Q0_u_c_procdff_71813_Q;
    wire [255:0] w_u_hcb_Q0_u_c_procdff_71814_Q;
    wire [767:0] w_u_hcb_Q0_u_c_procdff_71815_Q;
    wire [1023:0] w_u_hcb_Q0_u_c_procdff_71816_Q;
    wire [31:0] w_u_hcb_Q0_u_c_procdff_71817_Q;
    wire [0:0] w_u_hcb_Q0_u_c_procdff_71822_Q;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66661_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66663_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66665_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66667_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66669_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66671_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66673_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66675_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66677_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66679_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66681_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66683_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66685_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66687_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66689_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66691_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66693_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66695_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66697_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66699_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66701_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66703_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66705_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66707_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66709_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66711_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66713_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66715_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66717_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66719_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66721_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66723_Y;
    wire [0:0] w_u_hcb_Q0_u_c_procmux_66725_Y;
    wire [255:0] w_u_hcb_Q0_u_c_procmux_66727_Y;
    wire [255:0] w_u_hcb_Q0_u_c_procmux_66729_Y;
    wire [255:0] w_u_hcb_Q0_u_c_procmux_66731_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54443_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54444_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54445_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54446_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54447_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54448_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54449_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54450_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54451_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54452_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54453_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54454_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54455_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54456_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54457_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54458_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54459_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54460_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54461_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54462_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54463_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54464_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54465_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54466_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54467_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54468_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54469_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54470_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54471_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54472_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54473_Y;
    wire [0:0] w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54474_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_auto_proc_dff_cc_220_proc_dff_71776_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_auto_proc_dff_cc_220_proc_dff_71781_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54672_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54674_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54676_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54678_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54680_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54682_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54684_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54686_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54688_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54690_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54692_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54694_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54696_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54698_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54700_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54702_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54704_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54706_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54708_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54710_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54712_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54714_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54716_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54718_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54673_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54675_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54677_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54679_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54681_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54683_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54685_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54687_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54689_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54691_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54693_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54695_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54697_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54699_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54701_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54703_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54705_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54707_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54709_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54711_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54713_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54715_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54717_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54719_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_logic_not_ot_hbm_hc_bank_static_sv_59_54669_Y;
    wire [1:0] w_u_hcb_Q0_u_c_u_b_procdff_71773_Q;
    wire [9:0] w_u_hcb_Q0_u_c_u_b_procdff_71774_Q;
    wire [1023:0] w_u_hcb_Q0_u_c_u_b_procdff_71775_Q;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_procdff_71780_Q;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_procdff_71785_Q;
    wire [1:0] w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_auto_proc_dff_cc_220_proc_dff_71640_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_auto_proc_dff_cc_220_proc_dff_71660_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_auto_proc_dff_cc_220_proc_dff_71665_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_auto_proc_dff_cc_220_proc_dff_71670_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_auto_proc_dff_cc_220_proc_dff_71675_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_auto_proc_dff_cc_220_proc_dff_71680_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_669_55081_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55088_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55090_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55092_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55094_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55096_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55098_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55100_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55102_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55104_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55106_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55108_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55110_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55112_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55114_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55116_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55118_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55120_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55122_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55124_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55126_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55128_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55130_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55132_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55134_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55136_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55138_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55140_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55142_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55144_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55146_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55148_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55150_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55152_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55154_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55156_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55158_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55160_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55162_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55164_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55166_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55168_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55170_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55172_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55174_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55176_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55178_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55180_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55182_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55184_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55186_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55188_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55190_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55192_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55194_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55196_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55198_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55200_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55202_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55204_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55206_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55208_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55210_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55212_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55214_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55216_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55218_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55220_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55222_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55224_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55226_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55228_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55230_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55232_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55234_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55236_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55238_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55240_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55242_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55244_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55246_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55248_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55250_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55252_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55254_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55256_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55258_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55260_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55262_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55264_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55266_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55268_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55270_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55272_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55274_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55276_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55278_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55280_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55282_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55284_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55286_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55288_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55290_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55292_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55294_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55296_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55298_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55300_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55302_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55304_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55306_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55308_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55310_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55312_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55314_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55316_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55318_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55320_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55322_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55324_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55326_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55328_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55330_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55332_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55334_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55336_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55338_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55340_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55342_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_not_ot_hdc_v41x_hcp_sv_666_55079_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_not_ot_hdc_v41x_hcp_sv_669_55080_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_not_ot_hdc_v41x_hcp_sv_741_55344_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_logic_or_ot_hdc_v41x_hcp_sv_672_55082_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55087_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55089_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55091_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55093_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55095_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55097_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55099_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55101_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55103_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55105_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55107_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55109_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55111_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55113_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55115_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55117_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55119_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55121_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55123_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55125_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55127_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55129_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55131_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55133_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55135_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55137_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55139_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55141_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55143_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55145_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55147_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55149_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55151_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55153_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55155_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55157_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55159_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55161_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55163_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55165_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55167_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55169_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55171_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55173_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55175_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55177_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55179_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55181_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55183_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55185_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55187_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55189_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55191_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55193_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55195_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55197_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55199_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55201_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55203_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55205_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55207_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55209_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55211_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55213_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55215_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55217_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55219_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55221_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55223_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55225_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55227_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55229_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55231_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55233_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55235_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55237_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55239_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55241_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55243_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55245_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55247_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55249_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55251_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55253_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55255_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55257_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55259_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55261_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55263_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55265_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55267_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55269_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55271_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55273_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55275_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55277_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55279_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55281_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55283_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55285_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55287_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55289_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55291_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55293_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55295_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55297_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55299_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55301_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55303_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55305_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55307_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55309_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55311_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55313_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55315_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55317_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55319_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55321_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55323_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55325_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55327_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55329_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55331_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55333_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55335_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55337_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55339_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55341_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_procdff_71644_Q;
    wire [127:0] w_u_hcb_Q0_u_c_u_b_u_st_procdff_71645_Q;
    wire [127:0] w_u_hcb_Q0_u_c_u_b_u_st_procdff_71646_Q;
    wire [31:0] w_u_hcb_Q0_u_c_u_b_u_st_procdff_71647_Q;
    wire [9:0] w_u_hcb_Q0_u_c_u_b_u_st_procdff_71648_Q;
    wire [9:0] w_u_hcb_Q0_u_c_u_b_u_st_procdff_71649_Q;
    wire [31:0] w_u_hcb_Q0_u_c_u_b_u_st_procdff_71650_Q;
    wire [28:0] w_u_hcb_Q0_u_c_u_b_u_st_procdff_71651_Q;
    wire [28:0] w_u_hcb_Q0_u_c_u_b_u_st_procdff_71652_Q;
    wire [28:0] w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q;
    wire [28:0] w_u_hcb_Q0_u_c_u_b_u_st_procdff_71654_Q;
    wire [28:0] w_u_hcb_Q0_u_c_u_b_u_st_procdff_71655_Q;
    wire [28:0] w_u_hcb_Q0_u_c_u_b_u_st_procdff_71656_Q;
    wire [28:0] w_u_hcb_Q0_u_c_u_b_u_st_procdff_71657_Q;
    wire [28:0] w_u_hcb_Q0_u_c_u_b_u_st_procdff_71658_Q;
    wire [28:0] w_u_hcb_Q0_u_c_u_b_u_st_procdff_71659_Q;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_procdff_71664_Q;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_procdff_71669_Q;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_procdff_71674_Q;
    wire [8:0] w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_procdff_71684_Q;
    wire [0:0] w_u_hcb_Q0_u_c_u_b_u_st_reduce_or_ot_hdc_v41x_hcp_sv_750_55345_Y;
    wire [0:0] w_u_hcb_Q0_u_c_u_rst_rst_n;
    wire [1:0] w_u_hcb_Q0_ot_hbm_hc_bank128_pair0_fault;
    wire [511:0] w_u_hcb_Q0_ot_hbm_hc_bank128_pair0_sum_out;
    wire [1:0] w_u_hcb_Q0_ot_hbm_hc_bank128_pair1_fault;
    wire [511:0] w_u_hcb_Q0_ot_hbm_hc_bank128_pair1_sum_out;
    wire [1:0] w_u_hcb_Q0_ot_hbm_hc_bank128_pair2_fault;
    wire [511:0] w_u_hcb_Q0_ot_hbm_hc_bank128_pair2_sum_out;
    wire [1:0] w_u_hcb_Q0_ot_hbm_hc_bank128_pair3_fault;
    wire [511:0] w_u_hcb_Q0_ot_hbm_hc_bank128_pair3_sum_out;
    wire [1:0] w_u_hcb_Q0_ot_hbm_hc_bank128_pair4_fault;
    wire [511:0] w_u_hcb_Q0_ot_hbm_hc_bank128_pair4_sum_out;
    wire [1:0] w_u_hcb_Q0_ot_hbm_hc_bank128_pair5_fault;
    wire [511:0] w_u_hcb_Q0_ot_hbm_hc_bank128_pair5_sum_out;
    wire [1:0] w_u_hcb_Q0_ot_hbm_hc_bank128_pair6_fault;
    wire [511:0] w_u_hcb_Q0_ot_hbm_hc_bank128_pair6_sum_out;
    wire [1:0] w_u_hcb_Q0_ot_hbm_hc_bank128_pair7_fault;
    wire [511:0] w_u_hcb_Q0_ot_hbm_hc_bank128_pair7_sum_out;
    wire [21:0] L101x1_o_s0;
    wire [21:0] L101x1_o_s1;
    wire [5:0] L126x8_o_s0;
    wire [5:0] L126x8_o_s1;
    wire [1615:0] L28x1_o_s0;
    wire [1615:0] L28x1_o_s1;
    wire [1615:0] L28x1_o_s2;
    wire [1329:0] L36x1_o_s0;
    wire [1329:0] L36x1_o_s1;
    wire [1329:0] L36x1_o_s2;
    wire [788:0] L42x1_o_s0;
    wire [788:0] L42x1_o_s1;
    wire [788:0] L43x1_o_s0;
    wire [788:0] L43x1_o_s1;
    wire [611:0] L51x1_o_s0;
    wire [611:0] L51x1_o_s1;
    wire [610:0] L52x8_o_s0;
    wire [610:0] L52x8_o_s1;
    wire [4:0] L732x4_o_s0;
    wire [3:0] L733x3_o_s0;
    wire [1:0] L734x7_o_s0;
    wire [1:0] L734x7_o_s1;
    wire [274:0] L73x1_o_s0;
    wire [274:0] L73x1_o_s1;
     
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
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_rl_5), .q(rst_n_t11));   
    wire rst_rl_7;
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_rl_0), .q(rst_rl_7));   
    wire rst_rl_8;
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_rl_7), .q(rst_rl_8));   
    wire rst_rl_9;
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_rl_8), .q(rst_rl_9));   
    wire rst_rl_10;
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_9), .q(rst_rl_10));   
    wire rst_rl_11;
    ot_dp_rrelay u_rrl_11 (.clk(clk), .d(rst_rl_10), .q(rst_rl_11));   
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_11), .q(rst_n_t10));   
    wire rst_rl_13;
    ot_dp_rrelay u_rrl_13 (.clk(clk), .d(rst_rl_8), .q(rst_rl_13));   
    wire rst_rl_14;
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_13), .q(rst_rl_14));   
    wire rst_rl_15;
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_14), .q(rst_rl_15));   
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_15), .q(rst_n_t8));   
    wire rst_rl_17;
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_13), .q(rst_rl_17));   
    wire rst_rl_18;
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_rl_17), .q(rst_rl_18));   
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_18), .q(rst_n_t6));   
    wire rst_rl_20;
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_17), .q(rst_rl_20));   
    ot_dp_rrelay u_rrl_21 (.clk(clk), .d(rst_rl_20), .q(rst_n_t4));   
    ot_dp_rrelay u_rrl_22 (.clk(clk), .d(rst_rl_20), .q(rst_n_t2));   
    wire rst_rl_23;
    ot_dp_rrelay u_rrl_23 (.clk(clk), .d(rst_rl_0), .q(rst_rl_23));   
    wire rst_rl_24;
    ot_dp_rrelay u_rrl_24 (.clk(clk), .d(rst_rl_23), .q(rst_rl_24));   
    wire rst_rl_25;
    ot_dp_rrelay u_rrl_25 (.clk(clk), .d(rst_rl_24), .q(rst_rl_25));   
    wire rst_rl_26;
    ot_dp_rrelay u_rrl_26 (.clk(clk), .d(rst_rl_25), .q(rst_rl_26));   
    wire rst_rl_27;
    ot_dp_rrelay u_rrl_27 (.clk(clk), .d(rst_rl_26), .q(rst_rl_27));   
    ot_dp_rrelay u_rrl_28 (.clk(clk), .d(rst_rl_27), .q(rst_n_t28));   
    wire rst_rl_29;
    ot_dp_rrelay u_rrl_29 (.clk(clk), .d(rst_rl_23), .q(rst_rl_29));   
    wire rst_rl_30;
    ot_dp_rrelay u_rrl_30 (.clk(clk), .d(rst_rl_29), .q(rst_rl_30));   
    wire rst_rl_31;
    ot_dp_rrelay u_rrl_31 (.clk(clk), .d(rst_rl_30), .q(rst_rl_31));   
    wire rst_rl_32;
    ot_dp_rrelay u_rrl_32 (.clk(clk), .d(rst_rl_31), .q(rst_rl_32));   
    ot_dp_rrelay u_rrl_33 (.clk(clk), .d(rst_rl_32), .q(rst_o_0));   
    ot_dp_rrelay u_rrl_33_t (.clk(clk), .d(rst_rl_32), .q(rst_n_t22));   
    wire rst_rl_34;
    ot_dp_rrelay u_rrl_34 (.clk(clk), .d(rst_rl_23), .q(rst_rl_34));   
    wire rst_rl_35;
    ot_dp_rrelay u_rrl_35 (.clk(clk), .d(rst_rl_34), .q(rst_rl_35));   
    wire rst_rl_36;
    ot_dp_rrelay u_rrl_36 (.clk(clk), .d(rst_rl_35), .q(rst_rl_36));   
    wire rst_rl_37;
    ot_dp_rrelay u_rrl_37 (.clk(clk), .d(rst_rl_36), .q(rst_rl_37));   
    ot_dp_rrelay u_rrl_38 (.clk(clk), .d(rst_rl_37), .q(rst_n_t27));   
    wire rst_rl_39;
    ot_dp_rrelay u_rrl_39 (.clk(clk), .d(rst_rl_34), .q(rst_rl_39));   
    wire rst_rl_40;
    ot_dp_rrelay u_rrl_40 (.clk(clk), .d(rst_rl_39), .q(rst_rl_40));   
    wire rst_rl_41;
    ot_dp_rrelay u_rrl_41 (.clk(clk), .d(rst_rl_40), .q(rst_rl_41));   
    ot_dp_rrelay u_rrl_42 (.clk(clk), .d(rst_rl_41), .q(rst_n_t26));   
    wire rst_rl_43;
    ot_dp_rrelay u_rrl_43 (.clk(clk), .d(rst_rl_39), .q(rst_rl_43));   
    wire rst_rl_44;
    ot_dp_rrelay u_rrl_44 (.clk(clk), .d(rst_rl_43), .q(rst_rl_44));   
    ot_dp_rrelay u_rrl_45 (.clk(clk), .d(rst_rl_44), .q(rst_n_t25));   
    wire rst_rl_46;
    ot_dp_rrelay u_rrl_46 (.clk(clk), .d(rst_rl_43), .q(rst_rl_46));   
    ot_dp_rrelay u_rrl_47 (.clk(clk), .d(rst_rl_46), .q(rst_n_t24));   
    ot_dp_rrelay u_rrl_48 (.clk(clk), .d(rst_rl_46), .q(rst_n_t23));   
    wire rst_rl_49;
    ot_dp_rrelay u_rrl_49 (.clk(clk), .d(rst_root_n), .q(rst_rl_49));   
    wire rst_rl_50;
    ot_dp_rrelay u_rrl_50 (.clk(clk), .d(rst_rl_49), .q(rst_rl_50));   
    wire rst_rl_51;
    ot_dp_rrelay u_rrl_51 (.clk(clk), .d(rst_rl_50), .q(rst_rl_51));   
    wire rst_rl_52;
    ot_dp_rrelay u_rrl_52 (.clk(clk), .d(rst_rl_51), .q(rst_rl_52));   
    wire rst_rl_53;
    ot_dp_rrelay u_rrl_53 (.clk(clk), .d(rst_rl_52), .q(rst_rl_53));   
    wire rst_rl_54;
    ot_dp_rrelay u_rrl_54 (.clk(clk), .d(rst_rl_53), .q(rst_rl_54));   
    ot_dp_rrelay u_rrl_55 (.clk(clk), .d(rst_rl_54), .q(rst_n_t13));   
    wire rst_rl_56;
    ot_dp_rrelay u_rrl_56 (.clk(clk), .d(rst_rl_51), .q(rst_rl_56));   
    wire rst_rl_57;
    ot_dp_rrelay u_rrl_57 (.clk(clk), .d(rst_rl_56), .q(rst_rl_57));   
    wire rst_rl_58;
    ot_dp_rrelay u_rrl_58 (.clk(clk), .d(rst_rl_57), .q(rst_rl_58));   
    ot_dp_rrelay u_rrl_59 (.clk(clk), .d(rst_rl_58), .q(rst_n_t12));   
    wire rst_rl_60;
    ot_dp_rrelay u_rrl_60 (.clk(clk), .d(rst_rl_51), .q(rst_rl_60));   
    wire rst_rl_61;
    ot_dp_rrelay u_rrl_61 (.clk(clk), .d(rst_rl_60), .q(rst_rl_61));   
    wire rst_rl_62;
    ot_dp_rrelay u_rrl_62 (.clk(clk), .d(rst_rl_61), .q(rst_rl_62));   
    ot_dp_rrelay u_rrl_63 (.clk(clk), .d(rst_rl_62), .q(rst_n_t29));   
    ot_dp_rrelay u_rrl_64 (.clk(clk), .d(rst_rl_62), .q(rst_n_t30));   
    wire rst_rl_65;
    ot_dp_rrelay u_rrl_65 (.clk(clk), .d(rst_rl_51), .q(rst_rl_65));   
    wire rst_rl_66;
    ot_dp_rrelay u_rrl_66 (.clk(clk), .d(rst_rl_65), .q(rst_rl_66));   
    wire rst_rl_67;
    ot_dp_rrelay u_rrl_67 (.clk(clk), .d(rst_rl_66), .q(rst_rl_67));   
    ot_dp_rrelay u_rrl_68 (.clk(clk), .d(rst_rl_67), .q(rst_n_t14));   
    wire rst_rl_69;
    ot_dp_rrelay u_rrl_69 (.clk(clk), .d(rst_rl_51), .q(rst_rl_69));   
    wire rst_rl_70;
    ot_dp_rrelay u_rrl_70 (.clk(clk), .d(rst_rl_69), .q(rst_rl_70));   
    wire rst_rl_71;
    ot_dp_rrelay u_rrl_71 (.clk(clk), .d(rst_rl_70), .q(rst_rl_71));   
    ot_dp_rrelay u_rrl_72 (.clk(clk), .d(rst_rl_71), .q(rst_n_t16));   
    wire rst_rl_73;
    ot_dp_rrelay u_rrl_73 (.clk(clk), .d(rst_rl_51), .q(rst_rl_73));   
    wire rst_rl_74;
    ot_dp_rrelay u_rrl_74 (.clk(clk), .d(rst_rl_73), .q(rst_rl_74));   
    wire rst_rl_75;
    ot_dp_rrelay u_rrl_75 (.clk(clk), .d(rst_rl_74), .q(rst_rl_75));   
    ot_dp_rrelay u_rrl_76 (.clk(clk), .d(rst_rl_75), .q(rst_n_t18));   
    wire rst_rl_77;
    ot_dp_rrelay u_rrl_77 (.clk(clk), .d(rst_root_n), .q(rst_rl_77));   
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
    ot_dp_rrelay u_rrl_83 (.clk(clk), .d(rst_rl_82), .q(rst_n_t9));   
    wire rst_rl_84;
    ot_dp_rrelay u_rrl_84 (.clk(clk), .d(rst_rl_78), .q(rst_rl_84));   
    wire rst_rl_85;
    ot_dp_rrelay u_rrl_85 (.clk(clk), .d(rst_rl_84), .q(rst_rl_85));   
    wire rst_rl_86;
    ot_dp_rrelay u_rrl_86 (.clk(clk), .d(rst_rl_85), .q(rst_rl_86));   
    wire rst_rl_87;
    ot_dp_rrelay u_rrl_87 (.clk(clk), .d(rst_rl_86), .q(rst_rl_87));   
    ot_dp_rrelay u_rrl_88 (.clk(clk), .d(rst_rl_87), .q(rst_n_t0));   
    wire rst_rl_89;
    ot_dp_rrelay u_rrl_89 (.clk(clk), .d(rst_root_n), .q(rst_rl_89));   
    wire rst_rl_90;
    ot_dp_rrelay u_rrl_90 (.clk(clk), .d(rst_rl_89), .q(rst_rl_90));   
    wire rst_rl_91;
    ot_dp_rrelay u_rrl_91 (.clk(clk), .d(rst_rl_90), .q(rst_rl_91));   
    wire rst_rl_92;
    ot_dp_rrelay u_rrl_92 (.clk(clk), .d(rst_rl_91), .q(rst_rl_92));   
    wire rst_rl_93;
    ot_dp_rrelay u_rrl_93 (.clk(clk), .d(rst_rl_92), .q(rst_rl_93));   
    wire rst_rl_94;
    ot_dp_rrelay u_rrl_94 (.clk(clk), .d(rst_rl_93), .q(rst_rl_94));   
    ot_dp_rrelay u_rrl_95 (.clk(clk), .d(rst_rl_94), .q(rst_n_t15));   
    wire rst_rl_96;
    ot_dp_rrelay u_rrl_96 (.clk(clk), .d(rst_rl_91), .q(rst_rl_96));   
    wire rst_rl_97;
    ot_dp_rrelay u_rrl_97 (.clk(clk), .d(rst_rl_96), .q(rst_rl_97));   
    wire rst_rl_98;
    ot_dp_rrelay u_rrl_98 (.clk(clk), .d(rst_rl_97), .q(rst_rl_98));   
    ot_dp_rrelay u_rrl_99 (.clk(clk), .d(rst_rl_98), .q(rst_n_t20));   
    wire rst_rl_100;
    ot_dp_rrelay u_rrl_100 (.clk(clk), .d(rst_root_n), .q(rst_rl_100));   
    wire rst_rl_101;
    ot_dp_rrelay u_rrl_101 (.clk(clk), .d(rst_rl_100), .q(rst_rl_101));   
    wire rst_rl_102;
    ot_dp_rrelay u_rrl_102 (.clk(clk), .d(rst_rl_101), .q(rst_rl_102));   
    wire rst_rl_103;
    ot_dp_rrelay u_rrl_103 (.clk(clk), .d(rst_rl_102), .q(rst_rl_103));   
    wire rst_rl_104;
    ot_dp_rrelay u_rrl_104 (.clk(clk), .d(rst_rl_103), .q(rst_rl_104));   
    wire rst_rl_105;
    ot_dp_rrelay u_rrl_105 (.clk(clk), .d(rst_rl_104), .q(rst_rl_105));   
    ot_dp_rrelay u_rrl_106 (.clk(clk), .d(rst_rl_105), .q(rst_n_t7));   
    wire rst_rl_107;
    ot_dp_rrelay u_rrl_107 (.clk(clk), .d(rst_root_n), .q(rst_rl_107));   
    wire rst_rl_108;
    ot_dp_rrelay u_rrl_108 (.clk(clk), .d(rst_rl_107), .q(rst_rl_108));   
    wire rst_rl_109;
    ot_dp_rrelay u_rrl_109 (.clk(clk), .d(rst_rl_108), .q(rst_rl_109));   
    wire rst_rl_110;
    ot_dp_rrelay u_rrl_110 (.clk(clk), .d(rst_rl_109), .q(rst_rl_110));   
    wire rst_rl_111;
    ot_dp_rrelay u_rrl_111 (.clk(clk), .d(rst_rl_110), .q(rst_rl_111));   
    wire rst_rl_112;
    ot_dp_rrelay u_rrl_112 (.clk(clk), .d(rst_rl_111), .q(rst_rl_112));   
    ot_dp_rrelay u_rrl_113 (.clk(clk), .d(rst_rl_112), .q(rst_n_t17));   
    wire rst_rl_114;
    ot_dp_rrelay u_rrl_114 (.clk(clk), .d(rst_root_n), .q(rst_rl_114));   
    wire rst_rl_115;
    ot_dp_rrelay u_rrl_115 (.clk(clk), .d(rst_rl_114), .q(rst_rl_115));   
    wire rst_rl_116;
    ot_dp_rrelay u_rrl_116 (.clk(clk), .d(rst_rl_115), .q(rst_rl_116));   
    wire rst_rl_117;
    ot_dp_rrelay u_rrl_117 (.clk(clk), .d(rst_rl_116), .q(rst_rl_117));   
    wire rst_rl_118;
    ot_dp_rrelay u_rrl_118 (.clk(clk), .d(rst_rl_117), .q(rst_rl_118));   
    wire rst_rl_119;
    ot_dp_rrelay u_rrl_119 (.clk(clk), .d(rst_rl_118), .q(rst_rl_119));   
    ot_dp_rrelay u_rrl_120 (.clk(clk), .d(rst_rl_119), .q(rst_n_t5));   
    wire rst_rl_121;
    ot_dp_rrelay u_rrl_121 (.clk(clk), .d(rst_root_n), .q(rst_rl_121));   
    wire rst_rl_122;
    ot_dp_rrelay u_rrl_122 (.clk(clk), .d(rst_rl_121), .q(rst_rl_122));   
    wire rst_rl_123;
    ot_dp_rrelay u_rrl_123 (.clk(clk), .d(rst_rl_122), .q(rst_rl_123));   
    wire rst_rl_124;
    ot_dp_rrelay u_rrl_124 (.clk(clk), .d(rst_rl_123), .q(rst_rl_124));   
    wire rst_rl_125;
    ot_dp_rrelay u_rrl_125 (.clk(clk), .d(rst_rl_124), .q(rst_rl_125));   
    wire rst_rl_126;
    ot_dp_rrelay u_rrl_126 (.clk(clk), .d(rst_rl_125), .q(rst_rl_126));   
    ot_dp_rrelay u_rrl_127 (.clk(clk), .d(rst_rl_126), .q(rst_n_t19));   
    wire rst_rl_128;
    ot_dp_rrelay u_rrl_128 (.clk(clk), .d(rst_root_n), .q(rst_rl_128));   
    wire rst_rl_129;
    ot_dp_rrelay u_rrl_129 (.clk(clk), .d(rst_rl_128), .q(rst_rl_129));   
    wire rst_rl_130;
    ot_dp_rrelay u_rrl_130 (.clk(clk), .d(rst_rl_129), .q(rst_rl_130));   
    wire rst_rl_131;
    ot_dp_rrelay u_rrl_131 (.clk(clk), .d(rst_rl_130), .q(rst_rl_131));   
    wire rst_rl_132;
    ot_dp_rrelay u_rrl_132 (.clk(clk), .d(rst_rl_131), .q(rst_rl_132));   
    wire rst_rl_133;
    ot_dp_rrelay u_rrl_133 (.clk(clk), .d(rst_rl_132), .q(rst_rl_133));   
    ot_dp_rrelay u_rrl_134 (.clk(clk), .d(rst_rl_133), .q(rst_n_t3));   
    wire rst_rl_135;
    ot_dp_rrelay u_rrl_135 (.clk(clk), .d(rst_root_n), .q(rst_rl_135));   
    wire rst_rl_136;
    ot_dp_rrelay u_rrl_136 (.clk(clk), .d(rst_rl_135), .q(rst_rl_136));   
    wire rst_rl_137;
    ot_dp_rrelay u_rrl_137 (.clk(clk), .d(rst_rl_136), .q(rst_rl_137));   
    wire rst_rl_138;
    ot_dp_rrelay u_rrl_138 (.clk(clk), .d(rst_rl_137), .q(rst_rl_138));   
    wire rst_rl_139;
    ot_dp_rrelay u_rrl_139 (.clk(clk), .d(rst_rl_138), .q(rst_rl_139));   
    wire rst_rl_140;
    ot_dp_rrelay u_rrl_140 (.clk(clk), .d(rst_rl_139), .q(rst_rl_140));   
    ot_dp_rrelay u_rrl_141 (.clk(clk), .d(rst_rl_140), .q(rst_n_t21));   
    wire rst_rl_142;
    ot_dp_rrelay u_rrl_142 (.clk(clk), .d(rst_root_n), .q(rst_rl_142));   
    wire rst_rl_143;
    ot_dp_rrelay u_rrl_143 (.clk(clk), .d(rst_rl_142), .q(rst_rl_143));   
    wire rst_rl_144;
    ot_dp_rrelay u_rrl_144 (.clk(clk), .d(rst_rl_143), .q(rst_rl_144));   
    wire rst_rl_145;
    ot_dp_rrelay u_rrl_145 (.clk(clk), .d(rst_rl_144), .q(rst_rl_145));   
    wire rst_rl_146;
    ot_dp_rrelay u_rrl_146 (.clk(clk), .d(rst_rl_145), .q(rst_rl_146));   
    wire rst_rl_147;
    ot_dp_rrelay u_rrl_147 (.clk(clk), .d(rst_rl_146), .q(rst_rl_147));   
    ot_dp_rrelay u_rrl_148 (.clk(clk), .d(rst_rl_147), .q(rst_n_t1));   
    wire rst_n = rst_n_t11;
    ot_dp_st #(.W(4986)) u_bin_L160_i (.clk(clk), .rst_n(rst_n), .d(L160_i[4985:0]), .ea(L160_i[4986]), .q(L160_i_q), .eq(L160_i_eq));
    ot_dp_st #(.W(35)) u_bin_L188_i (.clk(clk), .rst_n(rst_n), .d(L188_i[34:0]), .ea(L188_i[35]), .q(L188_i_q), .eq(L188_i_eq));
    ot_dp_st #(.W(180)) u_bin_L202_i (.clk(clk), .rst_n(rst_n), .d(L202_i[179:0]), .ea(L202_i[180]), .q(L202_i_q), .eq(L202_i_eq));
    ot_dp_st #(.W(4097)) u_bin_L20_i (.clk(clk), .rst_n(rst_n), .d(L20_i[4096:0]), .ea(L20_i[4097]), .q(L20_i_q), .eq(L20_i_eq));
    ot_dp_st #(.W(304)) u_bin_L65_i (.clk(clk), .rst_n(rst_n), .d(L65_i[303:0]), .ea(L65_i[304]), .q(L65_i_q), .eq(L65_i_eq));
    ot_dp_st #(.W(4127)) u_bout_L14_o (.clk(clk), .rst_n(rst_n), .d({w_u_hcb_Q0_u_c_procdff_71790_Q[1320:0], w_u_hcb_Q0_u_c_procdff_71789_Q[9:0], w_u_hcb_Q0_u_c_procdff_71788_Q[9:0], w_u_hcb_Q0_u_c_procdff_71787_Q[7:0], w_u_hcb_Q0_u_c_procdff_71786_Q[0], w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0], w_hb_idx_s_SW_scorer_procmux_66659_Y[0], w_hb_idx_s_SW_scorer_procdff_71770_Q[4395:3308], w_hb_idx_s_SW_scorer_procdff_71770_Q[3296:2209], w_hb_idx_s_SW_scorer_procdff_71768_Q[0], w_hb_idx_s_SW_scorer_procdff_71767_Q[15:0], w_hb_idx_s_SW_scorer_procdff_71766_Q[31:0], w_hb_idx_s_SW_scorer_procdff_71765_Q[511:0], w_hb_idx_s_SW_scorer_procdff_71764_Q[7:0], w_hb_idx_s_SW_scorer_procdff_71763_Q[0], w_hb_idx_s_SW_scorer_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54980_Y[0], w_hb_idx_s_SW_scorer_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54972_Y[0], w_hb_idx_s_SW_scorer_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54964_Y[0], w_hb_idx_s_SW_scorer_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54956_Y[0], w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54983_Y[0], w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54975_Y[0], w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54967_Y[0], w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54959_Y[0], w_hb_idx_s_SW_scorer_ge_ot_hbm_idx_score_quarter_static_h_sv_92_54989_Y[0], w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_91_54986_Y[19:0]}), .ea(rst_n), .q(L14_o[4126:0]), .eq(L14_o[4127]));
    ot_dp_st #(.W(4512)) u_bout_L161_o (.clk(clk), .rst_n(rst_n), .d({w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_qlate_q[568:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[3], w_u_hb_idx_s_Q2_r0c0_k3h0_cs_out[31:0], w_u_hb_idx_s_Q2_r0c0_k3h0_cf_out[0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71532_Q[7:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71531_Q[7:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71530_Q[7:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71529_Q[7:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71524_Q[2175:1632], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71556_Q[29:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71555_Q[2175:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71554_Q[3:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71553_Q[0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71552_Q[567:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71551_Q[0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71549_Q[551:0], w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0]}), .ea(rst_n), .q(L161_o[4511:0]), .eq(L161_o[4512]));
    ot_dp_st #(.W(1389)) u_bout_L167_o (.clk(clk), .rst_n(rst_n), .d(w_u_hcb_Q0_u_c_procdff_71790_Q[2709:1321]), .ea(rst_n), .q(L167_o[1388:0]), .eq(L167_o[1389]));
    ot_dp_st #(.W(1388)) u_bout_L168_o (.clk(clk), .rst_n(rst_n), .d({w_u_hcb_Q0_u_c_procdff_71800_Q[0], w_u_hcb_Q0_u_c_procdff_71795_Q[0], w_u_hcb_Q0_u_c_procdff_71790_Q[4095:2710]}), .ea(rst_n), .q(L168_o[1387:0]), .eq(L168_o[1388]));
    ot_dp_st #(.W(4098)) u_bout_L19_o (.clk(clk), .rst_n(rst_n), .d({w_u_hcb_Q0_u_c_procdff_71805_Q[0], w_u_hcb_Q0_procdff_69251_Q[4096:0]}), .ea(rst_n), .q(L19_o[4097:0]), .eq(L19_o[4098]));
    ot_dp_st #(.W(1)) u_bout_L204_o (.clk(clk), .rst_n(rst_n), .d(w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0]), .ea(rst_n), .q(L204_o[0:0]), .eq(L204_o[1]));
    ot_dp_st #(.W(1)) u_bout_L205_o (.clk(clk), .rst_n(rst_n), .d(w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0]), .ea(rst_n), .q(L205_o[0:0]), .eq(L205_o[1]));
    ot_dp_st #(.W(21)) u_ft_L101x1_o_0 (.clk(clk), .rst_n(rst_n), .d(L101x1_i[20:0]), .ea(L101x1_i[21]), .q(L101x1_o_s0[20:0]), .eq(L101x1_o_s0[21]));
    ot_dp_st #(.W(21)) u_ft_L101x1_o_1 (.clk(clk), .rst_n(rst_n), .d(L101x1_o_s0[20:0]), .ea(L101x1_o_s0[21]), .q(L101x1_o_s1[20:0]), .eq(L101x1_o_s1[21]));
    ot_dp_st #(.W(21)) u_ft_L101x1_o_2 (.clk(clk), .rst_n(rst_n), .d(L101x1_o_s1[20:0]), .ea(L101x1_o_s1[21]), .q(L101x1_o[20:0]), .eq(L101x1_o[21]));
    ot_dp_st #(.W(5)) u_ft_L126x8_o_0 (.clk(clk), .rst_n(rst_n), .d(L126x8_i[4:0]), .ea(L126x8_i[5]), .q(L126x8_o_s0[4:0]), .eq(L126x8_o_s0[5]));
    ot_dp_st #(.W(5)) u_ft_L126x8_o_1 (.clk(clk), .rst_n(rst_n), .d(L126x8_o_s0[4:0]), .ea(L126x8_o_s0[5]), .q(L126x8_o_s1[4:0]), .eq(L126x8_o_s1[5]));
    ot_dp_st #(.W(5)) u_ft_L126x8_o_2 (.clk(clk), .rst_n(rst_n), .d(L126x8_o_s1[4:0]), .ea(L126x8_o_s1[5]), .q(L126x8_o[4:0]), .eq(L126x8_o[5]));
    ot_dp_st #(.W(1615)) u_ft_L28x1_o_0 (.clk(clk), .rst_n(rst_n), .d(L28x1_i[1614:0]), .ea(L28x1_i[1615]), .q(L28x1_o_s0[1614:0]), .eq(L28x1_o_s0[1615]));
    ot_dp_st #(.W(1615)) u_ft_L28x1_o_1 (.clk(clk), .rst_n(rst_n), .d(L28x1_o_s0[1614:0]), .ea(L28x1_o_s0[1615]), .q(L28x1_o_s1[1614:0]), .eq(L28x1_o_s1[1615]));
    ot_dp_st #(.W(1615)) u_ft_L28x1_o_2 (.clk(clk), .rst_n(rst_n), .d(L28x1_o_s1[1614:0]), .ea(L28x1_o_s1[1615]), .q(L28x1_o_s2[1614:0]), .eq(L28x1_o_s2[1615]));
    ot_dp_st #(.W(1615)) u_ft_L28x1_o_3 (.clk(clk), .rst_n(rst_n), .d(L28x1_o_s2[1614:0]), .ea(L28x1_o_s2[1615]), .q(L28x1_o[1614:0]), .eq(L28x1_o[1615]));
    ot_dp_st #(.W(1329)) u_ft_L36x1_o_0 (.clk(clk), .rst_n(rst_n), .d(L36x1_i[1328:0]), .ea(L36x1_i[1329]), .q(L36x1_o_s0[1328:0]), .eq(L36x1_o_s0[1329]));
    ot_dp_st #(.W(1329)) u_ft_L36x1_o_1 (.clk(clk), .rst_n(rst_n), .d(L36x1_o_s0[1328:0]), .ea(L36x1_o_s0[1329]), .q(L36x1_o_s1[1328:0]), .eq(L36x1_o_s1[1329]));
    ot_dp_st #(.W(1329)) u_ft_L36x1_o_2 (.clk(clk), .rst_n(rst_n), .d(L36x1_o_s1[1328:0]), .ea(L36x1_o_s1[1329]), .q(L36x1_o_s2[1328:0]), .eq(L36x1_o_s2[1329]));
    ot_dp_st #(.W(1329)) u_ft_L36x1_o_3 (.clk(clk), .rst_n(rst_n), .d(L36x1_o_s2[1328:0]), .ea(L36x1_o_s2[1329]), .q(L36x1_o[1328:0]), .eq(L36x1_o[1329]));
    ot_dp_st #(.W(788)) u_ft_L42x1_o_0 (.clk(clk), .rst_n(rst_n), .d(L42x1_i[787:0]), .ea(L42x1_i[788]), .q(L42x1_o_s0[787:0]), .eq(L42x1_o_s0[788]));
    ot_dp_st #(.W(788)) u_ft_L42x1_o_1 (.clk(clk), .rst_n(rst_n), .d(L42x1_o_s0[787:0]), .ea(L42x1_o_s0[788]), .q(L42x1_o_s1[787:0]), .eq(L42x1_o_s1[788]));
    ot_dp_st #(.W(788)) u_ft_L42x1_o_2 (.clk(clk), .rst_n(rst_n), .d(L42x1_o_s1[787:0]), .ea(L42x1_o_s1[788]), .q(L42x1_o[787:0]), .eq(L42x1_o[788]));
    ot_dp_st #(.W(788)) u_ft_L43x1_o_0 (.clk(clk), .rst_n(rst_n), .d(L43x1_i[787:0]), .ea(L43x1_i[788]), .q(L43x1_o_s0[787:0]), .eq(L43x1_o_s0[788]));
    ot_dp_st #(.W(788)) u_ft_L43x1_o_1 (.clk(clk), .rst_n(rst_n), .d(L43x1_o_s0[787:0]), .ea(L43x1_o_s0[788]), .q(L43x1_o_s1[787:0]), .eq(L43x1_o_s1[788]));
    ot_dp_st #(.W(788)) u_ft_L43x1_o_2 (.clk(clk), .rst_n(rst_n), .d(L43x1_o_s1[787:0]), .ea(L43x1_o_s1[788]), .q(L43x1_o[787:0]), .eq(L43x1_o[788]));
    ot_dp_st #(.W(611)) u_ft_L51x1_o_0 (.clk(clk), .rst_n(rst_n), .d(L51x1_i[610:0]), .ea(L51x1_i[611]), .q(L51x1_o_s0[610:0]), .eq(L51x1_o_s0[611]));
    ot_dp_st #(.W(611)) u_ft_L51x1_o_1 (.clk(clk), .rst_n(rst_n), .d(L51x1_o_s0[610:0]), .ea(L51x1_o_s0[611]), .q(L51x1_o_s1[610:0]), .eq(L51x1_o_s1[611]));
    ot_dp_st #(.W(611)) u_ft_L51x1_o_2 (.clk(clk), .rst_n(rst_n), .d(L51x1_o_s1[610:0]), .ea(L51x1_o_s1[611]), .q(L51x1_o[610:0]), .eq(L51x1_o[611]));
    ot_dp_st #(.W(610)) u_ft_L52x8_o_0 (.clk(clk), .rst_n(rst_n), .d(L52x8_i[609:0]), .ea(L52x8_i[610]), .q(L52x8_o_s0[609:0]), .eq(L52x8_o_s0[610]));
    ot_dp_st #(.W(610)) u_ft_L52x8_o_1 (.clk(clk), .rst_n(rst_n), .d(L52x8_o_s0[609:0]), .ea(L52x8_o_s0[610]), .q(L52x8_o_s1[609:0]), .eq(L52x8_o_s1[610]));
    ot_dp_st #(.W(610)) u_ft_L52x8_o_2 (.clk(clk), .rst_n(rst_n), .d(L52x8_o_s1[609:0]), .ea(L52x8_o_s1[610]), .q(L52x8_o[609:0]), .eq(L52x8_o[610]));
    ot_dp_st #(.W(4)) u_ft_L732x4_o_0 (.clk(clk), .rst_n(rst_n), .d(L732x4_i[3:0]), .ea(L732x4_i[4]), .q(L732x4_o_s0[3:0]), .eq(L732x4_o_s0[4]));
    ot_dp_st #(.W(4)) u_ft_L732x4_o_1 (.clk(clk), .rst_n(rst_n), .d(L732x4_o_s0[3:0]), .ea(L732x4_o_s0[4]), .q(L732x4_o[3:0]), .eq(L732x4_o[4]));
    ot_dp_st #(.W(3)) u_ft_L733x3_o_0 (.clk(clk), .rst_n(rst_n), .d(L733x3_i[2:0]), .ea(L733x3_i[3]), .q(L733x3_o_s0[2:0]), .eq(L733x3_o_s0[3]));
    ot_dp_st #(.W(3)) u_ft_L733x3_o_1 (.clk(clk), .rst_n(rst_n), .d(L733x3_o_s0[2:0]), .ea(L733x3_o_s0[3]), .q(L733x3_o[2:0]), .eq(L733x3_o[3]));
    ot_dp_st #(.W(1)) u_ft_L734x7_o_0 (.clk(clk), .rst_n(rst_n), .d(L734x7_i[0:0]), .ea(L734x7_i[1]), .q(L734x7_o_s0[0:0]), .eq(L734x7_o_s0[1]));
    ot_dp_st #(.W(1)) u_ft_L734x7_o_1 (.clk(clk), .rst_n(rst_n), .d(L734x7_o_s0[0:0]), .ea(L734x7_o_s0[1]), .q(L734x7_o_s1[0:0]), .eq(L734x7_o_s1[1]));
    ot_dp_st #(.W(1)) u_ft_L734x7_o_2 (.clk(clk), .rst_n(rst_n), .d(L734x7_o_s1[0:0]), .ea(L734x7_o_s1[1]), .q(L734x7_o[0:0]), .eq(L734x7_o[1]));
    ot_dp_st #(.W(274)) u_ft_L73x1_o_0 (.clk(clk), .rst_n(rst_n), .d(L73x1_i[273:0]), .ea(L73x1_i[274]), .q(L73x1_o_s0[273:0]), .eq(L73x1_o_s0[274]));
    ot_dp_st #(.W(274)) u_ft_L73x1_o_1 (.clk(clk), .rst_n(rst_n), .d(L73x1_o_s0[273:0]), .ea(L73x1_o_s0[274]), .q(L73x1_o_s1[273:0]), .eq(L73x1_o_s1[274]));
    ot_dp_st #(.W(274)) u_ft_L73x1_o_2 (.clk(clk), .rst_n(rst_n), .d(L73x1_o_s1[273:0]), .ea(L73x1_o_s1[274]), .q(L73x1_o[273:0]), .eq(L73x1_o[274]));
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_71_54855_Y = w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_71_54853_Y[19:0] + w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_71_54854_Y[19:0];   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_71_54857_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_71_54855_Y[19:0] + w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_71_54856_Y[19:0];   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_77_54866_Y = w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54865_Y[31:0] + {32{1'b0}};   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_77_54868_Y = w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54867_Y[31:0] + {{24{1'b0}}, w_hb_idx_s_SW_scorer_procdff_71769_Q[7:0]};   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_77_54873_Y = w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54872_Y[31:0] + 32'b00000000000000000000000000000001;   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_77_54875_Y = w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54874_Y[31:0] + {{24{1'b0}}, w_hb_idx_s_SW_scorer_procdff_71769_Q[7:0]};   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_77_54880_Y = w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54879_Y[31:0] + 32'b00000000000000000000000000000010;   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_77_54882_Y = w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54881_Y[31:0] + {{24{1'b0}}, w_hb_idx_s_SW_scorer_procdff_71769_Q[7:0]};   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_77_54887_Y = w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54886_Y[31:0] + 32'b00000000000000000000000000000011;   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_77_54889_Y = w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54888_Y[31:0] + {{24{1'b0}}, w_hb_idx_s_SW_scorer_procdff_71769_Q[7:0]};   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54897_Y = w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54896_Y[11:0] + {12{1'b0}};   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54899_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54897_Y[11:0] + w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54898_Y[11:0];   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54905_Y = w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54904_Y[11:0] + 12'b000000000001;   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54907_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54905_Y[11:0] + w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54906_Y[11:0];   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54913_Y = w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54912_Y[11:0] + 12'b000000000010;   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54915_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54913_Y[11:0] + w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54914_Y[11:0];   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54921_Y = w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54920_Y[11:0] + 12'b000000000011;   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54923_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54921_Y[11:0] + w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54922_Y[11:0];   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54953_Y = w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54952_Y[11:0] + 12'b000000000100;   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54955_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54953_Y[11:0] + w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54954_Y[11:0];   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54961_Y = w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54960_Y[11:0] + 12'b000000000101;   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54963_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54961_Y[11:0] + w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54962_Y[11:0];   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54969_Y = w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54968_Y[11:0] + 12'b000000000110;   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54971_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54969_Y[11:0] + w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54970_Y[11:0];   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54977_Y = w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54976_Y[11:0] + 12'b000000000111;   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54979_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54977_Y[11:0] + w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54978_Y[11:0];   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_91_54929_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_71_54857_Y[19:0] + w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_91_54928_Y[19:0];   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_91_54930_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_91_54929_Y[19:0] + {20{1'b0}};   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_91_54985_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_71_54857_Y[19:0] + w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_91_54984_Y[19:0];   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_91_54986_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_91_54985_Y[19:0] + 20'b00000000000000000100;   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_92_54931_Y = {{4{1'b0}}, w_hb_idx_s_SW_scorer_procdff_71769_Q[7:0]} + 12'b000000000001;   
    assign w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_92_54987_Y = {{4{1'b0}}, w_hb_idx_s_SW_scorer_procdff_71769_Q[7:0]} + 12'b000000000001;   
    assign w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71688_Y = ~w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0];
    assign w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71693_Y = ~w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0];
    assign w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71698_Y = ~w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0];
    assign w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71703_Y = ~w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0];
    assign w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71708_Y = ~w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0];
    assign w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71713_Y = ~w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0];
    assign w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71721_Y = ~w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0];
    assign w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71726_Y = ~w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0];
    assign w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71731_Y = ~w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0];
    assign w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71736_Y = ~w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0];
    assign w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71741_Y = ~w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0];
    assign w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71746_Y = ~w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0];
    assign w_hb_idx_s_SW_scorer_auto_proc_dff_cc_220_proc_dff_71752_Y = ~w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0];
    assign w_hb_idx_s_SW_scorer_ge_ot_hbm_idx_score_quarter_static_h_sv_92_54933_Y = w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_92_54932_Y[11:0] >= w_hb_idx_s_SW_scorer_procdff_71760_Q[11:0];   
    assign w_hb_idx_s_SW_scorer_ge_ot_hbm_idx_score_quarter_static_h_sv_92_54989_Y = w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_92_54988_Y[11:0] >= w_hb_idx_s_SW_scorer_procdff_71760_Q[11:0];   
    assign w_hb_idx_s_SW_scorer_gt_ot_hbm_idx_score_quarter_static_h_sv_76_54861_Y = w_hb_idx_s_SW_scorer_procdff_71760_Q[11:0] > 32'b00000000000000000000101010110000;   
    assign w_hb_idx_s_SW_scorer_gt_ot_hbm_idx_score_quarter_static_h_sv_76_54862_Y = w_hb_idx_s_SW_scorer_procdff_71769_Q[7:0] > 32'b00000000000000000000000010101010;   
    assign w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_120_54935_Y = !w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0];   
    assign w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_120_54991_Y = !w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0];   
    assign w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_139_54945_Y = !w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0];   
    assign w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_139_55001_Y = !w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0];   
    assign w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_153_54893_Y = !w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0];   
    assign w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_77_54864_Y = !w_hb_idx_s_SW_scorer_procdff_71770_Q[0];   
    assign w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_77_54871_Y = !w_hb_idx_s_SW_scorer_procdff_71770_Q[1099];   
    assign w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_77_54878_Y = !w_hb_idx_s_SW_scorer_procdff_71770_Q[2198];   
    assign w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_77_54885_Y = !w_hb_idx_s_SW_scorer_procdff_71770_Q[3297];   
    assign w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54901_Y = !w_hb_idx_s_SW_scorer_procdff_71761_Q[0];   
    assign w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54909_Y = !w_hb_idx_s_SW_scorer_procdff_71761_Q[0];   
    assign w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54917_Y = !w_hb_idx_s_SW_scorer_procdff_71761_Q[0];   
    assign w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54925_Y = !w_hb_idx_s_SW_scorer_procdff_71761_Q[0];   
    assign w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54957_Y = !w_hb_idx_s_SW_scorer_procdff_71761_Q[0];   
    assign w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54965_Y = !w_hb_idx_s_SW_scorer_procdff_71761_Q[0];   
    assign w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54973_Y = !w_hb_idx_s_SW_scorer_procdff_71761_Q[0];   
    assign w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54981_Y = !w_hb_idx_s_SW_scorer_procdff_71761_Q[0];   
    assign w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_76_54863_Y = w_hb_idx_s_SW_scorer_gt_ot_hbm_idx_score_quarter_static_h_sv_76_54861_Y[0] || w_hb_idx_s_SW_scorer_gt_ot_hbm_idx_score_quarter_static_h_sv_76_54862_Y[0];   
    assign w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_77_54870_Y = w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_77_54864_Y[0] || w_hb_idx_s_SW_scorer_nex_ot_hbm_idx_score_quarter_static_h_sv_77_54869_Y[0];   
    assign w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_77_54877_Y = w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_77_54871_Y[0] || w_hb_idx_s_SW_scorer_nex_ot_hbm_idx_score_quarter_static_h_sv_77_54876_Y[0];   
    assign w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_77_54884_Y = w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_77_54878_Y[0] || w_hb_idx_s_SW_scorer_nex_ot_hbm_idx_score_quarter_static_h_sv_77_54883_Y[0];   
    assign w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_77_54891_Y = w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_77_54885_Y[0] || w_hb_idx_s_SW_scorer_nex_ot_hbm_idx_score_quarter_static_h_sv_77_54890_Y[0];   
    assign w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54903_Y = w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54901_Y[0] || w_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54902_Y[0];   
    assign w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54911_Y = w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54909_Y[0] || w_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54910_Y[0];   
    assign w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54919_Y = w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54917_Y[0] || w_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54918_Y[0];   
    assign w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54927_Y = w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54925_Y[0] || w_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54926_Y[0];   
    assign w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54959_Y = w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54957_Y[0] || w_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54958_Y[0];   
    assign w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54967_Y = w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54965_Y[0] || w_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54966_Y[0];   
    assign w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54975_Y = w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54973_Y[0] || w_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54974_Y[0];   
    assign w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54983_Y = w_hb_idx_s_SW_scorer_logic_not_ot_hbm_idx_score_quarter_static_h_sv_88_54981_Y[0] || w_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54982_Y[0];   
    assign w_hb_idx_s_SW_scorer_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54900_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54899_Y[11:0] < w_hb_idx_s_SW_scorer_procdff_71760_Q[11:0];   
    assign w_hb_idx_s_SW_scorer_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54908_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54907_Y[11:0] < w_hb_idx_s_SW_scorer_procdff_71760_Q[11:0];   
    assign w_hb_idx_s_SW_scorer_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54916_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54915_Y[11:0] < w_hb_idx_s_SW_scorer_procdff_71760_Q[11:0];   
    assign w_hb_idx_s_SW_scorer_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54924_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54923_Y[11:0] < w_hb_idx_s_SW_scorer_procdff_71760_Q[11:0];   
    assign w_hb_idx_s_SW_scorer_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54956_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54955_Y[11:0] < w_hb_idx_s_SW_scorer_procdff_71760_Q[11:0];   
    assign w_hb_idx_s_SW_scorer_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54964_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54963_Y[11:0] < w_hb_idx_s_SW_scorer_procdff_71760_Q[11:0];   
    assign w_hb_idx_s_SW_scorer_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54972_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54971_Y[11:0] < w_hb_idx_s_SW_scorer_procdff_71760_Q[11:0];   
    assign w_hb_idx_s_SW_scorer_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54980_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_87_54979_Y[11:0] < w_hb_idx_s_SW_scorer_procdff_71760_Q[11:0];   
    assign w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_71_54853_Y = 20'b00000000011000000000 * {{9{1'b0}}, w_hb_idx_s_SW_scorer_procdff_71759_Q[10:0]};   
    assign w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_71_54854_Y = 20'b00000000000000001000 * {{12{1'b0}}, w_hb_idx_s_SW_scorer_procdff_71758_Q[7:0]};   
    assign w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_71_54856_Y = 20'b00000000110000000000 * {{12{1'b0}}, w_hb_idx_s_SW_scorer_procdff_71769_Q[7:0]};   
    assign w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54865_Y = 32'b00000000000000000000000000000100 * {{31{1'b0}}, w_hb_idx_s_SW_scorer_procdff_71757_Q[0]};   
    assign w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54867_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_77_54866_Y[31:0] * 32'b00000000000000000000000010000000;   
    assign w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54872_Y = 32'b00000000000000000000000000000100 * {{31{1'b0}}, w_hb_idx_s_SW_scorer_procdff_71757_Q[0]};   
    assign w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54874_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_77_54873_Y[31:0] * 32'b00000000000000000000000010000000;   
    assign w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54879_Y = 32'b00000000000000000000000000000100 * {{31{1'b0}}, w_hb_idx_s_SW_scorer_procdff_71757_Q[0]};   
    assign w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54881_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_77_54880_Y[31:0] * 32'b00000000000000000000000010000000;   
    assign w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54886_Y = 32'b00000000000000000000000000000100 * {{31{1'b0}}, w_hb_idx_s_SW_scorer_procdff_71757_Q[0]};   
    assign w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_77_54888_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_77_54887_Y[31:0] * 32'b00000000000000000000000010000000;   
    assign w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54896_Y = {{4{1'b0}}, w_hb_idx_s_SW_scorer_procdff_71769_Q[7:0]} * 12'b000000010000;   
    assign w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54904_Y = {{4{1'b0}}, w_hb_idx_s_SW_scorer_procdff_71769_Q[7:0]} * 12'b000000010000;   
    assign w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54912_Y = {{4{1'b0}}, w_hb_idx_s_SW_scorer_procdff_71769_Q[7:0]} * 12'b000000010000;   
    assign w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54920_Y = {{4{1'b0}}, w_hb_idx_s_SW_scorer_procdff_71769_Q[7:0]} * 12'b000000010000;   
    assign w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54952_Y = {{4{1'b0}}, w_hb_idx_s_SW_scorer_procdff_71769_Q[7:0]} * 12'b000000010000;   
    assign w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54960_Y = {{4{1'b0}}, w_hb_idx_s_SW_scorer_procdff_71769_Q[7:0]} * 12'b000000010000;   
    assign w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54968_Y = {{4{1'b0}}, w_hb_idx_s_SW_scorer_procdff_71769_Q[7:0]} * 12'b000000010000;   
    assign w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_87_54976_Y = {{4{1'b0}}, w_hb_idx_s_SW_scorer_procdff_71769_Q[7:0]} * 12'b000000010000;   
    assign w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_92_54932_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_92_54931_Y[11:0] * 12'b000000010000;   
    assign w_hb_idx_s_SW_scorer_mul_ot_hbm_idx_score_quarter_static_h_sv_92_54988_Y = w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_92_54987_Y[11:0] * 12'b000000010000;   
    assign w_hb_idx_s_SW_scorer_nex_ot_hbm_idx_score_quarter_static_h_sv_77_54869_Y = w_hb_idx_s_SW_scorer_procdff_71770_Q[10:1] !== w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_77_54868_Y[9:0];   
    assign w_hb_idx_s_SW_scorer_nex_ot_hbm_idx_score_quarter_static_h_sv_77_54876_Y = w_hb_idx_s_SW_scorer_procdff_71770_Q[1109:1100] !== w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_77_54875_Y[9:0];   
    assign w_hb_idx_s_SW_scorer_nex_ot_hbm_idx_score_quarter_static_h_sv_77_54883_Y = w_hb_idx_s_SW_scorer_procdff_71770_Q[2208:2199] !== w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_77_54882_Y[9:0];   
    assign w_hb_idx_s_SW_scorer_nex_ot_hbm_idx_score_quarter_static_h_sv_77_54890_Y = w_hb_idx_s_SW_scorer_procdff_71770_Q[3307:3298] !== w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_77_54889_Y[9:0];   
    reg [0:0] g_hb_idx_s_SW_scorer_procdff_71757_q;
    assign w_hb_idx_s_SW_scorer_procdff_71757_Q = g_hb_idx_s_SW_scorer_procdff_71757_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_procdff_71757_q <= 1'b0;   
    reg [7:0] g_hb_idx_s_SW_scorer_procdff_71758_q;
    assign w_hb_idx_s_SW_scorer_procdff_71758_Q = g_hb_idx_s_SW_scorer_procdff_71758_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_procdff_71758_q <= L202_i_q[8:1];   
    reg [10:0] g_hb_idx_s_SW_scorer_procdff_71759_q;
    assign w_hb_idx_s_SW_scorer_procdff_71759_Q = g_hb_idx_s_SW_scorer_procdff_71759_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_procdff_71759_q <= {11{1'b0}};   
    reg [11:0] g_hb_idx_s_SW_scorer_procdff_71760_q;
    assign w_hb_idx_s_SW_scorer_procdff_71760_Q = g_hb_idx_s_SW_scorer_procdff_71760_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_procdff_71760_q <= L160_i_q[589:578];   
    reg [0:0] g_hb_idx_s_SW_scorer_procdff_71761_q;
    assign w_hb_idx_s_SW_scorer_procdff_71761_Q = g_hb_idx_s_SW_scorer_procdff_71761_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_procdff_71761_q <= L202_i_q[0];   
    reg [170:0] g_hb_idx_s_SW_scorer_procdff_71762_q;
    assign w_hb_idx_s_SW_scorer_procdff_71762_Q = g_hb_idx_s_SW_scorer_procdff_71762_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_procdff_71762_q <= L202_i_q[179:9];   
    reg [0:0] g_hb_idx_s_SW_scorer_procdff_71763_q;
    assign w_hb_idx_s_SW_scorer_procdff_71763_Q = g_hb_idx_s_SW_scorer_procdff_71763_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_procdff_71763_q <= L160_i_q[552];   
    reg [7:0] g_hb_idx_s_SW_scorer_procdff_71764_q;
    assign w_hb_idx_s_SW_scorer_procdff_71764_Q = g_hb_idx_s_SW_scorer_procdff_71764_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_procdff_71764_q <= L160_i_q[519:512];   
    reg [511:0] g_hb_idx_s_SW_scorer_procdff_71765_q;
    assign w_hb_idx_s_SW_scorer_procdff_71765_Q = g_hb_idx_s_SW_scorer_procdff_71765_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_procdff_71765_q <= L160_i_q[511:0];   
    reg [31:0] g_hb_idx_s_SW_scorer_procdff_71766_q;
    assign w_hb_idx_s_SW_scorer_procdff_71766_Q = g_hb_idx_s_SW_scorer_procdff_71766_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_procdff_71766_q <= L160_i_q[551:520];   
    reg [15:0] g_hb_idx_s_SW_scorer_procdff_71767_q;
    assign w_hb_idx_s_SW_scorer_procdff_71767_Q = g_hb_idx_s_SW_scorer_procdff_71767_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_procdff_71767_q <= L160_i_q[568:553];   
    reg [0:0] g_hb_idx_s_SW_scorer_procdff_71768_q;
    assign w_hb_idx_s_SW_scorer_procdff_71768_Q = g_hb_idx_s_SW_scorer_procdff_71768_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_procdff_71768_q <= L160_i_q[577];   
    reg [7:0] g_hb_idx_s_SW_scorer_procdff_71769_q;
    assign w_hb_idx_s_SW_scorer_procdff_71769_Q = g_hb_idx_s_SW_scorer_procdff_71769_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_procdff_71769_q <= L160_i_q[576:569];   
    reg [4395:0] g_hb_idx_s_SW_scorer_procdff_71770_q;
    assign w_hb_idx_s_SW_scorer_procdff_71770_Q = g_hb_idx_s_SW_scorer_procdff_71770_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_procdff_71770_q <= L160_i_q[4985:590];   
    assign w_hb_idx_s_SW_scorer_procmux_66627_Y = w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_77_54891_Y[0] ? 1'b1 : w_hb_idx_s_SW_scorer_procmux_66635_Y[0];   
    assign w_hb_idx_s_SW_scorer_procmux_66629_Y = w_hb_idx_s_SW_scorer_procdff_71768_Q[0] ? w_hb_idx_s_SW_scorer_procmux_66627_Y[0] : 1'bx;   
    assign w_hb_idx_s_SW_scorer_procmux_66633_Y = w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_77_54884_Y[0] ? 1'b1 : w_hb_idx_s_SW_scorer_procmux_66641_Y[0];   
    assign w_hb_idx_s_SW_scorer_procmux_66635_Y = w_hb_idx_s_SW_scorer_procdff_71768_Q[0] ? w_hb_idx_s_SW_scorer_procmux_66633_Y[0] : 1'bx;   
    assign w_hb_idx_s_SW_scorer_procmux_66639_Y = w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_77_54877_Y[0] ? 1'b1 : w_hb_idx_s_SW_scorer_procmux_66647_Y[0];   
    assign w_hb_idx_s_SW_scorer_procmux_66641_Y = w_hb_idx_s_SW_scorer_procdff_71768_Q[0] ? w_hb_idx_s_SW_scorer_procmux_66639_Y[0] : 1'bx;   
    assign w_hb_idx_s_SW_scorer_procmux_66645_Y = w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_77_54870_Y[0] ? 1'b1 : w_hb_idx_s_SW_scorer_procmux_66653_Y[0];   
    assign w_hb_idx_s_SW_scorer_procmux_66647_Y = w_hb_idx_s_SW_scorer_procdff_71768_Q[0] ? w_hb_idx_s_SW_scorer_procmux_66645_Y[0] : 1'bx;   
    assign w_hb_idx_s_SW_scorer_procmux_66651_Y = w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_76_54863_Y[0] ? 1'b1 : 1'b0;   
    assign w_hb_idx_s_SW_scorer_procmux_66653_Y = w_hb_idx_s_SW_scorer_procdff_71768_Q[0] ? w_hb_idx_s_SW_scorer_procmux_66651_Y[0] : 1'bx;   
    assign w_hb_idx_s_SW_scorer_procmux_66659_Y = w_hb_idx_s_SW_scorer_procdff_71768_Q[0] ? w_hb_idx_s_SW_scorer_procmux_66629_Y[0] : 1'b0;   
    ot_bind_native_129bb1e301d3931c53ca86a8 g_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54902 (.A(w_hb_idx_s_SW_scorer_procdff_71762_Q[170:0]), .B(w_hb_idx_s_SW_scorer_procdff_71769_Q[7:0]), .Y(w_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54902_Y));
    ot_bind_native_129bb1e301d3931c53ca86a8 g_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54910 (.A(w_hb_idx_s_SW_scorer_procdff_71762_Q[170:0]), .B(w_hb_idx_s_SW_scorer_procdff_71769_Q[7:0]), .Y(w_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54910_Y));
    ot_bind_native_129bb1e301d3931c53ca86a8 g_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54918 (.A(w_hb_idx_s_SW_scorer_procdff_71762_Q[170:0]), .B(w_hb_idx_s_SW_scorer_procdff_71769_Q[7:0]), .Y(w_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54918_Y));
    ot_bind_native_129bb1e301d3931c53ca86a8 g_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54926 (.A(w_hb_idx_s_SW_scorer_procdff_71762_Q[170:0]), .B(w_hb_idx_s_SW_scorer_procdff_71769_Q[7:0]), .Y(w_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54926_Y));
    ot_bind_native_129bb1e301d3931c53ca86a8 g_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54958 (.A(w_hb_idx_s_SW_scorer_procdff_71762_Q[170:0]), .B(w_hb_idx_s_SW_scorer_procdff_71769_Q[7:0]), .Y(w_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54958_Y));
    ot_bind_native_129bb1e301d3931c53ca86a8 g_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54966 (.A(w_hb_idx_s_SW_scorer_procdff_71762_Q[170:0]), .B(w_hb_idx_s_SW_scorer_procdff_71769_Q[7:0]), .Y(w_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54966_Y));
    ot_bind_native_129bb1e301d3931c53ca86a8 g_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54974 (.A(w_hb_idx_s_SW_scorer_procdff_71762_Q[170:0]), .B(w_hb_idx_s_SW_scorer_procdff_71769_Q[7:0]), .Y(w_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54974_Y));
    ot_bind_native_129bb1e301d3931c53ca86a8 g_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54982 (.A(w_hb_idx_s_SW_scorer_procdff_71762_Q[170:0]), .B(w_hb_idx_s_SW_scorer_procdff_71769_Q[7:0]), .Y(w_hb_idx_s_SW_scorer_shiftx_ot_hbm_idx_score_quarter_static_h_sv_88_54982_Y));
    assign w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54898_Y = w_hb_idx_s_SW_scorer_procdff_71757_Q[0] ? 12'b000000001000 : {12{1'b0}};   
    assign w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54906_Y = w_hb_idx_s_SW_scorer_procdff_71757_Q[0] ? 12'b000000001000 : {12{1'b0}};   
    assign w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54914_Y = w_hb_idx_s_SW_scorer_procdff_71757_Q[0] ? 12'b000000001000 : {12{1'b0}};   
    assign w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54922_Y = w_hb_idx_s_SW_scorer_procdff_71757_Q[0] ? 12'b000000001000 : {12{1'b0}};   
    assign w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54954_Y = w_hb_idx_s_SW_scorer_procdff_71757_Q[0] ? 12'b000000001000 : {12{1'b0}};   
    assign w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54962_Y = w_hb_idx_s_SW_scorer_procdff_71757_Q[0] ? 12'b000000001000 : {12{1'b0}};   
    assign w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54970_Y = w_hb_idx_s_SW_scorer_procdff_71757_Q[0] ? 12'b000000001000 : {12{1'b0}};   
    assign w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_87_54978_Y = w_hb_idx_s_SW_scorer_procdff_71757_Q[0] ? 12'b000000001000 : {12{1'b0}};   
    assign w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_91_54928_Y = w_hb_idx_s_SW_scorer_procdff_71757_Q[0] ? 20'b00000000011000000000 : {20{1'b0}};   
    assign w_hb_idx_s_SW_scorer_ternary_ot_hbm_idx_score_quarter_static_h_sv_91_54984_Y = w_hb_idx_s_SW_scorer_procdff_71757_Q[0] ? 20'b00000000011000000000 : {20{1'b0}};   
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54724_Y = !w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71563_Q[4:3];   
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54726_Y = 2'b01 == w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71563_Q[4:3];   
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54728_Y = 2'b10 == w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71563_Q[4:3];   
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54730_Y = {2{1'b1}} == w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71563_Q[4:3];   
    reg [31:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71548_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71548_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71548_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71548_q <= 32'b00000000000000000000000000000100;   
    reg [551:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71549_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71549_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71549_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71549_q <= w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71550_Q[551:0];   
    reg [551:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71550_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71550_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71550_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71550_q <= {w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__905746de[137:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__41fd8e31[137:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__6a12df79[137:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__10176855[137:0]};   
    reg [0:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71551_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71551_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71551_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71551_q <= w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71557_Q[0];   
    reg [567:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71552_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71552_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71552_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71552_q <= w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71558_Q[567:0];   
    reg [0:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71553_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71553_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71553_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71553_q <= w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71559_Q[0];   
    reg [3:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71554_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71554_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71554_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71554_q <= w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71560_Q[3:0];   
    reg [2175:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71555_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71555_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71555_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71555_q <= w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71561_Q[2175:0];   
    reg [29:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71556_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71556_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71556_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71556_q <= w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71562_Q[29:0];   
    reg [0:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71557_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71557_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71557_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71557_q <= w_hb_idx_s_SW_scorer_procdff_71763_Q[0];   
    reg [567:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71558_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71558_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71558_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71558_q <= {w_hb_idx_s_SW_scorer_procdff_71764_Q[7:0], w_hb_idx_s_SW_scorer_procdff_71765_Q[511:0], w_hb_idx_s_SW_scorer_procdff_71766_Q[31:0], w_hb_idx_s_SW_scorer_procdff_71767_Q[15:0]};   
    reg [0:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71559_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71559_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71559_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71559_q <= w_hb_idx_s_SW_scorer_procdff_71768_Q[0];   
    reg [3:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71560_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71560_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71560_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71560_q <= {w_hb_idx_s_SW_scorer_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54924_Y[0], w_hb_idx_s_SW_scorer_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54916_Y[0], w_hb_idx_s_SW_scorer_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54908_Y[0], w_hb_idx_s_SW_scorer_lt_ot_hbm_idx_score_quarter_static_h_sv_87_54900_Y[0]};   
    reg [2175:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71561_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71561_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71561_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71561_q <= {w_hb_idx_s_SW_scorer_procdff_71770_Q[2197:1110], w_hb_idx_s_SW_scorer_procdff_71770_Q[1098:11]};   
    reg [29:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71562_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71562_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71562_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71562_q <= {w_hb_idx_s_SW_scorer_procmux_66659_Y[0], w_hb_idx_s_SW_scorer_ge_ot_hbm_idx_score_quarter_static_h_sv_92_54933_Y[0], w_hb_idx_s_SW_scorer_add_ot_hbm_idx_score_quarter_static_h_sv_91_54930_Y[19:0], {4{1'b0}}, w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54927_Y[0], w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54919_Y[0], w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54911_Y[0], w_hb_idx_s_SW_scorer_logic_or_ot_hbm_idx_score_quarter_static_h_sv_88_54903_Y[0]};   
    reg [7:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71563_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71563_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71563_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71563_q <= {8{1'b0}};   
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__10176855 = w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54724_Y[0] ? {w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71537_Q[0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_vl_q[4:1], L188_i_q[32:1], w_u_hb_idx_s_Q2_r0c0_k2h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c0_k1h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c0_k0h1_cs_out[31:0], L188_i_q[0], w_u_hb_idx_s_Q2_r0c0_k2h1_cf_out[0], w_u_hb_idx_s_Q2_r0c0_k1h1_cf_out[0], w_u_hb_idx_s_Q2_r0c0_k0h1_cf_out[0]} : {138{1'b0}};   
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__6a12df79 = w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54726_Y[0] ? {w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71537_Q[0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_vl_q[4:1], L188_i_q[32:1], w_u_hb_idx_s_Q2_r0c0_k2h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c0_k1h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c0_k0h1_cs_out[31:0], L188_i_q[0], w_u_hb_idx_s_Q2_r0c0_k2h1_cf_out[0], w_u_hb_idx_s_Q2_r0c0_k1h1_cf_out[0], w_u_hb_idx_s_Q2_r0c0_k0h1_cf_out[0]} : {138{1'b0}};   
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__41fd8e31 = w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54728_Y[0] ? {w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71537_Q[0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_vl_q[4:1], L188_i_q[32:1], w_u_hb_idx_s_Q2_r0c0_k2h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c0_k1h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c0_k0h1_cs_out[31:0], L188_i_q[0], w_u_hb_idx_s_Q2_r0c0_k2h1_cf_out[0], w_u_hb_idx_s_Q2_r0c0_k1h1_cf_out[0], w_u_hb_idx_s_Q2_r0c0_k0h1_cf_out[0]} : {138{1'b0}};   
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_ternary_ot_hbm_idx_score_quarter_static_h_sv__905746de = w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_eq_ot_hbm_idx_score_quarter_static_h_sv_37_54730_Y[0] ? {w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71537_Q[0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_vl_q[4:1], L188_i_q[32:1], w_u_hb_idx_s_Q2_r0c0_k2h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c0_k1h1_cs_out[31:0], w_u_hb_idx_s_Q2_r0c0_k0h1_cs_out[31:0], L188_i_q[0], w_u_hb_idx_s_Q2_r0c0_k2h1_cf_out[0], w_u_hb_idx_s_Q2_r0c0_k1h1_cf_out[0], w_u_hb_idx_s_Q2_r0c0_k0h1_cf_out[0]} : {138{1'b0}};   
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55671_Y = w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71521_Q[7:0] + {8{1'b0}};   
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55672_Y = w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71521_Q[7:0] + 8'b00000001;   
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55673_Y = w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71521_Q[7:0] + 8'b00000010;   
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55674_Y = w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71521_Q[7:0] + 8'b00000011;   
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55675_Y = w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71521_Q[7:0] + 8'b00000100;   
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55676_Y = w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71521_Q[7:0] + 8'b00000101;   
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55677_Y = w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71521_Q[7:0] + 8'b00000110;   
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55678_Y = w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71521_Q[7:0] + 8'b00000111;   
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_auto_proc_dff_cc_220_proc_dff_71533_Y = ~w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0];
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_auto_proc_dff_cc_220_proc_dff_71538_Y = ~w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0];
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_auto_proc_dff_cc_220_proc_dff_71543_Y = ~w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0];
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y = w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71557_Q[0] && w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[4];   
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_167_55670_Y = w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71559_Q[0] && w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[4];   
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y = w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_vl_q[0] && w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[4];   
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_logic_not_ot_hbm_idx_chunk_rt_h_sv_154_55666_Y = !w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0];   
    reg [31:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71508_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71508_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71508_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71508_q <= L188_i_q[32:1];   
    reg [0:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71509_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71509_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71509_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71509_q <= L188_i_q[0];   
    reg [31:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71510_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71510_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71510_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71510_q <= w_u_hb_idx_s_Q2_r0c0_k2h1_cs_out[31:0];   
    reg [0:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71511_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71511_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71511_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71511_q <= w_u_hb_idx_s_Q2_r0c0_k2h1_cf_out[0];   
    reg [31:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71512_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71512_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71512_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71512_q <= w_u_hb_idx_s_Q2_r0c0_k1h1_cs_out[31:0];   
    reg [0:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71513_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71513_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71513_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71513_q <= w_u_hb_idx_s_Q2_r0c0_k1h1_cf_out[0];   
    reg [31:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71514_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71514_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71514_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71514_q <= w_u_hb_idx_s_Q2_r0c0_k0h1_cs_out[31:0];   
    reg [0:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71515_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71515_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71515_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71515_q <= w_u_hb_idx_s_Q2_r0c0_k0h1_cf_out[0];   
    reg [0:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71516_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71516_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71516_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71516_q <= w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_196_55679_Y[0];   
    reg [3:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71517_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71517_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71517_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71517_q <= w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_vl_q[4:1];   
    reg [31:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71518_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71518_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71518_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71518_q <= 32'b00000000000000000000000000001000;   
    reg [567:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71519_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71519_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71519_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71519_q <= w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71558_Q[567:0];   
    reg [0:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71520_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71520_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71520_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71520_q <= w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_167_55670_Y[0];   
    reg [7:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71521_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71521_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71521_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71521_q <= w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71563_Q[7:0];   
    reg [0:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71522_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71522_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71522_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71522_q <= w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_logic_and_ot_hbm_idx_chunk_rt_h_sv_166_55669_Y[0];   
    reg [3:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71523_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71523_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71523_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71523_q <= w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71560_Q[3:0];   
    reg [2175:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71524_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71524_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71524_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71524_q <= w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_procdff_71561_Q[2175:0];   
    reg [7:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71525_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71525_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71525_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71525_q <= w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55671_Y[7:0];   
    reg [7:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71526_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71526_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71526_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71526_q <= w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55672_Y[7:0];   
    reg [7:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71527_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71527_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71527_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71527_q <= w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55673_Y[7:0];   
    reg [7:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71528_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71528_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71528_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71528_q <= w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55674_Y[7:0];   
    reg [7:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71529_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71529_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71529_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71529_q <= w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55675_Y[7:0];   
    reg [7:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71530_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71530_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71530_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71530_q <= w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55676_Y[7:0];   
    reg [7:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71531_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71531_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71531_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71531_q <= w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55677_Y[7:0];   
    reg [7:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71532_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71532_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71532_q;
    always @(posedge clk) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71532_q <= w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_add_ot_hbm_idx_chunk_rt_h_sv_171_55678_Y[7:0];   
    reg [0:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71537_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71537_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71537_q;
    always @(posedge clk or negedge w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0])
        if (!w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0]) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71537_q <= 1'b0; else g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71537_q <= w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_reduce_and_ot_hbm_idx_chunk_rt_h_sv_155_55667_Y[0];   
    reg [15:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71542_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71542_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71542_q;
    always @(posedge clk or negedge w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0])
        if (!w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0]) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71542_q <= 16'b0000000000000000; else g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71542_q <= {L188_i_q[34:33], w_u_hb_idx_s_Q2_r0c0_k3h0_prdy[1:0], w_u_hb_idx_s_Q2_r0c0_k2h1_prdy[1:0], w_u_hb_idx_s_Q2_r0c0_k2h0_prdy[1:0], w_u_hb_idx_s_Q2_r0c0_k1h1_prdy[1:0], w_u_hb_idx_s_Q2_r0c0_k1h0_prdy[1:0], w_u_hb_idx_s_Q2_r0c0_k0h1_prdy[1:0], w_u_hb_idx_s_Q2_r0c0_k0h0_prdy[1:0]};   
    reg [15:0] g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71547_q;
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71547_Q = g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71547_q;
    always @(posedge clk or negedge w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0])
        if (!w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0]) g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71547_q <= 16'b0000000000000000; else g_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71547_q <= w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71542_Q[15:0];   
    assign w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_reduce_and_ot_hbm_idx_chunk_rt_h_sv_155_55667_Y = &w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71547_Q[15:0];   
     
    ot_rst_delivered3 #(.REGIONS(1)) u_hb_idx_s_SW_scorer_g_delivered_reset_u_rr (
        .clk(clk),
        .rst_n(w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n),
        .rst_n_in(rst_n)
    );
     
    ot_rst_delivered3 #(.REGIONS(5)) u_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr (
        .clk(clk),
        .rst_n(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n),
        .rst_n_in(w_hb_idx_s_SW_scorer_g_delivered_reset_u_rr_rst_n[0])
    );
     
    ot_hdc_delay #(.D(0), .W(569)) u_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_qlate (
        .clk(clk),
        .d({w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71522_Q[0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71519_Q[567:0]}),
        .q(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_qlate_q),
        .rst_n(1'b1)
    );
     
    ot_hdc_delay #(.D(104), .RESET(1), .W(5)) u_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_vl (
        .clk(clk),
        .d({w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71523_Q[3:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71520_Q[0]}),
        .q(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_vl_q),
        .rst_n(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[4])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c0_k0h0 (
        .cf_out(w_u_hb_idx_s_Q2_r0c0_k0h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q2_r0c0_k0h0_cs_out),
        .hid4({w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71528_Q[7:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71527_Q[7:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71526_Q[7:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71524_Q[543:0]),
        .prdy(w_u_hb_idx_s_Q2_r0c0_k0h0_prdy),
        .q_b(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[0])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c0_k0h1 (
        .cf_in(w_u_hb_idx_s_Q2_r0c0_k0h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q2_r0c0_k0h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q2_r0c0_k0h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q2_r0c0_k0h1_cs_out),
        .hid4({w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71532_Q[7:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71531_Q[7:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71530_Q[7:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71524_Q[543:0]),
        .prdy(w_u_hb_idx_s_Q2_r0c0_k0h1_prdy),
        .q_b(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[0])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c0_k1h0 (
        .cf_out(w_u_hb_idx_s_Q2_r0c0_k1h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q2_r0c0_k1h0_cs_out),
        .hid4({w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71528_Q[7:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71527_Q[7:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71526_Q[7:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71524_Q[1087:544]),
        .prdy(w_u_hb_idx_s_Q2_r0c0_k1h0_prdy),
        .q_b(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[1])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c0_k1h1 (
        .cf_in(w_u_hb_idx_s_Q2_r0c0_k1h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q2_r0c0_k1h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q2_r0c0_k1h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q2_r0c0_k1h1_cs_out),
        .hid4({w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71532_Q[7:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71531_Q[7:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71530_Q[7:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71524_Q[1087:544]),
        .prdy(w_u_hb_idx_s_Q2_r0c0_k1h1_prdy),
        .q_b(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[1])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c0_k2h0 (
        .cf_out(w_u_hb_idx_s_Q2_r0c0_k2h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q2_r0c0_k2h0_cs_out),
        .hid4({w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71528_Q[7:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71527_Q[7:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71526_Q[7:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71524_Q[1631:1088]),
        .prdy(w_u_hb_idx_s_Q2_r0c0_k2h0_prdy),
        .q_b(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[2])
    );
     
    ot_hbm_idx_score_hcol_h1 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c0_k2h1 (
        .cf_in(w_u_hb_idx_s_Q2_r0c0_k2h0_cf_out[0]),
        .cf_out(w_u_hb_idx_s_Q2_r0c0_k2h1_cf_out),
        .clk_pair({clk, clk}),
        .cs_in(w_u_hb_idx_s_Q2_r0c0_k2h0_cs_out[31:0]),
        .cs_out(w_u_hb_idx_s_Q2_r0c0_k2h1_cs_out),
        .hid4({w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71532_Q[7:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71531_Q[7:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71530_Q[7:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71529_Q[7:0]}),
        .key(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71524_Q[1631:1088]),
        .prdy(w_u_hb_idx_s_Q2_r0c0_k2h1_prdy),
        .q_b(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[2])
    );
     
    ot_hbm_idx_score_hcol_h0 #(.DELIVERED_RESET(1), .MUT(0)) u_u_hb_idx_s_Q2_r0c0_k3h0 (
        .cf_out(w_u_hb_idx_s_Q2_r0c0_k3h0_cf_out),
        .clk_pair({clk, clk}),
        .cs_out(w_u_hb_idx_s_Q2_r0c0_k3h0_cs_out),
        .hid4({w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71528_Q[7:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71527_Q[7:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71526_Q[7:0], w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71525_Q[7:0]}),
        .key(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_procdff_71524_Q[2175:1632]),
        .prdy(w_u_hb_idx_s_Q2_r0c0_k3h0_prdy),
        .q_b(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_qlate_q[567:0]),
        .qv_b(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_u_qlate_q[568]),
        .rst_col(w_hb_idx_s_SW_scorer_ge_0_gc_0_leaf_core_g_delivered_reset_u_rr_rst_n[3])
    );
    reg [31:0] g_u_hcb_Q0_procdff_69249_q;
    assign w_u_hcb_Q0_procdff_69249_Q = g_u_hcb_Q0_procdff_69249_q;
    always @(posedge clk) g_u_hcb_Q0_procdff_69249_q <= 32'b00000000000000000000000000000010;   
    reg [4096:0] g_u_hcb_Q0_procdff_69250_q;
    assign w_u_hcb_Q0_procdff_69250_Q = g_u_hcb_Q0_procdff_69250_q;
    always @(posedge clk) g_u_hcb_Q0_procdff_69250_q <= L20_i_q[4096:0];   
    reg [4096:0] g_u_hcb_Q0_procdff_69251_q;
    assign w_u_hcb_Q0_procdff_69251_Q = g_u_hcb_Q0_procdff_69251_q;
    always @(posedge clk) g_u_hcb_Q0_procdff_69251_q <= w_u_hcb_Q0_procdff_69250_Q[4096:0];   
     
    ot_hbm_hc_bank128_pair_first_core u_u_hcb_Q0_ot_hbm_hc_bank128_pair0 (
        .clk(clk),
        .fault(w_u_hcb_Q0_ot_hbm_hc_bank128_pair0_fault),
        .go(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71644_Q[0]),
        .lane_valid(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71645_Q[15:0]),
        .rst_n(w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0]),
        .square(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71646_Q[15:0]),
        .sum_out(w_u_hcb_Q0_ot_hbm_hc_bank128_pair0_sum_out),
        .weight_addr(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71648_Q[9:0]),
        .weight_read(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71669_Q[0]),
        .weight_we0(w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54673_Y[0]),
        .weight_we1(w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54675_Y[0]),
        .write_addr(w_u_hcb_Q0_u_c_u_b_procdff_71774_Q[9:0]),
        .write_data(w_u_hcb_Q0_u_c_u_b_procdff_71775_Q[511:0]),
        .x_addr(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71649_Q[6:0]),
        .x_read(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71674_Q[0]),
        .x_write(w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54705_Y[0])
    );
     
    ot_hbm_hc_bank128_pair_first_core u_u_hcb_Q0_ot_hbm_hc_bank128_pair1 (
        .clk(clk),
        .fault(w_u_hcb_Q0_ot_hbm_hc_bank128_pair1_fault),
        .go(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71644_Q[0]),
        .lane_valid(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71645_Q[31:16]),
        .rst_n(w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0]),
        .square(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71646_Q[31:16]),
        .sum_out(w_u_hcb_Q0_ot_hbm_hc_bank128_pair1_sum_out),
        .weight_addr(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71648_Q[9:0]),
        .weight_read(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71669_Q[0]),
        .weight_we0(w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54677_Y[0]),
        .weight_we1(w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54679_Y[0]),
        .write_addr(w_u_hcb_Q0_u_c_u_b_procdff_71774_Q[9:0]),
        .write_data(w_u_hcb_Q0_u_c_u_b_procdff_71775_Q[1023:512]),
        .x_addr(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71649_Q[6:0]),
        .x_read(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71674_Q[0]),
        .x_write(w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54707_Y[0])
    );
     
    ot_hbm_hc_bank128_pair_first_core u_u_hcb_Q0_ot_hbm_hc_bank128_pair2 (
        .clk(clk),
        .fault(w_u_hcb_Q0_ot_hbm_hc_bank128_pair2_fault),
        .go(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71644_Q[0]),
        .lane_valid(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71645_Q[47:32]),
        .rst_n(w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0]),
        .square(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71646_Q[47:32]),
        .sum_out(w_u_hcb_Q0_ot_hbm_hc_bank128_pair2_sum_out),
        .weight_addr(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71648_Q[9:0]),
        .weight_read(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71669_Q[0]),
        .weight_we0(w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54681_Y[0]),
        .weight_we1(w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54683_Y[0]),
        .write_addr(w_u_hcb_Q0_u_c_u_b_procdff_71774_Q[9:0]),
        .write_data(w_u_hcb_Q0_u_c_u_b_procdff_71775_Q[511:0]),
        .x_addr(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71649_Q[6:0]),
        .x_read(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71674_Q[0]),
        .x_write(w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54709_Y[0])
    );
     
    ot_hbm_hc_bank128_pair_first_core u_u_hcb_Q0_ot_hbm_hc_bank128_pair3 (
        .clk(clk),
        .fault(w_u_hcb_Q0_ot_hbm_hc_bank128_pair3_fault),
        .go(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71644_Q[0]),
        .lane_valid(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71645_Q[63:48]),
        .rst_n(w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0]),
        .square(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71646_Q[63:48]),
        .sum_out(w_u_hcb_Q0_ot_hbm_hc_bank128_pair3_sum_out),
        .weight_addr(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71648_Q[9:0]),
        .weight_read(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71669_Q[0]),
        .weight_we0(w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54685_Y[0]),
        .weight_we1(w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54687_Y[0]),
        .write_addr(w_u_hcb_Q0_u_c_u_b_procdff_71774_Q[9:0]),
        .write_data(w_u_hcb_Q0_u_c_u_b_procdff_71775_Q[1023:512]),
        .x_addr(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71649_Q[6:0]),
        .x_read(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71674_Q[0]),
        .x_write(w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54711_Y[0])
    );
     
    ot_hbm_hc_bank128_pair_first_core u_u_hcb_Q0_ot_hbm_hc_bank128_pair4 (
        .clk(clk),
        .fault(w_u_hcb_Q0_ot_hbm_hc_bank128_pair4_fault),
        .go(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71644_Q[0]),
        .lane_valid(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71645_Q[79:64]),
        .rst_n(w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0]),
        .square(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71646_Q[79:64]),
        .sum_out(w_u_hcb_Q0_ot_hbm_hc_bank128_pair4_sum_out),
        .weight_addr(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71648_Q[9:0]),
        .weight_read(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71669_Q[0]),
        .weight_we0(w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54689_Y[0]),
        .weight_we1(w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54691_Y[0]),
        .write_addr(w_u_hcb_Q0_u_c_u_b_procdff_71774_Q[9:0]),
        .write_data(w_u_hcb_Q0_u_c_u_b_procdff_71775_Q[511:0]),
        .x_addr(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71649_Q[6:0]),
        .x_read(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71674_Q[0]),
        .x_write(w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54713_Y[0])
    );
     
    ot_hbm_hc_bank128_pair_first_core u_u_hcb_Q0_ot_hbm_hc_bank128_pair5 (
        .clk(clk),
        .fault(w_u_hcb_Q0_ot_hbm_hc_bank128_pair5_fault),
        .go(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71644_Q[0]),
        .lane_valid(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71645_Q[95:80]),
        .rst_n(w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0]),
        .square(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71646_Q[95:80]),
        .sum_out(w_u_hcb_Q0_ot_hbm_hc_bank128_pair5_sum_out),
        .weight_addr(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71648_Q[9:0]),
        .weight_read(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71669_Q[0]),
        .weight_we0(w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54693_Y[0]),
        .weight_we1(w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54695_Y[0]),
        .write_addr(w_u_hcb_Q0_u_c_u_b_procdff_71774_Q[9:0]),
        .write_data(w_u_hcb_Q0_u_c_u_b_procdff_71775_Q[1023:512]),
        .x_addr(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71649_Q[6:0]),
        .x_read(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71674_Q[0]),
        .x_write(w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54715_Y[0])
    );
     
    ot_hbm_hc_bank128_pair_first_core u_u_hcb_Q0_ot_hbm_hc_bank128_pair6 (
        .clk(clk),
        .fault(w_u_hcb_Q0_ot_hbm_hc_bank128_pair6_fault),
        .go(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71644_Q[0]),
        .lane_valid(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71645_Q[111:96]),
        .rst_n(w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0]),
        .square(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71646_Q[111:96]),
        .sum_out(w_u_hcb_Q0_ot_hbm_hc_bank128_pair6_sum_out),
        .weight_addr(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71648_Q[9:0]),
        .weight_read(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71669_Q[0]),
        .weight_we0(w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54697_Y[0]),
        .weight_we1(w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54699_Y[0]),
        .write_addr(w_u_hcb_Q0_u_c_u_b_procdff_71774_Q[9:0]),
        .write_data(w_u_hcb_Q0_u_c_u_b_procdff_71775_Q[511:0]),
        .x_addr(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71649_Q[6:0]),
        .x_read(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71674_Q[0]),
        .x_write(w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54717_Y[0])
    );
     
    ot_hbm_hc_bank128_pair_first_core u_u_hcb_Q0_ot_hbm_hc_bank128_pair7 (
        .clk(clk),
        .fault(w_u_hcb_Q0_ot_hbm_hc_bank128_pair7_fault),
        .go(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71644_Q[0]),
        .lane_valid(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71645_Q[127:112]),
        .rst_n(w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0]),
        .square(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71646_Q[127:112]),
        .sum_out(w_u_hcb_Q0_ot_hbm_hc_bank128_pair7_sum_out),
        .weight_addr(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71648_Q[9:0]),
        .weight_read(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71669_Q[0]),
        .weight_we0(w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54701_Y[0]),
        .weight_we1(w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54703_Y[0]),
        .write_addr(w_u_hcb_Q0_u_c_u_b_procdff_71774_Q[9:0]),
        .write_data(w_u_hcb_Q0_u_c_u_b_procdff_71775_Q[1023:512]),
        .x_addr(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71649_Q[6:0]),
        .x_read(w_u_hcb_Q0_u_c_u_b_u_st_procdff_71674_Q[0]),
        .x_write(w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54719_Y[0])
    );
    assign w_u_hcb_Q0_u_c_auto_proc_dff_cc_220_proc_dff_71791_Y = ~w_u_hcb_Q0_u_c_u_rst_rst_n[0];
    assign w_u_hcb_Q0_u_c_auto_proc_dff_cc_220_proc_dff_71796_Y = ~w_u_hcb_Q0_u_c_u_rst_rst_n[0];
    assign w_u_hcb_Q0_u_c_auto_proc_dff_cc_220_proc_dff_71801_Y = ~w_u_hcb_Q0_u_c_u_rst_rst_n[0];
    assign w_u_hcb_Q0_u_c_auto_proc_dff_cc_220_proc_dff_71806_Y = ~w_u_hcb_Q0_u_c_u_rst_rst_n[0];
    assign w_u_hcb_Q0_u_c_auto_proc_dff_cc_220_proc_dff_71818_Y = ~w_u_hcb_Q0_u_c_u_rst_rst_n[0];
    assign w_u_hcb_Q0_u_c_eq_ot_hbm_hc_bankq_static_sv_50_54435_Y = !w_u_hcb_Q0_u_c_procdff_71813_Q[1:0];   
    assign w_u_hcb_Q0_u_c_eq_ot_hbm_hc_bankq_static_sv_50_54437_Y = w_u_hcb_Q0_u_c_procdff_71813_Q[1:0] == 2'b01;   
    assign w_u_hcb_Q0_u_c_eq_ot_hbm_hc_bankq_static_sv_50_54439_Y = w_u_hcb_Q0_u_c_procdff_71813_Q[1:0] == 2'b10;   
    assign w_u_hcb_Q0_u_c_logic_and_ot_hbm_hc_bankq_static_sv_50_54436_Y = w_u_hcb_Q0_u_c_procdff_71822_Q[0] && w_u_hcb_Q0_u_c_eq_ot_hbm_hc_bankq_static_sv_50_54435_Y[0];   
    assign w_u_hcb_Q0_u_c_logic_and_ot_hbm_hc_bankq_static_sv_50_54438_Y = w_u_hcb_Q0_u_c_procdff_71822_Q[0] && w_u_hcb_Q0_u_c_eq_ot_hbm_hc_bankq_static_sv_50_54437_Y[0];   
    assign w_u_hcb_Q0_u_c_logic_and_ot_hbm_hc_bankq_static_sv_50_54440_Y = w_u_hcb_Q0_u_c_procdff_71822_Q[0] && w_u_hcb_Q0_u_c_eq_ot_hbm_hc_bankq_static_sv_50_54439_Y[0];   
    assign w_u_hcb_Q0_u_c_logic_and_ot_hbm_hc_bankq_static_sv_61_54477_Y = w_u_hcb_Q0_u_c_procdff_71810_Q[0] && w_u_hcb_Q0_u_c_procdff_71811_Q[0];   
    assign w_u_hcb_Q0_u_c_logic_not_ot_hbm_hc_bankq_static_sv_47_54432_Y = !w_u_hcb_Q0_u_c_u_rst_rst_n[0];   
    assign w_u_hcb_Q0_u_c_logic_not_ot_hbm_hc_bankq_static_sv_60_54476_Y = !w_u_hcb_Q0_u_c_u_rst_rst_n[0];   
    assign w_u_hcb_Q0_u_c_logic_not_ot_hbm_hc_bankq_static_sv_82_54479_Y = !w_u_hcb_Q0_u_c_u_rst_rst_n[0];   
    reg [0:0] g_u_hcb_Q0_u_c_procdff_71786_q;
    assign w_u_hcb_Q0_u_c_procdff_71786_Q = g_u_hcb_Q0_u_c_procdff_71786_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_procdff_71786_q <= w_u_hcb_Q0_u_c_u_b_u_st_procdff_71659_Q[28];   
    reg [7:0] g_u_hcb_Q0_u_c_procdff_71787_q;
    assign w_u_hcb_Q0_u_c_procdff_71787_Q = g_u_hcb_Q0_u_c_procdff_71787_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_procdff_71787_q <= w_u_hcb_Q0_u_c_u_b_u_st_procdff_71659_Q[27:20];   
    reg [9:0] g_u_hcb_Q0_u_c_procdff_71788_q;
    assign w_u_hcb_Q0_u_c_procdff_71788_Q = g_u_hcb_Q0_u_c_procdff_71788_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_procdff_71788_q <= w_u_hcb_Q0_u_c_u_b_u_st_procdff_71659_Q[19:10];   
    reg [9:0] g_u_hcb_Q0_u_c_procdff_71789_q;
    assign w_u_hcb_Q0_u_c_procdff_71789_Q = g_u_hcb_Q0_u_c_procdff_71789_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_procdff_71789_q <= w_u_hcb_Q0_u_c_u_b_u_st_procdff_71659_Q[9:0];   
    reg [4095:0] g_u_hcb_Q0_u_c_procdff_71790_q;
    assign w_u_hcb_Q0_u_c_procdff_71790_Q = g_u_hcb_Q0_u_c_procdff_71790_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_procdff_71790_q <= {w_u_hcb_Q0_ot_hbm_hc_bank128_pair7_sum_out[511:0], w_u_hcb_Q0_ot_hbm_hc_bank128_pair6_sum_out[511:0], w_u_hcb_Q0_ot_hbm_hc_bank128_pair5_sum_out[511:0], w_u_hcb_Q0_ot_hbm_hc_bank128_pair4_sum_out[511:0], w_u_hcb_Q0_ot_hbm_hc_bank128_pair3_sum_out[511:0], w_u_hcb_Q0_ot_hbm_hc_bank128_pair2_sum_out[511:0], w_u_hcb_Q0_ot_hbm_hc_bank128_pair1_sum_out[511:0], w_u_hcb_Q0_ot_hbm_hc_bank128_pair0_sum_out[511:0]};   
    reg [0:0] g_u_hcb_Q0_u_c_procdff_71795_q;
    assign w_u_hcb_Q0_u_c_procdff_71795_Q = g_u_hcb_Q0_u_c_procdff_71795_q;
    always @(posedge clk or negedge w_u_hcb_Q0_u_c_u_rst_rst_n[0])
        if (!w_u_hcb_Q0_u_c_u_rst_rst_n[0]) g_u_hcb_Q0_u_c_procdff_71795_q <= 1'b0; else g_u_hcb_Q0_u_c_procdff_71795_q <= w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[8];   
    reg [0:0] g_u_hcb_Q0_u_c_procdff_71800_q;
    assign w_u_hcb_Q0_u_c_procdff_71800_Q = g_u_hcb_Q0_u_c_procdff_71800_q;
    always @(posedge clk or negedge w_u_hcb_Q0_u_c_u_rst_rst_n[0])
        if (!w_u_hcb_Q0_u_c_u_rst_rst_n[0]) g_u_hcb_Q0_u_c_procdff_71800_q <= 1'b0; else g_u_hcb_Q0_u_c_procdff_71800_q <= w_u_hcb_Q0_u_c_u_b_u_st_procdff_71664_Q[0];   
    reg [0:0] g_u_hcb_Q0_u_c_procdff_71805_q;
    assign w_u_hcb_Q0_u_c_procdff_71805_Q = g_u_hcb_Q0_u_c_procdff_71805_q;
    always @(posedge clk or negedge w_u_hcb_Q0_u_c_u_rst_rst_n[0])
        if (!w_u_hcb_Q0_u_c_u_rst_rst_n[0]) g_u_hcb_Q0_u_c_procdff_71805_q <= 1'b0; else g_u_hcb_Q0_u_c_procdff_71805_q <= w_u_hcb_Q0_u_c_procmux_66661_Y[0];   
    reg [0:0] g_u_hcb_Q0_u_c_procdff_71810_q;
    assign w_u_hcb_Q0_u_c_procdff_71810_Q = g_u_hcb_Q0_u_c_procdff_71810_q;
    always @(posedge clk or negedge w_u_hcb_Q0_u_c_u_rst_rst_n[0])
        if (!w_u_hcb_Q0_u_c_u_rst_rst_n[0]) g_u_hcb_Q0_u_c_procdff_71810_q <= 1'b0; else g_u_hcb_Q0_u_c_procdff_71810_q <= L65_i_q[43];   
    reg [0:0] g_u_hcb_Q0_u_c_procdff_71811_q;
    assign w_u_hcb_Q0_u_c_procdff_71811_Q = g_u_hcb_Q0_u_c_procdff_71811_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_procdff_71811_q <= w_u_hcb_Q0_u_c_procmux_66725_Y[0];   
    reg [31:0] g_u_hcb_Q0_u_c_procdff_71812_q;
    assign w_u_hcb_Q0_u_c_procdff_71812_Q = g_u_hcb_Q0_u_c_procdff_71812_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_procdff_71812_q <= 32'b00000000000000000000000000100000;   
    reg [1:0] g_u_hcb_Q0_u_c_procdff_71813_q;
    assign w_u_hcb_Q0_u_c_procdff_71813_Q = g_u_hcb_Q0_u_c_procdff_71813_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_procdff_71813_q <= L65_i_q[302:301];   
    reg [255:0] g_u_hcb_Q0_u_c_procdff_71814_q;
    assign w_u_hcb_Q0_u_c_procdff_71814_Q = g_u_hcb_Q0_u_c_procdff_71814_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_procdff_71814_q <= L65_i_q[300:45];   
    reg [767:0] g_u_hcb_Q0_u_c_procdff_71815_q;
    assign w_u_hcb_Q0_u_c_procdff_71815_Q = g_u_hcb_Q0_u_c_procdff_71815_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_procdff_71815_q <= {w_u_hcb_Q0_u_c_procmux_66727_Y[255:0], w_u_hcb_Q0_u_c_procmux_66729_Y[255:0], w_u_hcb_Q0_u_c_procmux_66731_Y[255:0]};   
    reg [1023:0] g_u_hcb_Q0_u_c_procdff_71816_q;
    assign w_u_hcb_Q0_u_c_procdff_71816_Q = g_u_hcb_Q0_u_c_procdff_71816_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_procdff_71816_q <= {w_u_hcb_Q0_u_c_procdff_71814_Q[255:0], w_u_hcb_Q0_u_c_procdff_71815_Q[767:0]};   
    reg [31:0] g_u_hcb_Q0_u_c_procdff_71817_q;
    assign w_u_hcb_Q0_u_c_procdff_71817_Q = g_u_hcb_Q0_u_c_procdff_71817_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_procdff_71817_q <= 32'b00000000000000000000000000000011;   
    reg [0:0] g_u_hcb_Q0_u_c_procdff_71822_q;
    assign w_u_hcb_Q0_u_c_procdff_71822_Q = g_u_hcb_Q0_u_c_procdff_71822_q;
    always @(posedge clk or negedge w_u_hcb_Q0_u_c_u_rst_rst_n[0])
        if (!w_u_hcb_Q0_u_c_u_rst_rst_n[0]) g_u_hcb_Q0_u_c_procdff_71822_q <= 1'b0; else g_u_hcb_Q0_u_c_procdff_71822_q <= L65_i_q[303];   
    assign w_u_hcb_Q0_u_c_procmux_66661_Y = w_u_hcb_Q0_u_c_logic_and_ot_hbm_hc_bankq_static_sv_61_54477_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procdff_71805_Q[0];   
    assign w_u_hcb_Q0_u_c_procmux_66663_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54443_Y[0] ? 1'b1 : 1'b0;   
    assign w_u_hcb_Q0_u_c_procmux_66665_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54444_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66663_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66667_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54445_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66665_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66669_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54446_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66667_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66671_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54447_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66669_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66673_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54448_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66671_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66675_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54449_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66673_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66677_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54450_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66675_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66679_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54451_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66677_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66681_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54452_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66679_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66683_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54453_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66681_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66685_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54454_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66683_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66687_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54455_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66685_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66689_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54456_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66687_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66691_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54457_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66689_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66693_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54458_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66691_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66695_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54459_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66693_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66697_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54460_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66695_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66699_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54461_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66697_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66701_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54462_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66699_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66703_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54463_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66701_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66705_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54464_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66703_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66707_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54465_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66705_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66709_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54466_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66707_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66711_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54467_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66709_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66713_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54468_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66711_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66715_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54469_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66713_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66717_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54470_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66715_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66719_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54471_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66717_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66721_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54472_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66719_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66723_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54473_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66721_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66725_Y = w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54474_Y[0] ? 1'b1 : w_u_hcb_Q0_u_c_procmux_66723_Y[0];   
    assign w_u_hcb_Q0_u_c_procmux_66727_Y = w_u_hcb_Q0_u_c_logic_and_ot_hbm_hc_bankq_static_sv_50_54440_Y[0] ? w_u_hcb_Q0_u_c_procdff_71814_Q[255:0] : w_u_hcb_Q0_u_c_procdff_71815_Q[767:512];   
    assign w_u_hcb_Q0_u_c_procmux_66729_Y = w_u_hcb_Q0_u_c_logic_and_ot_hbm_hc_bankq_static_sv_50_54438_Y[0] ? w_u_hcb_Q0_u_c_procdff_71814_Q[255:0] : w_u_hcb_Q0_u_c_procdff_71815_Q[511:256];   
    assign w_u_hcb_Q0_u_c_procmux_66731_Y = w_u_hcb_Q0_u_c_logic_and_ot_hbm_hc_bankq_static_sv_50_54436_Y[0] ? w_u_hcb_Q0_u_c_procdff_71814_Q[255:0] : w_u_hcb_Q0_u_c_procdff_71815_Q[255:0];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54443_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[15:0];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54444_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[47:32];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54445_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[79:64];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54446_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[111:96];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54447_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[143:128];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54448_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[175:160];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54449_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[207:192];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54450_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[239:224];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54451_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[271:256];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54452_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[303:288];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54453_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[335:320];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54454_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[367:352];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54455_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[399:384];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54456_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[431:416];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54457_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[463:448];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54458_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[495:480];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54459_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[527:512];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54460_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[559:544];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54461_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[591:576];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54462_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[623:608];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54463_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[655:640];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54464_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[687:672];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54465_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[719:704];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54466_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[751:736];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54467_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[783:768];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54468_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[815:800];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54469_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[847:832];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54470_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[879:864];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54471_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[911:896];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54472_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[943:928];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54473_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[975:960];   
    assign w_u_hcb_Q0_u_c_reduce_or_ot_hbm_hc_bankq_static_sv_57_54474_Y = |w_u_hcb_Q0_u_c_procdff_71816_Q[1007:992];   
    assign w_u_hcb_Q0_u_c_u_b_auto_proc_dff_cc_220_proc_dff_71776_Y = ~w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[1];
    assign w_u_hcb_Q0_u_c_u_b_auto_proc_dff_cc_220_proc_dff_71781_Y = ~w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[1];
    assign w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54672_Y = !w_u_hcb_Q0_u_c_u_b_procdff_71773_Q[1:0];   
    assign w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54674_Y = !w_u_hcb_Q0_u_c_u_b_procdff_71773_Q[1:0];   
    assign w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54676_Y = !w_u_hcb_Q0_u_c_u_b_procdff_71773_Q[1:0];   
    assign w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54678_Y = !w_u_hcb_Q0_u_c_u_b_procdff_71773_Q[1:0];   
    assign w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54680_Y = w_u_hcb_Q0_u_c_u_b_procdff_71773_Q[1:0] == 2'b01;   
    assign w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54682_Y = w_u_hcb_Q0_u_c_u_b_procdff_71773_Q[1:0] == 2'b01;   
    assign w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54684_Y = w_u_hcb_Q0_u_c_u_b_procdff_71773_Q[1:0] == 2'b01;   
    assign w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54686_Y = w_u_hcb_Q0_u_c_u_b_procdff_71773_Q[1:0] == 2'b01;   
    assign w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54688_Y = w_u_hcb_Q0_u_c_u_b_procdff_71773_Q[1:0] == 2'b10;   
    assign w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54690_Y = w_u_hcb_Q0_u_c_u_b_procdff_71773_Q[1:0] == 2'b10;   
    assign w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54692_Y = w_u_hcb_Q0_u_c_u_b_procdff_71773_Q[1:0] == 2'b10;   
    assign w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54694_Y = w_u_hcb_Q0_u_c_u_b_procdff_71773_Q[1:0] == 2'b10;   
    assign w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54696_Y = w_u_hcb_Q0_u_c_u_b_procdff_71773_Q[1:0] == {2{1'b1}};   
    assign w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54698_Y = w_u_hcb_Q0_u_c_u_b_procdff_71773_Q[1:0] == {2{1'b1}};   
    assign w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54700_Y = w_u_hcb_Q0_u_c_u_b_procdff_71773_Q[1:0] == {2{1'b1}};   
    assign w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54702_Y = w_u_hcb_Q0_u_c_u_b_procdff_71773_Q[1:0] == {2{1'b1}};   
    assign w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54704_Y = !w_u_hcb_Q0_u_c_u_b_procdff_71773_Q[1:0];   
    assign w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54706_Y = !w_u_hcb_Q0_u_c_u_b_procdff_71773_Q[1:0];   
    assign w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54708_Y = w_u_hcb_Q0_u_c_u_b_procdff_71773_Q[1:0] == 2'b01;   
    assign w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54710_Y = w_u_hcb_Q0_u_c_u_b_procdff_71773_Q[1:0] == 2'b01;   
    assign w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54712_Y = w_u_hcb_Q0_u_c_u_b_procdff_71773_Q[1:0] == 2'b10;   
    assign w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54714_Y = w_u_hcb_Q0_u_c_u_b_procdff_71773_Q[1:0] == 2'b10;   
    assign w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54716_Y = w_u_hcb_Q0_u_c_u_b_procdff_71773_Q[1:0] == {2{1'b1}};   
    assign w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54718_Y = w_u_hcb_Q0_u_c_u_b_procdff_71773_Q[1:0] == {2{1'b1}};   
    assign w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54673_Y = w_u_hcb_Q0_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54672_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54675_Y = w_u_hcb_Q0_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54674_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54677_Y = w_u_hcb_Q0_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54676_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54679_Y = w_u_hcb_Q0_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54678_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54681_Y = w_u_hcb_Q0_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54680_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54683_Y = w_u_hcb_Q0_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54682_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54685_Y = w_u_hcb_Q0_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54684_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54687_Y = w_u_hcb_Q0_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54686_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54689_Y = w_u_hcb_Q0_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54688_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54691_Y = w_u_hcb_Q0_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54690_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54693_Y = w_u_hcb_Q0_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54692_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54695_Y = w_u_hcb_Q0_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54694_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54697_Y = w_u_hcb_Q0_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54696_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54699_Y = w_u_hcb_Q0_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54698_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54701_Y = w_u_hcb_Q0_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54700_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_74_54703_Y = w_u_hcb_Q0_u_c_u_b_procdff_71780_Q[0] && w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_74_54702_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54705_Y = w_u_hcb_Q0_u_c_u_b_procdff_71785_Q[0] && w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54704_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54707_Y = w_u_hcb_Q0_u_c_u_b_procdff_71785_Q[0] && w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54706_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54709_Y = w_u_hcb_Q0_u_c_u_b_procdff_71785_Q[0] && w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54708_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54711_Y = w_u_hcb_Q0_u_c_u_b_procdff_71785_Q[0] && w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54710_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54713_Y = w_u_hcb_Q0_u_c_u_b_procdff_71785_Q[0] && w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54712_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54715_Y = w_u_hcb_Q0_u_c_u_b_procdff_71785_Q[0] && w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54714_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54717_Y = w_u_hcb_Q0_u_c_u_b_procdff_71785_Q[0] && w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54716_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_logic_and_ot_hbm_hc_bank_static_sv_84_54719_Y = w_u_hcb_Q0_u_c_u_b_procdff_71785_Q[0] && w_u_hcb_Q0_u_c_u_b_eq_ot_hbm_hc_bank_static_sv_84_54718_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_logic_not_ot_hbm_hc_bank_static_sv_59_54669_Y = !w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[1];   
    reg [1:0] g_u_hcb_Q0_u_c_u_b_procdff_71773_q;
    assign w_u_hcb_Q0_u_c_u_b_procdff_71773_Q = g_u_hcb_Q0_u_c_u_b_procdff_71773_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_u_b_procdff_71773_q <= L65_i_q[31:30];   
    reg [9:0] g_u_hcb_Q0_u_c_u_b_procdff_71774_q;
    assign w_u_hcb_Q0_u_c_u_b_procdff_71774_Q = g_u_hcb_Q0_u_c_u_b_procdff_71774_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_u_b_procdff_71774_q <= L65_i_q[41:32];   
    reg [1023:0] g_u_hcb_Q0_u_c_u_b_procdff_71775_q;
    assign w_u_hcb_Q0_u_c_u_b_procdff_71775_Q = g_u_hcb_Q0_u_c_u_b_procdff_71775_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_u_b_procdff_71775_q <= w_u_hcb_Q0_u_c_procdff_71816_Q[1023:0];   
    reg [0:0] g_u_hcb_Q0_u_c_u_b_procdff_71780_q;
    assign w_u_hcb_Q0_u_c_u_b_procdff_71780_Q = g_u_hcb_Q0_u_c_u_b_procdff_71780_q;
    always @(posedge clk or negedge w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[1])
        if (!w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[1]) g_u_hcb_Q0_u_c_u_b_procdff_71780_q <= 1'b0; else g_u_hcb_Q0_u_c_u_b_procdff_71780_q <= L65_i_q[42];   
    reg [0:0] g_u_hcb_Q0_u_c_u_b_procdff_71785_q;
    assign w_u_hcb_Q0_u_c_u_b_procdff_71785_Q = g_u_hcb_Q0_u_c_u_b_procdff_71785_q;
    always @(posedge clk or negedge w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[1])
        if (!w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[1]) g_u_hcb_Q0_u_c_u_b_procdff_71785_q <= 1'b0; else g_u_hcb_Q0_u_c_u_b_procdff_71785_q <= L65_i_q[43];   
     
    ot_rst_relay #(.REGIONS(2)) u_u_hcb_Q0_u_c_u_b_g_rr_u_rst (
        .clk(clk),
        .rst_n(w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n),
        .rst_n_in(L65_i_q[44])
    );
    assign w_u_hcb_Q0_u_c_u_b_u_st_auto_proc_dff_cc_220_proc_dff_71640_Y = ~w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0];
    assign w_u_hcb_Q0_u_c_u_b_u_st_auto_proc_dff_cc_220_proc_dff_71660_Y = ~w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0];
    assign w_u_hcb_Q0_u_c_u_b_u_st_auto_proc_dff_cc_220_proc_dff_71665_Y = ~w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0];
    assign w_u_hcb_Q0_u_c_u_b_u_st_auto_proc_dff_cc_220_proc_dff_71670_Y = ~w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0];
    assign w_u_hcb_Q0_u_c_u_b_u_st_auto_proc_dff_cc_220_proc_dff_71675_Y = ~w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0];
    assign w_u_hcb_Q0_u_c_u_b_u_st_auto_proc_dff_cc_220_proc_dff_71680_Y = ~w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0];
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_669_55081_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[0] && w_u_hcb_Q0_u_c_u_b_u_st_logic_not_ot_hdc_v41x_hcp_sv_669_55080_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55088_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55087_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55090_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55089_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55092_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55091_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55094_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55093_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55096_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55095_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55098_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55097_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55100_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55099_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55102_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55101_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55104_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55103_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55106_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55105_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55108_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55107_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55110_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55109_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55112_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55111_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55114_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55113_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55116_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55115_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55118_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55117_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55120_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55119_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55122_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55121_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55124_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55123_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55126_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55125_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55128_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55127_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55130_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55129_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55132_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55131_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55134_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55133_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55136_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55135_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55138_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55137_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55140_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55139_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55142_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55141_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55144_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55143_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55146_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55145_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55148_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55147_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55150_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55149_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55152_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55151_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55154_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55153_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55156_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55155_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55158_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55157_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55160_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55159_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55162_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55161_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55164_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55163_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55166_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55165_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55168_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55167_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55170_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55169_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55172_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55171_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55174_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55173_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55176_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55175_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55178_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55177_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55180_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55179_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55182_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55181_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55184_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55183_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55186_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55185_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55188_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55187_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55190_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55189_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55192_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55191_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55194_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55193_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55196_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55195_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55198_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55197_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55200_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55199_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55202_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55201_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55204_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55203_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55206_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55205_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55208_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55207_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55210_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55209_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55212_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55211_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55214_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55213_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55216_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55215_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55218_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55217_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55220_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55219_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55222_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55221_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55224_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55223_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55226_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55225_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55228_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55227_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55230_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55229_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55232_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55231_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55234_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55233_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55236_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55235_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55238_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55237_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55240_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55239_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55242_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55241_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55244_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55243_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55246_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55245_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55248_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55247_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55250_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55249_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55252_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55251_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55254_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55253_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55256_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55255_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55258_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55257_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55260_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55259_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55262_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55261_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55264_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55263_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55266_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55265_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55268_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55267_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55270_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55269_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55272_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55271_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55274_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55273_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55276_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55275_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55278_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55277_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55280_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55279_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55282_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55281_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55284_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55283_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55286_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55285_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55288_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55287_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55290_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55289_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55292_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55291_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55294_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55293_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55296_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55295_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55298_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55297_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55300_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55299_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55302_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55301_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55304_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55303_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55306_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55305_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55308_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55307_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55310_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55309_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55312_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55311_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55314_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55313_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55316_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55315_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55318_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55317_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55320_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55319_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55322_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55321_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55324_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55323_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55326_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55325_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55328_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55327_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55330_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55329_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55332_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55331_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55334_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55333_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55336_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55335_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55338_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55337_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55340_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55339_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55342_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[2] && w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55341_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_not_ot_hdc_v41x_hcp_sv_666_55079_Y = !w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_not_ot_hdc_v41x_hcp_sv_669_55080_Y = !w_u_hcb_Q0_u_c_u_b_u_st_procdff_71651_Q[28];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_not_ot_hdc_v41x_hcp_sv_741_55344_Y = !w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_logic_or_ot_hdc_v41x_hcp_sv_672_55082_Y = w_u_hcb_Q0_u_c_u_b_u_st_procdff_71684_Q[0] || w_u_hcb_Q0_u_c_u_b_u_st_reduce_or_ot_hdc_v41x_hcp_sv_750_55345_Y[0];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55087_Y = {32{1'b0}} < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55089_Y = 32'b00000000000000000000000000000001 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55091_Y = 32'b00000000000000000000000000000010 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55093_Y = 32'b00000000000000000000000000000011 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55095_Y = 32'b00000000000000000000000000000100 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55097_Y = 32'b00000000000000000000000000000101 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55099_Y = 32'b00000000000000000000000000000110 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55101_Y = 32'b00000000000000000000000000000111 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55103_Y = 32'b00000000000000000000000000001000 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55105_Y = 32'b00000000000000000000000000001001 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55107_Y = 32'b00000000000000000000000000001010 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55109_Y = 32'b00000000000000000000000000001011 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55111_Y = 32'b00000000000000000000000000001100 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55113_Y = 32'b00000000000000000000000000001101 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55115_Y = 32'b00000000000000000000000000001110 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55117_Y = 32'b00000000000000000000000000001111 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55119_Y = 32'b00000000000000000000000000010000 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55121_Y = 32'b00000000000000000000000000010001 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55123_Y = 32'b00000000000000000000000000010010 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55125_Y = 32'b00000000000000000000000000010011 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55127_Y = 32'b00000000000000000000000000010100 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55129_Y = 32'b00000000000000000000000000010101 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55131_Y = 32'b00000000000000000000000000010110 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55133_Y = 32'b00000000000000000000000000010111 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55135_Y = 32'b00000000000000000000000000011000 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55137_Y = 32'b00000000000000000000000000011001 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55139_Y = 32'b00000000000000000000000000011010 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55141_Y = 32'b00000000000000000000000000011011 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55143_Y = 32'b00000000000000000000000000011100 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55145_Y = 32'b00000000000000000000000000011101 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55147_Y = 32'b00000000000000000000000000011110 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55149_Y = 32'b00000000000000000000000000011111 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55151_Y = 32'b00000000000000000000000000100000 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55153_Y = 32'b00000000000000000000000000100001 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55155_Y = 32'b00000000000000000000000000100010 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55157_Y = 32'b00000000000000000000000000100011 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55159_Y = 32'b00000000000000000000000000100100 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55161_Y = 32'b00000000000000000000000000100101 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55163_Y = 32'b00000000000000000000000000100110 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55165_Y = 32'b00000000000000000000000000100111 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55167_Y = 32'b00000000000000000000000000101000 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55169_Y = 32'b00000000000000000000000000101001 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55171_Y = 32'b00000000000000000000000000101010 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55173_Y = 32'b00000000000000000000000000101011 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55175_Y = 32'b00000000000000000000000000101100 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55177_Y = 32'b00000000000000000000000000101101 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55179_Y = 32'b00000000000000000000000000101110 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55181_Y = 32'b00000000000000000000000000101111 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55183_Y = 32'b00000000000000000000000000110000 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55185_Y = 32'b00000000000000000000000000110001 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55187_Y = 32'b00000000000000000000000000110010 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55189_Y = 32'b00000000000000000000000000110011 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55191_Y = 32'b00000000000000000000000000110100 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55193_Y = 32'b00000000000000000000000000110101 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55195_Y = 32'b00000000000000000000000000110110 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55197_Y = 32'b00000000000000000000000000110111 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55199_Y = 32'b00000000000000000000000000111000 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55201_Y = 32'b00000000000000000000000000111001 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55203_Y = 32'b00000000000000000000000000111010 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55205_Y = 32'b00000000000000000000000000111011 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55207_Y = 32'b00000000000000000000000000111100 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55209_Y = 32'b00000000000000000000000000111101 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55211_Y = 32'b00000000000000000000000000111110 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55213_Y = 32'b00000000000000000000000000111111 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55215_Y = 32'b00000000000000000000000001000000 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55217_Y = 32'b00000000000000000000000001000001 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55219_Y = 32'b00000000000000000000000001000010 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55221_Y = 32'b00000000000000000000000001000011 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55223_Y = 32'b00000000000000000000000001000100 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55225_Y = 32'b00000000000000000000000001000101 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55227_Y = 32'b00000000000000000000000001000110 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55229_Y = 32'b00000000000000000000000001000111 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55231_Y = 32'b00000000000000000000000001001000 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55233_Y = 32'b00000000000000000000000001001001 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55235_Y = 32'b00000000000000000000000001001010 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55237_Y = 32'b00000000000000000000000001001011 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55239_Y = 32'b00000000000000000000000001001100 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55241_Y = 32'b00000000000000000000000001001101 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55243_Y = 32'b00000000000000000000000001001110 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55245_Y = 32'b00000000000000000000000001001111 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55247_Y = 32'b00000000000000000000000001010000 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55249_Y = 32'b00000000000000000000000001010001 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55251_Y = 32'b00000000000000000000000001010010 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55253_Y = 32'b00000000000000000000000001010011 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55255_Y = 32'b00000000000000000000000001010100 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55257_Y = 32'b00000000000000000000000001010101 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55259_Y = 32'b00000000000000000000000001010110 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55261_Y = 32'b00000000000000000000000001010111 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55263_Y = 32'b00000000000000000000000001011000 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55265_Y = 32'b00000000000000000000000001011001 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55267_Y = 32'b00000000000000000000000001011010 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55269_Y = 32'b00000000000000000000000001011011 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55271_Y = 32'b00000000000000000000000001011100 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55273_Y = 32'b00000000000000000000000001011101 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55275_Y = 32'b00000000000000000000000001011110 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55277_Y = 32'b00000000000000000000000001011111 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55279_Y = 32'b00000000000000000000000001100000 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55281_Y = 32'b00000000000000000000000001100001 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55283_Y = 32'b00000000000000000000000001100010 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55285_Y = 32'b00000000000000000000000001100011 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55287_Y = 32'b00000000000000000000000001100100 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55289_Y = 32'b00000000000000000000000001100101 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55291_Y = 32'b00000000000000000000000001100110 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55293_Y = 32'b00000000000000000000000001100111 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55295_Y = 32'b00000000000000000000000001101000 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55297_Y = 32'b00000000000000000000000001101001 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55299_Y = 32'b00000000000000000000000001101010 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55301_Y = 32'b00000000000000000000000001101011 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55303_Y = 32'b00000000000000000000000001101100 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55305_Y = 32'b00000000000000000000000001101101 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55307_Y = 32'b00000000000000000000000001101110 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55309_Y = 32'b00000000000000000000000001101111 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55311_Y = 32'b00000000000000000000000001110000 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55313_Y = 32'b00000000000000000000000001110001 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55315_Y = 32'b00000000000000000000000001110010 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55317_Y = 32'b00000000000000000000000001110011 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55319_Y = 32'b00000000000000000000000001110100 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55321_Y = 32'b00000000000000000000000001110101 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55323_Y = 32'b00000000000000000000000001110110 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55325_Y = 32'b00000000000000000000000001110111 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55327_Y = 32'b00000000000000000000000001111000 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55329_Y = 32'b00000000000000000000000001111001 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55331_Y = 32'b00000000000000000000000001111010 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55333_Y = 32'b00000000000000000000000001111011 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55335_Y = 32'b00000000000000000000000001111100 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55337_Y = 32'b00000000000000000000000001111101 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55339_Y = 32'b00000000000000000000000001111110 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    assign w_u_hcb_Q0_u_c_u_b_u_st_lt_ot_hdc_v41x_hcp_sv_738_55341_Y = 32'b00000000000000000000000001111111 < w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[27:20];   
    reg [0:0] g_u_hcb_Q0_u_c_u_b_u_st_procdff_71644_q;
    assign w_u_hcb_Q0_u_c_u_b_u_st_procdff_71644_Q = g_u_hcb_Q0_u_c_u_b_u_st_procdff_71644_q;
    always @(posedge clk or negedge w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0])
        if (!w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0]) g_u_hcb_Q0_u_c_u_b_u_st_procdff_71644_q <= 1'b0; else g_u_hcb_Q0_u_c_u_b_u_st_procdff_71644_q <= w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[3];   
    reg [127:0] g_u_hcb_Q0_u_c_u_b_u_st_procdff_71645_q;
    assign w_u_hcb_Q0_u_c_u_b_u_st_procdff_71645_Q = g_u_hcb_Q0_u_c_u_b_u_st_procdff_71645_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_u_b_u_st_procdff_71645_q <= {w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55342_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55340_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55338_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55336_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55334_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55332_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55330_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55328_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55326_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55324_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55322_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55320_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55318_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55316_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55314_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55312_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55310_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55308_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55306_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55304_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55302_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55300_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55298_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55296_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55294_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55292_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55290_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55288_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55286_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55284_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55282_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55280_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55278_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55276_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55274_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55272_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55270_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55268_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55266_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55264_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55262_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55260_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55258_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55256_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55254_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55252_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55250_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55248_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55246_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55244_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55242_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55240_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55238_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55236_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55234_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55232_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55230_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55228_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55226_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55224_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55222_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55220_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55218_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55216_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55214_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55212_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55210_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55208_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55206_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55204_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55202_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55200_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55198_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55196_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55194_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55192_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55190_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55188_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55186_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55184_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55182_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55180_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55178_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55176_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55174_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55172_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55170_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55168_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55166_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55164_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55162_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55160_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55158_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55156_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55154_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55152_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55150_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55148_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55146_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55144_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55142_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55140_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55138_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55136_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55134_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55132_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55130_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55128_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55126_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55124_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55122_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55120_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55118_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55116_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55114_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55112_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55110_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55108_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55106_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55104_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55102_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55100_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55098_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55096_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55094_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55092_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55090_Y[0], w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_738_55088_Y[0]};   
    reg [127:0] g_u_hcb_Q0_u_c_u_b_u_st_procdff_71646_q;
    assign w_u_hcb_Q0_u_c_u_b_u_st_procdff_71646_Q = g_u_hcb_Q0_u_c_u_b_u_st_procdff_71646_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_u_b_u_st_procdff_71646_q <= {w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28], w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28]};   
    reg [31:0] g_u_hcb_Q0_u_c_u_b_u_st_procdff_71647_q;
    assign w_u_hcb_Q0_u_c_u_b_u_st_procdff_71647_Q = g_u_hcb_Q0_u_c_u_b_u_st_procdff_71647_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_u_b_u_st_procdff_71647_q <= 32'b00000000000000000000000010000000;   
    reg [9:0] g_u_hcb_Q0_u_c_u_b_u_st_procdff_71648_q;
    assign w_u_hcb_Q0_u_c_u_b_u_st_procdff_71648_Q = g_u_hcb_Q0_u_c_u_b_u_st_procdff_71648_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_u_b_u_st_procdff_71648_q <= w_u_hcb_Q0_u_c_u_b_u_st_procdff_71651_Q[19:10];   
    reg [9:0] g_u_hcb_Q0_u_c_u_b_u_st_procdff_71649_q;
    assign w_u_hcb_Q0_u_c_u_b_u_st_procdff_71649_Q = g_u_hcb_Q0_u_c_u_b_u_st_procdff_71649_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_u_b_u_st_procdff_71649_q <= w_u_hcb_Q0_u_c_u_b_u_st_procdff_71651_Q[9:0];   
    reg [31:0] g_u_hcb_Q0_u_c_u_b_u_st_procdff_71650_q;
    assign w_u_hcb_Q0_u_c_u_b_u_st_procdff_71650_Q = g_u_hcb_Q0_u_c_u_b_u_st_procdff_71650_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_u_b_u_st_procdff_71650_q <= 32'b00000000000000000000000000001001;   
    reg [28:0] g_u_hcb_Q0_u_c_u_b_u_st_procdff_71651_q;
    assign w_u_hcb_Q0_u_c_u_b_u_st_procdff_71651_Q = g_u_hcb_Q0_u_c_u_b_u_st_procdff_71651_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_u_b_u_st_procdff_71651_q <= L65_i_q[28:0];   
    reg [28:0] g_u_hcb_Q0_u_c_u_b_u_st_procdff_71652_q;
    assign w_u_hcb_Q0_u_c_u_b_u_st_procdff_71652_Q = g_u_hcb_Q0_u_c_u_b_u_st_procdff_71652_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_u_b_u_st_procdff_71652_q <= w_u_hcb_Q0_u_c_u_b_u_st_procdff_71651_Q[28:0];   
    reg [28:0] g_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_q;
    assign w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q = g_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_q <= w_u_hcb_Q0_u_c_u_b_u_st_procdff_71652_Q[28:0];   
    reg [28:0] g_u_hcb_Q0_u_c_u_b_u_st_procdff_71654_q;
    assign w_u_hcb_Q0_u_c_u_b_u_st_procdff_71654_Q = g_u_hcb_Q0_u_c_u_b_u_st_procdff_71654_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_u_b_u_st_procdff_71654_q <= w_u_hcb_Q0_u_c_u_b_u_st_procdff_71653_Q[28:0];   
    reg [28:0] g_u_hcb_Q0_u_c_u_b_u_st_procdff_71655_q;
    assign w_u_hcb_Q0_u_c_u_b_u_st_procdff_71655_Q = g_u_hcb_Q0_u_c_u_b_u_st_procdff_71655_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_u_b_u_st_procdff_71655_q <= w_u_hcb_Q0_u_c_u_b_u_st_procdff_71654_Q[28:0];   
    reg [28:0] g_u_hcb_Q0_u_c_u_b_u_st_procdff_71656_q;
    assign w_u_hcb_Q0_u_c_u_b_u_st_procdff_71656_Q = g_u_hcb_Q0_u_c_u_b_u_st_procdff_71656_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_u_b_u_st_procdff_71656_q <= w_u_hcb_Q0_u_c_u_b_u_st_procdff_71655_Q[28:0];   
    reg [28:0] g_u_hcb_Q0_u_c_u_b_u_st_procdff_71657_q;
    assign w_u_hcb_Q0_u_c_u_b_u_st_procdff_71657_Q = g_u_hcb_Q0_u_c_u_b_u_st_procdff_71657_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_u_b_u_st_procdff_71657_q <= w_u_hcb_Q0_u_c_u_b_u_st_procdff_71656_Q[28:0];   
    reg [28:0] g_u_hcb_Q0_u_c_u_b_u_st_procdff_71658_q;
    assign w_u_hcb_Q0_u_c_u_b_u_st_procdff_71658_Q = g_u_hcb_Q0_u_c_u_b_u_st_procdff_71658_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_u_b_u_st_procdff_71658_q <= w_u_hcb_Q0_u_c_u_b_u_st_procdff_71657_Q[28:0];   
    reg [28:0] g_u_hcb_Q0_u_c_u_b_u_st_procdff_71659_q;
    assign w_u_hcb_Q0_u_c_u_b_u_st_procdff_71659_Q = g_u_hcb_Q0_u_c_u_b_u_st_procdff_71659_q;
    always @(posedge clk) g_u_hcb_Q0_u_c_u_b_u_st_procdff_71659_q <= w_u_hcb_Q0_u_c_u_b_u_st_procdff_71658_Q[28:0];   
    reg [0:0] g_u_hcb_Q0_u_c_u_b_u_st_procdff_71664_q;
    assign w_u_hcb_Q0_u_c_u_b_u_st_procdff_71664_Q = g_u_hcb_Q0_u_c_u_b_u_st_procdff_71664_q;
    always @(posedge clk or negedge w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0])
        if (!w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0]) g_u_hcb_Q0_u_c_u_b_u_st_procdff_71664_q <= 1'b0; else g_u_hcb_Q0_u_c_u_b_u_st_procdff_71664_q <= w_u_hcb_Q0_u_c_u_b_u_st_logic_or_ot_hdc_v41x_hcp_sv_672_55082_Y[0];   
    reg [0:0] g_u_hcb_Q0_u_c_u_b_u_st_procdff_71669_q;
    assign w_u_hcb_Q0_u_c_u_b_u_st_procdff_71669_Q = g_u_hcb_Q0_u_c_u_b_u_st_procdff_71669_q;
    always @(posedge clk or negedge w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0])
        if (!w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0]) g_u_hcb_Q0_u_c_u_b_u_st_procdff_71669_q <= 1'b0; else g_u_hcb_Q0_u_c_u_b_u_st_procdff_71669_q <= w_u_hcb_Q0_u_c_u_b_u_st_logic_and_ot_hdc_v41x_hcp_sv_669_55081_Y[0];   
    reg [0:0] g_u_hcb_Q0_u_c_u_b_u_st_procdff_71674_q;
    assign w_u_hcb_Q0_u_c_u_b_u_st_procdff_71674_Q = g_u_hcb_Q0_u_c_u_b_u_st_procdff_71674_q;
    always @(posedge clk or negedge w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0])
        if (!w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0]) g_u_hcb_Q0_u_c_u_b_u_st_procdff_71674_q <= 1'b0; else g_u_hcb_Q0_u_c_u_b_u_st_procdff_71674_q <= w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[0];   
    reg [8:0] g_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_q;
    assign w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q = g_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_q;
    always @(posedge clk or negedge w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0])
        if (!w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0]) g_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_q <= 9'b000000000; else g_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_q <= {w_u_hcb_Q0_u_c_u_b_u_st_procdff_71679_Q[7:0], L65_i_q[29]};   
    reg [0:0] g_u_hcb_Q0_u_c_u_b_u_st_procdff_71684_q;
    assign w_u_hcb_Q0_u_c_u_b_u_st_procdff_71684_Q = g_u_hcb_Q0_u_c_u_b_u_st_procdff_71684_q;
    always @(posedge clk or negedge w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0])
        if (!w_u_hcb_Q0_u_c_u_b_g_rr_u_rst_rst_n[0]) g_u_hcb_Q0_u_c_u_b_u_st_procdff_71684_q <= 1'b0; else g_u_hcb_Q0_u_c_u_b_u_st_procdff_71684_q <= 1'b0;   
    assign w_u_hcb_Q0_u_c_u_b_u_st_reduce_or_ot_hdc_v41x_hcp_sv_750_55345_Y = |{w_u_hcb_Q0_ot_hbm_hc_bank128_pair7_fault[1:0], w_u_hcb_Q0_ot_hbm_hc_bank128_pair6_fault[1:0], w_u_hcb_Q0_ot_hbm_hc_bank128_pair5_fault[1:0], w_u_hcb_Q0_ot_hbm_hc_bank128_pair4_fault[1:0], w_u_hcb_Q0_ot_hbm_hc_bank128_pair3_fault[1:0], w_u_hcb_Q0_ot_hbm_hc_bank128_pair2_fault[1:0], w_u_hcb_Q0_ot_hbm_hc_bank128_pair1_fault[1:0], w_u_hcb_Q0_ot_hbm_hc_bank128_pair0_fault[1:0]};   
     
    ot_rst_relay #(.REGIONS(1)) u_u_hcb_Q0_u_c_u_rst (
        .clk(clk),
        .rst_n(w_u_hcb_Q0_u_c_u_rst_rst_n),
        .rst_n_in(L65_i_q[44])
    );
endmodule
