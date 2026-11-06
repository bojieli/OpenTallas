module gold(input clk,rst,input [6:0] r,f,output ready,fault);
wire rst_root_n=rst;
reg [9:0] rp=0; always @(posedge clk) rp <= {rp[8:0],rst};
wire rst_rl_0 = rp[0];
wire rst_rl_1 = rp[1];
wire rst_rl_2 = rp[2];
wire rst_rl_3 = rp[3];
wire rst_rl_4 = rp[4];
wire rst_rl_5 = rp[5];
wire rst_rl_6 = rp[6];
wire rst_rl_7 = rp[7];
wire rst_rl_8 = rp[8];
wire rr_t0 = rp[9];
wire rst_rl_10 = rp[3];
wire rst_rl_11 = rp[4];
wire rst_rl_12 = rp[5];
wire rst_rl_13 = rp[6];
wire rst_rl_14 = rp[7];
wire rst_rl_15 = rp[8];
wire rr_t4 = rp[9];
wire rst_rl_17 = rp[4];
wire rst_rl_18 = rp[5];
wire rst_rl_19 = rp[6];
wire rst_rl_20 = rp[7];
wire rst_rl_21 = rp[8];
wire rr_t8 = rp[9];
wire rst_rl_23 = rp[5];
wire rst_rl_24 = rp[6];
wire rst_rl_25 = rp[7];
wire rst_rl_26 = rp[8];
wire rr_t15 = rp[9];
wire rst_rl_28 = rp[6];
wire rst_rl_29 = rp[7];
wire rst_rl_30 = rp[8];
wire rr_t30 = rp[9];
wire rst_rl_32 = rp[0];
wire rst_rl_33 = rp[1];
wire rst_rl_34 = rp[2];
wire rst_rl_35 = rp[3];
wire rst_rl_36 = rp[4];
wire rst_rl_37 = rp[5];
wire rst_rl_38 = rp[6];
wire rst_rl_39 = rp[7];
wire rst_rl_40 = rp[8];
wire rr_t1 = rp[9];
wire rst_rl_42 = rp[3];
wire rst_rl_43 = rp[4];
wire rst_rl_44 = rp[5];
wire rst_rl_45 = rp[6];
wire rst_rl_46 = rp[7];
wire rst_rl_47 = rp[8];
wire rr_t3 = rp[9];
wire rst_rl_49 = rp[3];
wire rst_rl_50 = rp[4];
wire rst_rl_51 = rp[5];
wire rst_rl_52 = rp[6];
wire rst_rl_53 = rp[7];
wire rst_rl_54 = rp[8];
wire rr_t18 = rp[9];
wire rr_t22 = rp[9];
wire rst_rl_57 = rp[4];
wire rst_rl_58 = rp[5];
wire rst_rl_59 = rp[6];
wire rst_rl_60 = rp[7];
wire rst_rl_61 = rp[8];
wire rr_t34 = rp[9];
wire rst_rl_63 = rp[8];
wire rr_t26 = rp[9];
wire rst_rl_65 = rp[2];
wire rst_rl_66 = rp[3];
wire rst_rl_67 = rp[4];
wire rst_rl_68 = rp[5];
wire rst_rl_69 = rp[6];
wire rst_rl_70 = rp[7];
wire rst_rl_71 = rp[8];
wire rr_t2 = rp[9];
wire rr_t6 = rp[9];
wire rst_rl_74 = rp[6];
wire rst_rl_75 = rp[7];
wire rst_rl_76 = rp[8];
wire rr_t10 = rp[9];
wire rst_rl_78 = rp[7];
wire rst_rl_79 = rp[8];
wire rr_t14 = rp[9];
wire rst_rl_81 = rp[0];
wire rst_rl_82 = rp[1];
wire rst_rl_83 = rp[2];
wire rst_rl_84 = rp[3];
wire rst_rl_85 = rp[4];
wire rst_rl_86 = rp[5];
wire rst_rl_87 = rp[6];
wire rst_rl_88 = rp[7];
wire rst_rl_89 = rp[8];
wire rr_t5 = rp[9];
wire rr_t32 = rp[9];
wire rst_rl_92 = rp[2];
wire rst_rl_93 = rp[3];
wire rst_rl_94 = rp[4];
wire rst_rl_95 = rp[5];
wire rst_rl_96 = rp[6];
wire rst_rl_97 = rp[7];
wire rst_rl_98 = rp[8];
wire rr_t9 = rp[9];
wire rst_rl_100 = rp[5];
wire rst_rl_101 = rp[6];
wire rst_rl_102 = rp[7];
wire rst_rl_103 = rp[8];
wire rr_t17 = rp[9];
wire rst_rl_105 = rp[8];
wire rr_t21 = rp[9];
wire rr_t25 = rp[9];
wire rst_rl_108 = rp[7];
wire rst_rl_109 = rp[8];
wire rr_t33 = rp[9];
wire rst_rl_111 = rp[2];
wire rst_rl_112 = rp[3];
wire rst_rl_113 = rp[4];
wire rst_rl_114 = rp[5];
wire rst_rl_115 = rp[6];
wire rst_rl_116 = rp[7];
wire rst_rl_117 = rp[8];
wire rr_t29 = rp[9];
wire rst_rl_119 = rp[0];
wire rst_rl_120 = rp[1];
wire rst_rl_121 = rp[2];
wire rst_rl_122 = rp[3];
wire rst_rl_123 = rp[4];
wire rst_rl_124 = rp[5];
wire rst_rl_125 = rp[6];
wire rst_rl_126 = rp[7];
wire rst_rl_127 = rp[8];
wire rr_t7 = rp[9];
wire rr_t11 = rp[9];
wire rst_rl_130 = rp[4];
wire rst_rl_131 = rp[5];
wire rst_rl_132 = rp[6];
wire rst_rl_133 = rp[7];
wire rst_rl_134 = rp[8];
wire rr_t19 = rp[9];
wire rst_rl_136 = rp[8];
wire rr_t23 = rp[9];
wire rr_t27 = rp[9];
wire rst_rl_139 = rp[2];
wire rst_rl_140 = rp[3];
wire rst_rl_141 = rp[4];
wire rst_rl_142 = rp[5];
wire rst_rl_143 = rp[6];
wire rst_rl_144 = rp[7];
wire rst_rl_145 = rp[8];
wire rr_t31 = rp[9];
wire rst_rl_147 = rp[6];
wire rst_rl_148 = rp[7];
wire rst_rl_149 = rp[8];
wire rr_t28 = rp[9];
wire rst_rl_151 = rp[0];
wire rst_rl_152 = rp[1];
wire rst_rl_153 = rp[2];
wire rst_rl_154 = rp[3];
wire rst_rl_155 = rp[4];
wire rst_rl_156 = rp[5];
wire rst_rl_157 = rp[6];
wire rst_rl_158 = rp[7];
wire rst_rl_159 = rp[8];
wire rr_t12 = rp[9];
wire rst_rl_161 = rp[8];
wire rr_t13 = rp[9];
wire rst_rl_163 = rp[0];
wire rst_rl_164 = rp[1];
wire rst_rl_165 = rp[2];
wire rst_rl_166 = rp[3];
wire rst_rl_167 = rp[4];
wire rst_rl_168 = rp[5];
wire rst_rl_169 = rp[6];
wire rst_rl_170 = rp[7];
wire rst_rl_171 = rp[8];
wire rr_t16 = rp[9];
wire rst_rl_173 = rp[8];
wire rr_t20 = rp[9];
wire rr_t24 = rp[9];
wire cland_up_ready,cland_up_fault;
    wire cland_r_rst_n_t0, cland_f_rst_n_t0;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t0 (
        .clk(clk), .rst_n(rr_t0), .ready_i({r[0]}),
        .fault_i({f[0]}), .ready_o(cland_r_rst_n_t0), .fault_o(cland_f_rst_n_t0));
    wire cland_r_rst_n_t2, cland_f_rst_n_t2;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t2 (
        .clk(clk), .rst_n(rr_t2), .ready_i({r[1]}),
        .fault_i({f[1]}), .ready_o(cland_r_rst_n_t2), .fault_o(cland_f_rst_n_t2));
    wire cland_r_rst_n_t24, cland_f_rst_n_t24;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t24 (
        .clk(clk), .rst_n(rr_t24), .ready_i({r[2]}),
        .fault_i({f[2]}), .ready_o(cland_r_rst_n_t24), .fault_o(cland_f_rst_n_t24));
    wire cland_r_rst_n_t27, cland_f_rst_n_t27;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t27 (
        .clk(clk), .rst_n(rr_t27), .ready_i({r[3]}),
        .fault_i({f[3]}), .ready_o(cland_r_rst_n_t27), .fault_o(cland_f_rst_n_t27));
    wire cland_r_rst_n_t28, cland_f_rst_n_t28;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t28 (
        .clk(clk), .rst_n(rr_t28), .ready_i({r[5]}),
        .fault_i({f[5]}), .ready_o(cland_r_rst_n_t28), .fault_o(cland_f_rst_n_t28));
    wire cland_r_rst_n_t29, cland_f_rst_n_t29;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t29 (
        .clk(clk), .rst_n(rr_t29), .ready_i({r[6]}),
        .fault_i({f[6]}), .ready_o(cland_r_rst_n_t29), .fault_o(cland_f_rst_n_t29));
    wire cland_r_rst_n_t30, cland_f_rst_n_t30;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t30 (
        .clk(clk), .rst_n(rr_t30), .ready_i({r[4]}),
        .fault_i({f[4]}), .ready_o(cland_r_rst_n_t30), .fault_o(cland_f_rst_n_t30));
    wire cland_r_rst_rl_117, cland_f_rst_rl_117;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_117 (
        .clk(clk), .rst_n(rst_rl_117), .ready_i({cland_r_rst_n_t29}),
        .fault_i({cland_f_rst_n_t29}), .ready_o(cland_r_rst_rl_117), .fault_o(cland_f_rst_rl_117));
    wire cland_r_rst_rl_136, cland_f_rst_rl_136;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_136 (
        .clk(clk), .rst_n(rst_rl_136), .ready_i({cland_r_rst_n_t27}),
        .fault_i({cland_f_rst_n_t27}), .ready_o(cland_r_rst_rl_136), .fault_o(cland_f_rst_rl_136));
    wire cland_r_rst_rl_149, cland_f_rst_rl_149;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_149 (
        .clk(clk), .rst_n(rst_rl_149), .ready_i({cland_r_rst_n_t28}),
        .fault_i({cland_f_rst_n_t28}), .ready_o(cland_r_rst_rl_149), .fault_o(cland_f_rst_rl_149));
    wire cland_r_rst_rl_173, cland_f_rst_rl_173;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_173 (
        .clk(clk), .rst_n(rst_rl_173), .ready_i({cland_r_rst_n_t24}),
        .fault_i({cland_f_rst_n_t24}), .ready_o(cland_r_rst_rl_173), .fault_o(cland_f_rst_rl_173));
    wire cland_r_rst_rl_30, cland_f_rst_rl_30;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_30 (
        .clk(clk), .rst_n(rst_rl_30), .ready_i({cland_r_rst_n_t30}),
        .fault_i({cland_f_rst_n_t30}), .ready_o(cland_r_rst_rl_30), .fault_o(cland_f_rst_rl_30));
    wire cland_r_rst_rl_71, cland_f_rst_rl_71;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_71 (
        .clk(clk), .rst_n(rst_rl_71), .ready_i({cland_r_rst_n_t2}),
        .fault_i({cland_f_rst_n_t2}), .ready_o(cland_r_rst_rl_71), .fault_o(cland_f_rst_rl_71));
    wire cland_r_rst_rl_8, cland_f_rst_rl_8;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_8 (
        .clk(clk), .rst_n(rst_rl_8), .ready_i({cland_r_rst_n_t0}),
        .fault_i({cland_f_rst_n_t0}), .ready_o(cland_r_rst_rl_8), .fault_o(cland_f_rst_rl_8));
    wire cland_r_rst_rl_116, cland_f_rst_rl_116;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_116 (
        .clk(clk), .rst_n(rst_rl_116), .ready_i({cland_r_rst_rl_117}),
        .fault_i({cland_f_rst_rl_117}), .ready_o(cland_r_rst_rl_116), .fault_o(cland_f_rst_rl_116));
    wire cland_r_rst_rl_133, cland_f_rst_rl_133;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_133 (
        .clk(clk), .rst_n(rst_rl_133), .ready_i({cland_r_rst_rl_136}),
        .fault_i({cland_f_rst_rl_136}), .ready_o(cland_r_rst_rl_133), .fault_o(cland_f_rst_rl_133));
    wire cland_r_rst_rl_148, cland_f_rst_rl_148;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_148 (
        .clk(clk), .rst_n(rst_rl_148), .ready_i({cland_r_rst_rl_149}),
        .fault_i({cland_f_rst_rl_149}), .ready_o(cland_r_rst_rl_148), .fault_o(cland_f_rst_rl_148));
    wire cland_r_rst_rl_170, cland_f_rst_rl_170;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_170 (
        .clk(clk), .rst_n(rst_rl_170), .ready_i({cland_r_rst_rl_173}),
        .fault_i({cland_f_rst_rl_173}), .ready_o(cland_r_rst_rl_170), .fault_o(cland_f_rst_rl_170));
    wire cland_r_rst_rl_29, cland_f_rst_rl_29;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_29 (
        .clk(clk), .rst_n(rst_rl_29), .ready_i({cland_r_rst_rl_30}),
        .fault_i({cland_f_rst_rl_30}), .ready_o(cland_r_rst_rl_29), .fault_o(cland_f_rst_rl_29));
    wire cland_r_rst_rl_7, cland_f_rst_rl_7;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_7 (
        .clk(clk), .rst_n(rst_rl_7), .ready_i({cland_r_rst_rl_8}),
        .fault_i({cland_f_rst_rl_8}), .ready_o(cland_r_rst_rl_7), .fault_o(cland_f_rst_rl_7));
    wire cland_r_rst_rl_70, cland_f_rst_rl_70;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_70 (
        .clk(clk), .rst_n(rst_rl_70), .ready_i({cland_r_rst_rl_71}),
        .fault_i({cland_f_rst_rl_71}), .ready_o(cland_r_rst_rl_70), .fault_o(cland_f_rst_rl_70));
    wire cland_r_rst_rl_115, cland_f_rst_rl_115;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_115 (
        .clk(clk), .rst_n(rst_rl_115), .ready_i({cland_r_rst_rl_116}),
        .fault_i({cland_f_rst_rl_116}), .ready_o(cland_r_rst_rl_115), .fault_o(cland_f_rst_rl_115));
    wire cland_r_rst_rl_132, cland_f_rst_rl_132;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_132 (
        .clk(clk), .rst_n(rst_rl_132), .ready_i({cland_r_rst_rl_133}),
        .fault_i({cland_f_rst_rl_133}), .ready_o(cland_r_rst_rl_132), .fault_o(cland_f_rst_rl_132));
    wire cland_r_rst_rl_147, cland_f_rst_rl_147;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_147 (
        .clk(clk), .rst_n(rst_rl_147), .ready_i({cland_r_rst_rl_148}),
        .fault_i({cland_f_rst_rl_148}), .ready_o(cland_r_rst_rl_147), .fault_o(cland_f_rst_rl_147));
    wire cland_r_rst_rl_169, cland_f_rst_rl_169;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_169 (
        .clk(clk), .rst_n(rst_rl_169), .ready_i({cland_r_rst_rl_170}),
        .fault_i({cland_f_rst_rl_170}), .ready_o(cland_r_rst_rl_169), .fault_o(cland_f_rst_rl_169));
    wire cland_r_rst_rl_28, cland_f_rst_rl_28;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_28 (
        .clk(clk), .rst_n(rst_rl_28), .ready_i({cland_r_rst_rl_29}),
        .fault_i({cland_f_rst_rl_29}), .ready_o(cland_r_rst_rl_28), .fault_o(cland_f_rst_rl_28));
    wire cland_r_rst_rl_6, cland_f_rst_rl_6;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_6 (
        .clk(clk), .rst_n(rst_rl_6), .ready_i({cland_r_rst_rl_7}),
        .fault_i({cland_f_rst_rl_7}), .ready_o(cland_r_rst_rl_6), .fault_o(cland_f_rst_rl_6));
    wire cland_r_rst_rl_69, cland_f_rst_rl_69;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_69 (
        .clk(clk), .rst_n(rst_rl_69), .ready_i({cland_r_rst_rl_70}),
        .fault_i({cland_f_rst_rl_70}), .ready_o(cland_r_rst_rl_69), .fault_o(cland_f_rst_rl_69));
    wire cland_r_rst_rl_114, cland_f_rst_rl_114;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_114 (
        .clk(clk), .rst_n(rst_rl_114), .ready_i({cland_r_rst_rl_115}),
        .fault_i({cland_f_rst_rl_115}), .ready_o(cland_r_rst_rl_114), .fault_o(cland_f_rst_rl_114));
    wire cland_r_rst_rl_131, cland_f_rst_rl_131;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_131 (
        .clk(clk), .rst_n(rst_rl_131), .ready_i({cland_r_rst_rl_132}),
        .fault_i({cland_f_rst_rl_132}), .ready_o(cland_r_rst_rl_131), .fault_o(cland_f_rst_rl_131));
    wire cland_r_rst_rl_142, cland_f_rst_rl_142;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_142 (
        .clk(clk), .rst_n(rst_rl_142), .ready_i({cland_r_rst_rl_147}),
        .fault_i({cland_f_rst_rl_147}), .ready_o(cland_r_rst_rl_142), .fault_o(cland_f_rst_rl_142));
    wire cland_r_rst_rl_168, cland_f_rst_rl_168;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_168 (
        .clk(clk), .rst_n(rst_rl_168), .ready_i({cland_r_rst_rl_169}),
        .fault_i({cland_f_rst_rl_169}), .ready_o(cland_r_rst_rl_168), .fault_o(cland_f_rst_rl_168));
    wire cland_r_rst_rl_23, cland_f_rst_rl_23;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_23 (
        .clk(clk), .rst_n(rst_rl_23), .ready_i({cland_r_rst_rl_28}),
        .fault_i({cland_f_rst_rl_28}), .ready_o(cland_r_rst_rl_23), .fault_o(cland_f_rst_rl_23));
    wire cland_r_rst_rl_5, cland_f_rst_rl_5;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_5 (
        .clk(clk), .rst_n(rst_rl_5), .ready_i({cland_r_rst_rl_6}),
        .fault_i({cland_f_rst_rl_6}), .ready_o(cland_r_rst_rl_5), .fault_o(cland_f_rst_rl_5));
    wire cland_r_rst_rl_68, cland_f_rst_rl_68;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_68 (
        .clk(clk), .rst_n(rst_rl_68), .ready_i({cland_r_rst_rl_69}),
        .fault_i({cland_f_rst_rl_69}), .ready_o(cland_r_rst_rl_68), .fault_o(cland_f_rst_rl_68));
    wire cland_r_rst_rl_113, cland_f_rst_rl_113;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_113 (
        .clk(clk), .rst_n(rst_rl_113), .ready_i({cland_r_rst_rl_114}),
        .fault_i({cland_f_rst_rl_114}), .ready_o(cland_r_rst_rl_113), .fault_o(cland_f_rst_rl_113));
    wire cland_r_rst_rl_130, cland_f_rst_rl_130;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_130 (
        .clk(clk), .rst_n(rst_rl_130), .ready_i({cland_r_rst_rl_131}),
        .fault_i({cland_f_rst_rl_131}), .ready_o(cland_r_rst_rl_130), .fault_o(cland_f_rst_rl_130));
    wire cland_r_rst_rl_141, cland_f_rst_rl_141;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_141 (
        .clk(clk), .rst_n(rst_rl_141), .ready_i({cland_r_rst_rl_142}),
        .fault_i({cland_f_rst_rl_142}), .ready_o(cland_r_rst_rl_141), .fault_o(cland_f_rst_rl_141));
    wire cland_r_rst_rl_167, cland_f_rst_rl_167;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_167 (
        .clk(clk), .rst_n(rst_rl_167), .ready_i({cland_r_rst_rl_168}),
        .fault_i({cland_f_rst_rl_168}), .ready_o(cland_r_rst_rl_167), .fault_o(cland_f_rst_rl_167));
    wire cland_r_rst_rl_17, cland_f_rst_rl_17;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_17 (
        .clk(clk), .rst_n(rst_rl_17), .ready_i({cland_r_rst_rl_23}),
        .fault_i({cland_f_rst_rl_23}), .ready_o(cland_r_rst_rl_17), .fault_o(cland_f_rst_rl_17));
    wire cland_r_rst_rl_4, cland_f_rst_rl_4;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_4 (
        .clk(clk), .rst_n(rst_rl_4), .ready_i({cland_r_rst_rl_5}),
        .fault_i({cland_f_rst_rl_5}), .ready_o(cland_r_rst_rl_4), .fault_o(cland_f_rst_rl_4));
    wire cland_r_rst_rl_67, cland_f_rst_rl_67;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_67 (
        .clk(clk), .rst_n(rst_rl_67), .ready_i({cland_r_rst_rl_68}),
        .fault_i({cland_f_rst_rl_68}), .ready_o(cland_r_rst_rl_67), .fault_o(cland_f_rst_rl_67));
    wire cland_r_rst_rl_10, cland_f_rst_rl_10;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_10 (
        .clk(clk), .rst_n(rst_rl_10), .ready_i({cland_r_rst_rl_17}),
        .fault_i({cland_f_rst_rl_17}), .ready_o(cland_r_rst_rl_10), .fault_o(cland_f_rst_rl_10));
    wire cland_r_rst_rl_112, cland_f_rst_rl_112;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_112 (
        .clk(clk), .rst_n(rst_rl_112), .ready_i({cland_r_rst_rl_113}),
        .fault_i({cland_f_rst_rl_113}), .ready_o(cland_r_rst_rl_112), .fault_o(cland_f_rst_rl_112));
    wire cland_r_rst_rl_122, cland_f_rst_rl_122;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_122 (
        .clk(clk), .rst_n(rst_rl_122), .ready_i({cland_r_rst_rl_130}),
        .fault_i({cland_f_rst_rl_130}), .ready_o(cland_r_rst_rl_122), .fault_o(cland_f_rst_rl_122));
    wire cland_r_rst_rl_140, cland_f_rst_rl_140;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_140 (
        .clk(clk), .rst_n(rst_rl_140), .ready_i({cland_r_rst_rl_141}),
        .fault_i({cland_f_rst_rl_141}), .ready_o(cland_r_rst_rl_140), .fault_o(cland_f_rst_rl_140));
    wire cland_r_rst_rl_166, cland_f_rst_rl_166;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_166 (
        .clk(clk), .rst_n(rst_rl_166), .ready_i({cland_r_rst_rl_167}),
        .fault_i({cland_f_rst_rl_167}), .ready_o(cland_r_rst_rl_166), .fault_o(cland_f_rst_rl_166));
    wire cland_r_rst_rl_3, cland_f_rst_rl_3;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_3 (
        .clk(clk), .rst_n(rst_rl_3), .ready_i({cland_r_rst_rl_4}),
        .fault_i({cland_f_rst_rl_4}), .ready_o(cland_r_rst_rl_3), .fault_o(cland_f_rst_rl_3));
    wire cland_r_rst_rl_66, cland_f_rst_rl_66;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_66 (
        .clk(clk), .rst_n(rst_rl_66), .ready_i({cland_r_rst_rl_67}),
        .fault_i({cland_f_rst_rl_67}), .ready_o(cland_r_rst_rl_66), .fault_o(cland_f_rst_rl_66));
    wire cland_r_rst_rl_111, cland_f_rst_rl_111;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_111 (
        .clk(clk), .rst_n(rst_rl_111), .ready_i({cland_r_rst_rl_112}),
        .fault_i({cland_f_rst_rl_112}), .ready_o(cland_r_rst_rl_111), .fault_o(cland_f_rst_rl_111));
    wire cland_r_rst_rl_121, cland_f_rst_rl_121;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_121 (
        .clk(clk), .rst_n(rst_rl_121), .ready_i({cland_r_rst_rl_122}),
        .fault_i({cland_f_rst_rl_122}), .ready_o(cland_r_rst_rl_121), .fault_o(cland_f_rst_rl_121));
    wire cland_r_rst_rl_139, cland_f_rst_rl_139;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_139 (
        .clk(clk), .rst_n(rst_rl_139), .ready_i({cland_r_rst_rl_140}),
        .fault_i({cland_f_rst_rl_140}), .ready_o(cland_r_rst_rl_139), .fault_o(cland_f_rst_rl_139));
    wire cland_r_rst_rl_165, cland_f_rst_rl_165;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_165 (
        .clk(clk), .rst_n(rst_rl_165), .ready_i({cland_r_rst_rl_166}),
        .fault_i({cland_f_rst_rl_166}), .ready_o(cland_r_rst_rl_165), .fault_o(cland_f_rst_rl_165));
    wire cland_r_rst_rl_2, cland_f_rst_rl_2;
    ot_dp_landing_collect #(.N(2)) u_cland_collect_rst_rl_2 (
        .clk(clk), .rst_n(rst_rl_2), .ready_i({cland_r_rst_rl_10, cland_r_rst_rl_3}),
        .fault_i({cland_f_rst_rl_10, cland_f_rst_rl_3}), .ready_o(cland_r_rst_rl_2), .fault_o(cland_f_rst_rl_2));
    wire cland_r_rst_rl_65, cland_f_rst_rl_65;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_65 (
        .clk(clk), .rst_n(rst_rl_65), .ready_i({cland_r_rst_rl_66}),
        .fault_i({cland_f_rst_rl_66}), .ready_o(cland_r_rst_rl_65), .fault_o(cland_f_rst_rl_65));
    wire cland_r_rst_rl_1, cland_f_rst_rl_1;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_1 (
        .clk(clk), .rst_n(rst_rl_1), .ready_i({cland_r_rst_rl_2}),
        .fault_i({cland_f_rst_rl_2}), .ready_o(cland_r_rst_rl_1), .fault_o(cland_f_rst_rl_1));
    wire cland_r_rst_rl_120, cland_f_rst_rl_120;
    ot_dp_landing_collect #(.N(2)) u_cland_collect_rst_rl_120 (
        .clk(clk), .rst_n(rst_rl_120), .ready_i({cland_r_rst_rl_121, cland_r_rst_rl_139}),
        .fault_i({cland_f_rst_rl_121, cland_f_rst_rl_139}), .ready_o(cland_r_rst_rl_120), .fault_o(cland_f_rst_rl_120));
    wire cland_r_rst_rl_164, cland_f_rst_rl_164;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_164 (
        .clk(clk), .rst_n(rst_rl_164), .ready_i({cland_r_rst_rl_165}),
        .fault_i({cland_f_rst_rl_165}), .ready_o(cland_r_rst_rl_164), .fault_o(cland_f_rst_rl_164));
    wire cland_r_rst_rl_33, cland_f_rst_rl_33;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_33 (
        .clk(clk), .rst_n(rst_rl_33), .ready_i({cland_r_rst_rl_65}),
        .fault_i({cland_f_rst_rl_65}), .ready_o(cland_r_rst_rl_33), .fault_o(cland_f_rst_rl_33));
    wire cland_r_rst_rl_82, cland_f_rst_rl_82;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_82 (
        .clk(clk), .rst_n(rst_rl_82), .ready_i({cland_r_rst_rl_111}),
        .fault_i({cland_f_rst_rl_111}), .ready_o(cland_r_rst_rl_82), .fault_o(cland_f_rst_rl_82));
    wire cland_r_rst_rl_0, cland_f_rst_rl_0;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_0 (
        .clk(clk), .rst_n(rst_rl_0), .ready_i({cland_r_rst_rl_1}),
        .fault_i({cland_f_rst_rl_1}), .ready_o(cland_r_rst_rl_0), .fault_o(cland_f_rst_rl_0));
    wire cland_r_rst_rl_119, cland_f_rst_rl_119;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_119 (
        .clk(clk), .rst_n(rst_rl_119), .ready_i({cland_r_rst_rl_120}),
        .fault_i({cland_f_rst_rl_120}), .ready_o(cland_r_rst_rl_119), .fault_o(cland_f_rst_rl_119));
    wire cland_r_rst_rl_163, cland_f_rst_rl_163;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_163 (
        .clk(clk), .rst_n(rst_rl_163), .ready_i({cland_r_rst_rl_164}),
        .fault_i({cland_f_rst_rl_164}), .ready_o(cland_r_rst_rl_163), .fault_o(cland_f_rst_rl_163));
    wire cland_r_rst_rl_32, cland_f_rst_rl_32;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_32 (
        .clk(clk), .rst_n(rst_rl_32), .ready_i({cland_r_rst_rl_33}),
        .fault_i({cland_f_rst_rl_33}), .ready_o(cland_r_rst_rl_32), .fault_o(cland_f_rst_rl_32));
    wire cland_r_rst_rl_81, cland_f_rst_rl_81;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_81 (
        .clk(clk), .rst_n(rst_rl_81), .ready_i({cland_r_rst_rl_82}),
        .fault_i({cland_f_rst_rl_82}), .ready_o(cland_r_rst_rl_81), .fault_o(cland_f_rst_rl_81));
    ot_dp_landing_collect #(.N(5)) u_cland_collect_rst_root_n (
        .clk(clk), .rst_n(rst_root_n), .ready_i({cland_r_rst_rl_0, cland_r_rst_rl_119, cland_r_rst_rl_163, cland_r_rst_rl_32, cland_r_rst_rl_81}),
        .fault_i({cland_f_rst_rl_0, cland_f_rst_rl_119, cland_f_rst_rl_163, cland_f_rst_rl_32, cland_f_rst_rl_81}), .ready_o(cland_up_ready), .fault_o(cland_up_fault));
assign ready=cland_up_ready;assign fault=cland_up_fault;endmodule
module gate(input clk,rst,input [6:0] r,f,output ready,fault);
wire rst_root_n=rst;
reg [9:0] rp=0; always @(posedge clk) rp <= {rp[8:0],rst};
wire rst_rl_0 = rp[0];
wire rst_rl_1 = rp[1];
wire rst_rl_2 = rp[2];
wire rst_rl_3 = rp[3];
wire rst_rl_4 = rp[4];
wire rst_rl_5 = rp[5];
wire rst_rl_6 = rp[6];
wire rst_rl_7 = rp[7];
wire rst_rl_8 = rp[8];
wire rr_t0 = rp[9];
wire rst_rl_10 = rp[3];
wire rst_rl_11 = rp[4];
wire rst_rl_12 = rp[5];
wire rst_rl_13 = rp[6];
wire rst_rl_14 = rp[7];
wire rst_rl_15 = rp[8];
wire rr_t4 = rp[9];
wire rst_rl_17 = rp[4];
wire rst_rl_18 = rp[5];
wire rst_rl_19 = rp[6];
wire rst_rl_20 = rp[7];
wire rst_rl_21 = rp[8];
wire rr_t8 = rp[9];
wire rst_rl_23 = rp[5];
wire rst_rl_24 = rp[6];
wire rst_rl_25 = rp[7];
wire rst_rl_26 = rp[8];
wire rr_t15 = rp[9];
wire rst_rl_28 = rp[6];
wire rst_rl_29 = rp[7];
wire rst_rl_30 = rp[8];
wire rr_t30 = rp[9];
wire rst_rl_32 = rp[0];
wire rst_rl_33 = rp[1];
wire rst_rl_34 = rp[2];
wire rst_rl_35 = rp[3];
wire rst_rl_36 = rp[4];
wire rst_rl_37 = rp[5];
wire rst_rl_38 = rp[6];
wire rst_rl_39 = rp[7];
wire rst_rl_40 = rp[8];
wire rr_t1 = rp[9];
wire rst_rl_42 = rp[3];
wire rst_rl_43 = rp[4];
wire rst_rl_44 = rp[5];
wire rst_rl_45 = rp[6];
wire rst_rl_46 = rp[7];
wire rst_rl_47 = rp[8];
wire rr_t18 = rp[9];
wire rr_t22 = rp[9];
wire rst_rl_50 = rp[4];
wire rst_rl_51 = rp[5];
wire rst_rl_52 = rp[6];
wire rst_rl_53 = rp[7];
wire rst_rl_54 = rp[8];
wire rr_t34 = rp[9];
wire rst_rl_56 = rp[8];
wire rr_t26 = rp[9];
wire rst_rl_58 = rp[2];
wire rst_rl_59 = rp[3];
wire rst_rl_60 = rp[4];
wire rst_rl_61 = rp[5];
wire rst_rl_62 = rp[6];
wire rst_rl_63 = rp[7];
wire rst_rl_64 = rp[8];
wire rr_t2 = rp[9];
wire rr_t6 = rp[9];
wire rst_rl_67 = rp[6];
wire rst_rl_68 = rp[7];
wire rst_rl_69 = rp[8];
wire rr_t10 = rp[9];
wire rst_rl_71 = rp[7];
wire rst_rl_72 = rp[8];
wire rr_t14 = rp[9];
wire rst_rl_74 = rp[0];
wire rst_rl_75 = rp[1];
wire rst_rl_76 = rp[2];
wire rst_rl_77 = rp[3];
wire rst_rl_78 = rp[4];
wire rst_rl_79 = rp[5];
wire rst_rl_80 = rp[6];
wire rst_rl_81 = rp[7];
wire rst_rl_82 = rp[8];
wire rr_t3 = rp[9];
wire rst_rl_84 = rp[3];
wire rst_rl_85 = rp[4];
wire rst_rl_86 = rp[5];
wire rst_rl_87 = rp[6];
wire rst_rl_88 = rp[7];
wire rst_rl_89 = rp[8];
wire rr_t7 = rp[9];
wire rst_rl_91 = rp[4];
wire rst_rl_92 = rp[5];
wire rst_rl_93 = rp[6];
wire rst_rl_94 = rp[7];
wire rst_rl_95 = rp[8];
wire rr_t11 = rp[9];
wire rst_rl_97 = rp[5];
wire rst_rl_98 = rp[6];
wire rst_rl_99 = rp[7];
wire rst_rl_100 = rp[8];
wire rr_t19 = rp[9];
wire rst_rl_102 = rp[8];
wire rr_t23 = rp[9];
wire rr_t27 = rp[9];
wire rst_rl_105 = rp[3];
wire rst_rl_106 = rp[4];
wire rst_rl_107 = rp[5];
wire rst_rl_108 = rp[6];
wire rst_rl_109 = rp[7];
wire rst_rl_110 = rp[8];
wire rr_t29 = rp[9];
wire rst_rl_112 = rp[1];
wire rst_rl_113 = rp[2];
wire rst_rl_114 = rp[3];
wire rst_rl_115 = rp[4];
wire rst_rl_116 = rp[5];
wire rst_rl_117 = rp[6];
wire rst_rl_118 = rp[7];
wire rst_rl_119 = rp[8];
wire rr_t5 = rp[9];
wire rr_t32 = rp[9];
wire rst_rl_122 = rp[4];
wire rst_rl_123 = rp[5];
wire rst_rl_124 = rp[6];
wire rst_rl_125 = rp[7];
wire rst_rl_126 = rp[8];
wire rr_t9 = rp[9];
wire rst_rl_128 = rp[5];
wire rst_rl_129 = rp[6];
wire rst_rl_130 = rp[7];
wire rst_rl_131 = rp[8];
wire rr_t17 = rp[9];
wire rst_rl_133 = rp[8];
wire rr_t21 = rp[9];
wire rr_t25 = rp[9];
wire rst_rl_136 = rp[7];
wire rst_rl_137 = rp[8];
wire rr_t33 = rp[9];
wire rst_rl_139 = rp[0];
wire rst_rl_140 = rp[1];
wire rst_rl_141 = rp[2];
wire rst_rl_142 = rp[3];
wire rst_rl_143 = rp[4];
wire rst_rl_144 = rp[5];
wire rst_rl_145 = rp[6];
wire rst_rl_146 = rp[7];
wire rst_rl_147 = rp[8];
wire rr_t12 = rp[9];
wire rst_rl_149 = rp[8];
wire rr_t13 = rp[9];
wire rst_rl_151 = rp[0];
wire rst_rl_152 = rp[1];
wire rst_rl_153 = rp[2];
wire rst_rl_154 = rp[3];
wire rst_rl_155 = rp[4];
wire rst_rl_156 = rp[5];
wire rst_rl_157 = rp[6];
wire rst_rl_158 = rp[7];
wire rst_rl_159 = rp[8];
wire rr_t16 = rp[9];
wire rst_rl_161 = rp[8];
wire rr_t20 = rp[9];
wire rr_t24 = rp[9];
wire rst_rl_164 = rp[0];
wire rst_rl_165 = rp[1];
wire rst_rl_166 = rp[2];
wire rst_rl_167 = rp[3];
wire rst_rl_168 = rp[4];
wire rst_rl_169 = rp[5];
wire rst_rl_170 = rp[6];
wire rst_rl_171 = rp[7];
wire rst_rl_172 = rp[8];
wire rr_t31 = rp[9];
wire rst_rl_174 = rp[6];
wire rst_rl_175 = rp[7];
wire rst_rl_176 = rp[8];
wire rr_t28 = rp[9];
wire cland_up_ready,cland_up_fault;
    wire cland_r_rst_n_t0, cland_f_rst_n_t0;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t0 (
        .clk(clk), .rst_n(rr_t0), .ready_i({r[0]}),
        .fault_i({f[0]}), .ready_o(cland_r_rst_n_t0), .fault_o(cland_f_rst_n_t0));
    wire cland_r_rst_n_t2, cland_f_rst_n_t2;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t2 (
        .clk(clk), .rst_n(rr_t2), .ready_i({r[1]}),
        .fault_i({f[1]}), .ready_o(cland_r_rst_n_t2), .fault_o(cland_f_rst_n_t2));
    wire cland_r_rst_n_t24, cland_f_rst_n_t24;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t24 (
        .clk(clk), .rst_n(rr_t24), .ready_i({r[2]}),
        .fault_i({f[2]}), .ready_o(cland_r_rst_n_t24), .fault_o(cland_f_rst_n_t24));
    wire cland_r_rst_n_t27, cland_f_rst_n_t27;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t27 (
        .clk(clk), .rst_n(rr_t27), .ready_i({r[3]}),
        .fault_i({f[3]}), .ready_o(cland_r_rst_n_t27), .fault_o(cland_f_rst_n_t27));
    wire cland_r_rst_n_t28, cland_f_rst_n_t28;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t28 (
        .clk(clk), .rst_n(rr_t28), .ready_i({r[5]}),
        .fault_i({f[5]}), .ready_o(cland_r_rst_n_t28), .fault_o(cland_f_rst_n_t28));
    wire cland_r_rst_n_t29, cland_f_rst_n_t29;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t29 (
        .clk(clk), .rst_n(rr_t29), .ready_i({r[6]}),
        .fault_i({f[6]}), .ready_o(cland_r_rst_n_t29), .fault_o(cland_f_rst_n_t29));
    wire cland_r_rst_n_t30, cland_f_rst_n_t30;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_n_t30 (
        .clk(clk), .rst_n(rr_t30), .ready_i({r[4]}),
        .fault_i({f[4]}), .ready_o(cland_r_rst_n_t30), .fault_o(cland_f_rst_n_t30));
    wire cland_r_rst_rl_102, cland_f_rst_rl_102;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_102 (
        .clk(clk), .rst_n(rst_rl_102), .ready_i({cland_r_rst_n_t27}),
        .fault_i({cland_f_rst_n_t27}), .ready_o(cland_r_rst_rl_102), .fault_o(cland_f_rst_rl_102));
    wire cland_r_rst_rl_110, cland_f_rst_rl_110;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_110 (
        .clk(clk), .rst_n(rst_rl_110), .ready_i({cland_r_rst_n_t29}),
        .fault_i({cland_f_rst_n_t29}), .ready_o(cland_r_rst_rl_110), .fault_o(cland_f_rst_rl_110));
    wire cland_r_rst_rl_161, cland_f_rst_rl_161;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_161 (
        .clk(clk), .rst_n(rst_rl_161), .ready_i({cland_r_rst_n_t24}),
        .fault_i({cland_f_rst_n_t24}), .ready_o(cland_r_rst_rl_161), .fault_o(cland_f_rst_rl_161));
    wire cland_r_rst_rl_176, cland_f_rst_rl_176;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_176 (
        .clk(clk), .rst_n(rst_rl_176), .ready_i({cland_r_rst_n_t28}),
        .fault_i({cland_f_rst_n_t28}), .ready_o(cland_r_rst_rl_176), .fault_o(cland_f_rst_rl_176));
    wire cland_r_rst_rl_30, cland_f_rst_rl_30;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_30 (
        .clk(clk), .rst_n(rst_rl_30), .ready_i({cland_r_rst_n_t30}),
        .fault_i({cland_f_rst_n_t30}), .ready_o(cland_r_rst_rl_30), .fault_o(cland_f_rst_rl_30));
    wire cland_r_rst_rl_64, cland_f_rst_rl_64;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_64 (
        .clk(clk), .rst_n(rst_rl_64), .ready_i({cland_r_rst_n_t2}),
        .fault_i({cland_f_rst_n_t2}), .ready_o(cland_r_rst_rl_64), .fault_o(cland_f_rst_rl_64));
    wire cland_r_rst_rl_8, cland_f_rst_rl_8;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_8 (
        .clk(clk), .rst_n(rst_rl_8), .ready_i({cland_r_rst_n_t0}),
        .fault_i({cland_f_rst_n_t0}), .ready_o(cland_r_rst_rl_8), .fault_o(cland_f_rst_rl_8));
    wire cland_r_rst_rl_109, cland_f_rst_rl_109;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_109 (
        .clk(clk), .rst_n(rst_rl_109), .ready_i({cland_r_rst_rl_110}),
        .fault_i({cland_f_rst_rl_110}), .ready_o(cland_r_rst_rl_109), .fault_o(cland_f_rst_rl_109));
    wire cland_r_rst_rl_158, cland_f_rst_rl_158;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_158 (
        .clk(clk), .rst_n(rst_rl_158), .ready_i({cland_r_rst_rl_161}),
        .fault_i({cland_f_rst_rl_161}), .ready_o(cland_r_rst_rl_158), .fault_o(cland_f_rst_rl_158));
    wire cland_r_rst_rl_175, cland_f_rst_rl_175;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_175 (
        .clk(clk), .rst_n(rst_rl_175), .ready_i({cland_r_rst_rl_176}),
        .fault_i({cland_f_rst_rl_176}), .ready_o(cland_r_rst_rl_175), .fault_o(cland_f_rst_rl_175));
    wire cland_r_rst_rl_29, cland_f_rst_rl_29;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_29 (
        .clk(clk), .rst_n(rst_rl_29), .ready_i({cland_r_rst_rl_30}),
        .fault_i({cland_f_rst_rl_30}), .ready_o(cland_r_rst_rl_29), .fault_o(cland_f_rst_rl_29));
    wire cland_r_rst_rl_63, cland_f_rst_rl_63;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_63 (
        .clk(clk), .rst_n(rst_rl_63), .ready_i({cland_r_rst_rl_64}),
        .fault_i({cland_f_rst_rl_64}), .ready_o(cland_r_rst_rl_63), .fault_o(cland_f_rst_rl_63));
    wire cland_r_rst_rl_7, cland_f_rst_rl_7;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_7 (
        .clk(clk), .rst_n(rst_rl_7), .ready_i({cland_r_rst_rl_8}),
        .fault_i({cland_f_rst_rl_8}), .ready_o(cland_r_rst_rl_7), .fault_o(cland_f_rst_rl_7));
    wire cland_r_rst_rl_99, cland_f_rst_rl_99;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_99 (
        .clk(clk), .rst_n(rst_rl_99), .ready_i({cland_r_rst_rl_102}),
        .fault_i({cland_f_rst_rl_102}), .ready_o(cland_r_rst_rl_99), .fault_o(cland_f_rst_rl_99));
    wire cland_r_rst_rl_108, cland_f_rst_rl_108;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_108 (
        .clk(clk), .rst_n(rst_rl_108), .ready_i({cland_r_rst_rl_109}),
        .fault_i({cland_f_rst_rl_109}), .ready_o(cland_r_rst_rl_108), .fault_o(cland_f_rst_rl_108));
    wire cland_r_rst_rl_157, cland_f_rst_rl_157;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_157 (
        .clk(clk), .rst_n(rst_rl_157), .ready_i({cland_r_rst_rl_158}),
        .fault_i({cland_f_rst_rl_158}), .ready_o(cland_r_rst_rl_157), .fault_o(cland_f_rst_rl_157));
    wire cland_r_rst_rl_174, cland_f_rst_rl_174;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_174 (
        .clk(clk), .rst_n(rst_rl_174), .ready_i({cland_r_rst_rl_175}),
        .fault_i({cland_f_rst_rl_175}), .ready_o(cland_r_rst_rl_174), .fault_o(cland_f_rst_rl_174));
    wire cland_r_rst_rl_28, cland_f_rst_rl_28;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_28 (
        .clk(clk), .rst_n(rst_rl_28), .ready_i({cland_r_rst_rl_29}),
        .fault_i({cland_f_rst_rl_29}), .ready_o(cland_r_rst_rl_28), .fault_o(cland_f_rst_rl_28));
    wire cland_r_rst_rl_6, cland_f_rst_rl_6;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_6 (
        .clk(clk), .rst_n(rst_rl_6), .ready_i({cland_r_rst_rl_7}),
        .fault_i({cland_f_rst_rl_7}), .ready_o(cland_r_rst_rl_6), .fault_o(cland_f_rst_rl_6));
    wire cland_r_rst_rl_62, cland_f_rst_rl_62;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_62 (
        .clk(clk), .rst_n(rst_rl_62), .ready_i({cland_r_rst_rl_63}),
        .fault_i({cland_f_rst_rl_63}), .ready_o(cland_r_rst_rl_62), .fault_o(cland_f_rst_rl_62));
    wire cland_r_rst_rl_98, cland_f_rst_rl_98;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_98 (
        .clk(clk), .rst_n(rst_rl_98), .ready_i({cland_r_rst_rl_99}),
        .fault_i({cland_f_rst_rl_99}), .ready_o(cland_r_rst_rl_98), .fault_o(cland_f_rst_rl_98));
    wire cland_r_rst_rl_107, cland_f_rst_rl_107;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_107 (
        .clk(clk), .rst_n(rst_rl_107), .ready_i({cland_r_rst_rl_108}),
        .fault_i({cland_f_rst_rl_108}), .ready_o(cland_r_rst_rl_107), .fault_o(cland_f_rst_rl_107));
    wire cland_r_rst_rl_156, cland_f_rst_rl_156;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_156 (
        .clk(clk), .rst_n(rst_rl_156), .ready_i({cland_r_rst_rl_157}),
        .fault_i({cland_f_rst_rl_157}), .ready_o(cland_r_rst_rl_156), .fault_o(cland_f_rst_rl_156));
    wire cland_r_rst_rl_169, cland_f_rst_rl_169;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_169 (
        .clk(clk), .rst_n(rst_rl_169), .ready_i({cland_r_rst_rl_174}),
        .fault_i({cland_f_rst_rl_174}), .ready_o(cland_r_rst_rl_169), .fault_o(cland_f_rst_rl_169));
    wire cland_r_rst_rl_23, cland_f_rst_rl_23;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_23 (
        .clk(clk), .rst_n(rst_rl_23), .ready_i({cland_r_rst_rl_28}),
        .fault_i({cland_f_rst_rl_28}), .ready_o(cland_r_rst_rl_23), .fault_o(cland_f_rst_rl_23));
    wire cland_r_rst_rl_5, cland_f_rst_rl_5;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_5 (
        .clk(clk), .rst_n(rst_rl_5), .ready_i({cland_r_rst_rl_6}),
        .fault_i({cland_f_rst_rl_6}), .ready_o(cland_r_rst_rl_5), .fault_o(cland_f_rst_rl_5));
    wire cland_r_rst_rl_61, cland_f_rst_rl_61;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_61 (
        .clk(clk), .rst_n(rst_rl_61), .ready_i({cland_r_rst_rl_62}),
        .fault_i({cland_f_rst_rl_62}), .ready_o(cland_r_rst_rl_61), .fault_o(cland_f_rst_rl_61));
    wire cland_r_rst_rl_97, cland_f_rst_rl_97;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_97 (
        .clk(clk), .rst_n(rst_rl_97), .ready_i({cland_r_rst_rl_98}),
        .fault_i({cland_f_rst_rl_98}), .ready_o(cland_r_rst_rl_97), .fault_o(cland_f_rst_rl_97));
    wire cland_r_rst_rl_106, cland_f_rst_rl_106;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_106 (
        .clk(clk), .rst_n(rst_rl_106), .ready_i({cland_r_rst_rl_107}),
        .fault_i({cland_f_rst_rl_107}), .ready_o(cland_r_rst_rl_106), .fault_o(cland_f_rst_rl_106));
    wire cland_r_rst_rl_155, cland_f_rst_rl_155;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_155 (
        .clk(clk), .rst_n(rst_rl_155), .ready_i({cland_r_rst_rl_156}),
        .fault_i({cland_f_rst_rl_156}), .ready_o(cland_r_rst_rl_155), .fault_o(cland_f_rst_rl_155));
    wire cland_r_rst_rl_168, cland_f_rst_rl_168;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_168 (
        .clk(clk), .rst_n(rst_rl_168), .ready_i({cland_r_rst_rl_169}),
        .fault_i({cland_f_rst_rl_169}), .ready_o(cland_r_rst_rl_168), .fault_o(cland_f_rst_rl_168));
    wire cland_r_rst_rl_17, cland_f_rst_rl_17;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_17 (
        .clk(clk), .rst_n(rst_rl_17), .ready_i({cland_r_rst_rl_23}),
        .fault_i({cland_f_rst_rl_23}), .ready_o(cland_r_rst_rl_17), .fault_o(cland_f_rst_rl_17));
    wire cland_r_rst_rl_4, cland_f_rst_rl_4;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_4 (
        .clk(clk), .rst_n(rst_rl_4), .ready_i({cland_r_rst_rl_5}),
        .fault_i({cland_f_rst_rl_5}), .ready_o(cland_r_rst_rl_4), .fault_o(cland_f_rst_rl_4));
    wire cland_r_rst_rl_60, cland_f_rst_rl_60;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_60 (
        .clk(clk), .rst_n(rst_rl_60), .ready_i({cland_r_rst_rl_61}),
        .fault_i({cland_f_rst_rl_61}), .ready_o(cland_r_rst_rl_60), .fault_o(cland_f_rst_rl_60));
    wire cland_r_rst_rl_91, cland_f_rst_rl_91;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_91 (
        .clk(clk), .rst_n(rst_rl_91), .ready_i({cland_r_rst_rl_97}),
        .fault_i({cland_f_rst_rl_97}), .ready_o(cland_r_rst_rl_91), .fault_o(cland_f_rst_rl_91));
    wire cland_r_rst_rl_10, cland_f_rst_rl_10;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_10 (
        .clk(clk), .rst_n(rst_rl_10), .ready_i({cland_r_rst_rl_17}),
        .fault_i({cland_f_rst_rl_17}), .ready_o(cland_r_rst_rl_10), .fault_o(cland_f_rst_rl_10));
    wire cland_r_rst_rl_105, cland_f_rst_rl_105;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_105 (
        .clk(clk), .rst_n(rst_rl_105), .ready_i({cland_r_rst_rl_106}),
        .fault_i({cland_f_rst_rl_106}), .ready_o(cland_r_rst_rl_105), .fault_o(cland_f_rst_rl_105));
    wire cland_r_rst_rl_154, cland_f_rst_rl_154;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_154 (
        .clk(clk), .rst_n(rst_rl_154), .ready_i({cland_r_rst_rl_155}),
        .fault_i({cland_f_rst_rl_155}), .ready_o(cland_r_rst_rl_154), .fault_o(cland_f_rst_rl_154));
    wire cland_r_rst_rl_167, cland_f_rst_rl_167;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_167 (
        .clk(clk), .rst_n(rst_rl_167), .ready_i({cland_r_rst_rl_168}),
        .fault_i({cland_f_rst_rl_168}), .ready_o(cland_r_rst_rl_167), .fault_o(cland_f_rst_rl_167));
    wire cland_r_rst_rl_3, cland_f_rst_rl_3;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_3 (
        .clk(clk), .rst_n(rst_rl_3), .ready_i({cland_r_rst_rl_4}),
        .fault_i({cland_f_rst_rl_4}), .ready_o(cland_r_rst_rl_3), .fault_o(cland_f_rst_rl_3));
    wire cland_r_rst_rl_59, cland_f_rst_rl_59;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_59 (
        .clk(clk), .rst_n(rst_rl_59), .ready_i({cland_r_rst_rl_60}),
        .fault_i({cland_f_rst_rl_60}), .ready_o(cland_r_rst_rl_59), .fault_o(cland_f_rst_rl_59));
    wire cland_r_rst_rl_84, cland_f_rst_rl_84;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_84 (
        .clk(clk), .rst_n(rst_rl_84), .ready_i({cland_r_rst_rl_91}),
        .fault_i({cland_f_rst_rl_91}), .ready_o(cland_r_rst_rl_84), .fault_o(cland_f_rst_rl_84));
    wire cland_r_rst_rl_153, cland_f_rst_rl_153;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_153 (
        .clk(clk), .rst_n(rst_rl_153), .ready_i({cland_r_rst_rl_154}),
        .fault_i({cland_f_rst_rl_154}), .ready_o(cland_r_rst_rl_153), .fault_o(cland_f_rst_rl_153));
    wire cland_r_rst_rl_166, cland_f_rst_rl_166;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_166 (
        .clk(clk), .rst_n(rst_rl_166), .ready_i({cland_r_rst_rl_167}),
        .fault_i({cland_f_rst_rl_167}), .ready_o(cland_r_rst_rl_166), .fault_o(cland_f_rst_rl_166));
    wire cland_r_rst_rl_2, cland_f_rst_rl_2;
    ot_dp_landing_collect #(.N(2)) u_cland_collect_rst_rl_2 (
        .clk(clk), .rst_n(rst_rl_2), .ready_i({cland_r_rst_rl_10, cland_r_rst_rl_3}),
        .fault_i({cland_f_rst_rl_10, cland_f_rst_rl_3}), .ready_o(cland_r_rst_rl_2), .fault_o(cland_f_rst_rl_2));
    wire cland_r_rst_rl_58, cland_f_rst_rl_58;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_58 (
        .clk(clk), .rst_n(rst_rl_58), .ready_i({cland_r_rst_rl_59}),
        .fault_i({cland_f_rst_rl_59}), .ready_o(cland_r_rst_rl_58), .fault_o(cland_f_rst_rl_58));
    wire cland_r_rst_rl_76, cland_f_rst_rl_76;
    ot_dp_landing_collect #(.N(2)) u_cland_collect_rst_rl_76 (
        .clk(clk), .rst_n(rst_rl_76), .ready_i({cland_r_rst_rl_105, cland_r_rst_rl_84}),
        .fault_i({cland_f_rst_rl_105, cland_f_rst_rl_84}), .ready_o(cland_r_rst_rl_76), .fault_o(cland_f_rst_rl_76));
    wire cland_r_rst_rl_1, cland_f_rst_rl_1;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_1 (
        .clk(clk), .rst_n(rst_rl_1), .ready_i({cland_r_rst_rl_2}),
        .fault_i({cland_f_rst_rl_2}), .ready_o(cland_r_rst_rl_1), .fault_o(cland_f_rst_rl_1));
    wire cland_r_rst_rl_152, cland_f_rst_rl_152;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_152 (
        .clk(clk), .rst_n(rst_rl_152), .ready_i({cland_r_rst_rl_153}),
        .fault_i({cland_f_rst_rl_153}), .ready_o(cland_r_rst_rl_152), .fault_o(cland_f_rst_rl_152));
    wire cland_r_rst_rl_165, cland_f_rst_rl_165;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_165 (
        .clk(clk), .rst_n(rst_rl_165), .ready_i({cland_r_rst_rl_166}),
        .fault_i({cland_f_rst_rl_166}), .ready_o(cland_r_rst_rl_165), .fault_o(cland_f_rst_rl_165));
    wire cland_r_rst_rl_33, cland_f_rst_rl_33;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_33 (
        .clk(clk), .rst_n(rst_rl_33), .ready_i({cland_r_rst_rl_58}),
        .fault_i({cland_f_rst_rl_58}), .ready_o(cland_r_rst_rl_33), .fault_o(cland_f_rst_rl_33));
    wire cland_r_rst_rl_75, cland_f_rst_rl_75;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_75 (
        .clk(clk), .rst_n(rst_rl_75), .ready_i({cland_r_rst_rl_76}),
        .fault_i({cland_f_rst_rl_76}), .ready_o(cland_r_rst_rl_75), .fault_o(cland_f_rst_rl_75));
    wire cland_r_rst_rl_0, cland_f_rst_rl_0;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_0 (
        .clk(clk), .rst_n(rst_rl_0), .ready_i({cland_r_rst_rl_1}),
        .fault_i({cland_f_rst_rl_1}), .ready_o(cland_r_rst_rl_0), .fault_o(cland_f_rst_rl_0));
    wire cland_r_rst_rl_151, cland_f_rst_rl_151;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_151 (
        .clk(clk), .rst_n(rst_rl_151), .ready_i({cland_r_rst_rl_152}),
        .fault_i({cland_f_rst_rl_152}), .ready_o(cland_r_rst_rl_151), .fault_o(cland_f_rst_rl_151));
    wire cland_r_rst_rl_164, cland_f_rst_rl_164;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_164 (
        .clk(clk), .rst_n(rst_rl_164), .ready_i({cland_r_rst_rl_165}),
        .fault_i({cland_f_rst_rl_165}), .ready_o(cland_r_rst_rl_164), .fault_o(cland_f_rst_rl_164));
    wire cland_r_rst_rl_32, cland_f_rst_rl_32;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_32 (
        .clk(clk), .rst_n(rst_rl_32), .ready_i({cland_r_rst_rl_33}),
        .fault_i({cland_f_rst_rl_33}), .ready_o(cland_r_rst_rl_32), .fault_o(cland_f_rst_rl_32));
    wire cland_r_rst_rl_74, cland_f_rst_rl_74;
    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_74 (
        .clk(clk), .rst_n(rst_rl_74), .ready_i({cland_r_rst_rl_75}),
        .fault_i({cland_f_rst_rl_75}), .ready_o(cland_r_rst_rl_74), .fault_o(cland_f_rst_rl_74));
    ot_dp_landing_collect #(.N(5)) u_cland_collect_rst_root_n (
        .clk(clk), .rst_n(rst_root_n), .ready_i({cland_r_rst_rl_0, cland_r_rst_rl_151, cland_r_rst_rl_164, cland_r_rst_rl_32, cland_r_rst_rl_74}),
        .fault_i({cland_f_rst_rl_0, cland_f_rst_rl_151, cland_f_rst_rl_164, cland_f_rst_rl_32, cland_f_rst_rl_74}), .ready_o(cland_up_ready), .fault_o(cland_up_fault));
assign ready=cland_up_ready;assign fault=cland_up_fault;endmodule
