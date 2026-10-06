// die_top_lint: port-identical REGISTERED STUBS of every placeholder master (generated abstract ports and
// widths; directions from the DIRECTION MODEL in tools/die_top_lint.py; x = conflicting across instances
// -> inout).  Outputs come from flops on the stub clock (ck[0] when the abstract has a clock port).

module qfd_chead (
    inout wire [387:0] e,
    inout wire [387:0] n,
    inout wire [387:0] s,
    inout wire [387:0] w
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^e, ^n, ^s, ^w};
    reg [386:0] r_n_0; always @(posedge lint_clk) r_n_0 <= {387{lint_in}}; assign n[386:0] = r_n_0;
    reg [386:0] r_s_0; always @(posedge lint_clk) r_s_0 <= {387{lint_in}}; assign s[386:0] = r_s_0;
endmodule

module qfd_cst (
    inout wire [387:0] a,
    inout wire [387:0] b,
    inout wire [324:0] tap
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b, ^tap};
    reg [323:0] r_tap_0; always @(posedge lint_clk) r_tap_0 <= {324{lint_in}}; assign tap[323:0] = r_tap_0;
endmodule

module qfd_ctrl (
    inout wire [612:0] c0,
    inout wire [612:0] c1,
    inout wire [612:0] c10,
    inout wire [612:0] c11,
    inout wire [612:0] c12,
    inout wire [612:0] c13,
    inout wire [612:0] c14,
    inout wire [612:0] c15,
    inout wire [612:0] c16,
    inout wire [612:0] c17,
    inout wire [612:0] c18,
    inout wire [612:0] c19,
    inout wire [612:0] c2,
    inout wire [612:0] c20,
    inout wire [612:0] c21,
    inout wire [612:0] c22,
    inout wire [612:0] c23,
    inout wire [612:0] c24,
    inout wire [612:0] c25,
    inout wire [612:0] c26,
    inout wire [612:0] c27,
    inout wire [612:0] c28,
    inout wire [612:0] c29,
    inout wire [612:0] c3,
    inout wire [612:0] c30,
    inout wire [612:0] c31,
    inout wire [612:0] c4,
    inout wire [612:0] c5,
    inout wire [612:0] c6,
    inout wire [612:0] c7,
    inout wire [612:0] c8,
    inout wire [612:0] c9,
    input wire [127:0] kv,
    inout wire [9208:0] phy
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^c0, ^c1, ^c10, ^c11, ^c12, ^c13, ^c14, ^c15, ^c16, ^c17, ^c18, ^c19, ^c2, ^c20, ^c21, ^c22, ^c23, ^c24, ^c25, ^c26, ^c27, ^c28, ^c29, ^c3, ^c30, ^c31, ^c4, ^c5, ^c6, ^c7, ^c8, ^c9, ^kv, ^phy};
    reg [281:0] r_c0_0; always @(posedge lint_clk) r_c0_0 <= {282{lint_in}}; assign c0[281:0] = r_c0_0;
    reg [1:0] r_c0_310; always @(posedge lint_clk) r_c0_310 <= {2{lint_in}}; assign c0[311:310] = r_c0_310;
    reg [9:0] r_c0_602; always @(posedge lint_clk) r_c0_602 <= {10{lint_in}}; assign c0[611:602] = r_c0_602;
    reg [281:0] r_c1_0; always @(posedge lint_clk) r_c1_0 <= {282{lint_in}}; assign c1[281:0] = r_c1_0;
    reg [1:0] r_c1_310; always @(posedge lint_clk) r_c1_310 <= {2{lint_in}}; assign c1[311:310] = r_c1_310;
    reg [9:0] r_c1_602; always @(posedge lint_clk) r_c1_602 <= {10{lint_in}}; assign c1[611:602] = r_c1_602;
    reg [281:0] r_c10_0; always @(posedge lint_clk) r_c10_0 <= {282{lint_in}}; assign c10[281:0] = r_c10_0;
    reg [1:0] r_c10_310; always @(posedge lint_clk) r_c10_310 <= {2{lint_in}}; assign c10[311:310] = r_c10_310;
    reg [9:0] r_c10_602; always @(posedge lint_clk) r_c10_602 <= {10{lint_in}}; assign c10[611:602] = r_c10_602;
    reg [281:0] r_c11_0; always @(posedge lint_clk) r_c11_0 <= {282{lint_in}}; assign c11[281:0] = r_c11_0;
    reg [1:0] r_c11_310; always @(posedge lint_clk) r_c11_310 <= {2{lint_in}}; assign c11[311:310] = r_c11_310;
    reg [9:0] r_c11_602; always @(posedge lint_clk) r_c11_602 <= {10{lint_in}}; assign c11[611:602] = r_c11_602;
    reg [281:0] r_c12_0; always @(posedge lint_clk) r_c12_0 <= {282{lint_in}}; assign c12[281:0] = r_c12_0;
    reg [1:0] r_c12_310; always @(posedge lint_clk) r_c12_310 <= {2{lint_in}}; assign c12[311:310] = r_c12_310;
    reg [9:0] r_c12_602; always @(posedge lint_clk) r_c12_602 <= {10{lint_in}}; assign c12[611:602] = r_c12_602;
    reg [281:0] r_c13_0; always @(posedge lint_clk) r_c13_0 <= {282{lint_in}}; assign c13[281:0] = r_c13_0;
    reg [1:0] r_c13_310; always @(posedge lint_clk) r_c13_310 <= {2{lint_in}}; assign c13[311:310] = r_c13_310;
    reg [9:0] r_c13_602; always @(posedge lint_clk) r_c13_602 <= {10{lint_in}}; assign c13[611:602] = r_c13_602;
    reg [281:0] r_c14_0; always @(posedge lint_clk) r_c14_0 <= {282{lint_in}}; assign c14[281:0] = r_c14_0;
    reg [1:0] r_c14_310; always @(posedge lint_clk) r_c14_310 <= {2{lint_in}}; assign c14[311:310] = r_c14_310;
    reg [9:0] r_c14_602; always @(posedge lint_clk) r_c14_602 <= {10{lint_in}}; assign c14[611:602] = r_c14_602;
    reg [281:0] r_c15_0; always @(posedge lint_clk) r_c15_0 <= {282{lint_in}}; assign c15[281:0] = r_c15_0;
    reg [1:0] r_c15_310; always @(posedge lint_clk) r_c15_310 <= {2{lint_in}}; assign c15[311:310] = r_c15_310;
    reg [9:0] r_c15_602; always @(posedge lint_clk) r_c15_602 <= {10{lint_in}}; assign c15[611:602] = r_c15_602;
    reg [281:0] r_c16_0; always @(posedge lint_clk) r_c16_0 <= {282{lint_in}}; assign c16[281:0] = r_c16_0;
    reg [1:0] r_c16_310; always @(posedge lint_clk) r_c16_310 <= {2{lint_in}}; assign c16[311:310] = r_c16_310;
    reg [9:0] r_c16_602; always @(posedge lint_clk) r_c16_602 <= {10{lint_in}}; assign c16[611:602] = r_c16_602;
    reg [281:0] r_c17_0; always @(posedge lint_clk) r_c17_0 <= {282{lint_in}}; assign c17[281:0] = r_c17_0;
    reg [1:0] r_c17_310; always @(posedge lint_clk) r_c17_310 <= {2{lint_in}}; assign c17[311:310] = r_c17_310;
    reg [9:0] r_c17_602; always @(posedge lint_clk) r_c17_602 <= {10{lint_in}}; assign c17[611:602] = r_c17_602;
    reg [281:0] r_c18_0; always @(posedge lint_clk) r_c18_0 <= {282{lint_in}}; assign c18[281:0] = r_c18_0;
    reg [1:0] r_c18_310; always @(posedge lint_clk) r_c18_310 <= {2{lint_in}}; assign c18[311:310] = r_c18_310;
    reg [9:0] r_c18_602; always @(posedge lint_clk) r_c18_602 <= {10{lint_in}}; assign c18[611:602] = r_c18_602;
    reg [281:0] r_c19_0; always @(posedge lint_clk) r_c19_0 <= {282{lint_in}}; assign c19[281:0] = r_c19_0;
    reg [1:0] r_c19_310; always @(posedge lint_clk) r_c19_310 <= {2{lint_in}}; assign c19[311:310] = r_c19_310;
    reg [9:0] r_c19_602; always @(posedge lint_clk) r_c19_602 <= {10{lint_in}}; assign c19[611:602] = r_c19_602;
    reg [281:0] r_c2_0; always @(posedge lint_clk) r_c2_0 <= {282{lint_in}}; assign c2[281:0] = r_c2_0;
    reg [1:0] r_c2_310; always @(posedge lint_clk) r_c2_310 <= {2{lint_in}}; assign c2[311:310] = r_c2_310;
    reg [9:0] r_c2_602; always @(posedge lint_clk) r_c2_602 <= {10{lint_in}}; assign c2[611:602] = r_c2_602;
    reg [281:0] r_c20_0; always @(posedge lint_clk) r_c20_0 <= {282{lint_in}}; assign c20[281:0] = r_c20_0;
    reg [1:0] r_c20_310; always @(posedge lint_clk) r_c20_310 <= {2{lint_in}}; assign c20[311:310] = r_c20_310;
    reg [9:0] r_c20_602; always @(posedge lint_clk) r_c20_602 <= {10{lint_in}}; assign c20[611:602] = r_c20_602;
    reg [281:0] r_c21_0; always @(posedge lint_clk) r_c21_0 <= {282{lint_in}}; assign c21[281:0] = r_c21_0;
    reg [1:0] r_c21_310; always @(posedge lint_clk) r_c21_310 <= {2{lint_in}}; assign c21[311:310] = r_c21_310;
    reg [9:0] r_c21_602; always @(posedge lint_clk) r_c21_602 <= {10{lint_in}}; assign c21[611:602] = r_c21_602;
    reg [281:0] r_c22_0; always @(posedge lint_clk) r_c22_0 <= {282{lint_in}}; assign c22[281:0] = r_c22_0;
    reg [1:0] r_c22_310; always @(posedge lint_clk) r_c22_310 <= {2{lint_in}}; assign c22[311:310] = r_c22_310;
    reg [9:0] r_c22_602; always @(posedge lint_clk) r_c22_602 <= {10{lint_in}}; assign c22[611:602] = r_c22_602;
    reg [281:0] r_c23_0; always @(posedge lint_clk) r_c23_0 <= {282{lint_in}}; assign c23[281:0] = r_c23_0;
    reg [1:0] r_c23_310; always @(posedge lint_clk) r_c23_310 <= {2{lint_in}}; assign c23[311:310] = r_c23_310;
    reg [9:0] r_c23_602; always @(posedge lint_clk) r_c23_602 <= {10{lint_in}}; assign c23[611:602] = r_c23_602;
    reg [281:0] r_c24_0; always @(posedge lint_clk) r_c24_0 <= {282{lint_in}}; assign c24[281:0] = r_c24_0;
    reg [1:0] r_c24_310; always @(posedge lint_clk) r_c24_310 <= {2{lint_in}}; assign c24[311:310] = r_c24_310;
    reg [9:0] r_c24_602; always @(posedge lint_clk) r_c24_602 <= {10{lint_in}}; assign c24[611:602] = r_c24_602;
    reg [281:0] r_c25_0; always @(posedge lint_clk) r_c25_0 <= {282{lint_in}}; assign c25[281:0] = r_c25_0;
    reg [1:0] r_c25_310; always @(posedge lint_clk) r_c25_310 <= {2{lint_in}}; assign c25[311:310] = r_c25_310;
    reg [9:0] r_c25_602; always @(posedge lint_clk) r_c25_602 <= {10{lint_in}}; assign c25[611:602] = r_c25_602;
    reg [281:0] r_c26_0; always @(posedge lint_clk) r_c26_0 <= {282{lint_in}}; assign c26[281:0] = r_c26_0;
    reg [1:0] r_c26_310; always @(posedge lint_clk) r_c26_310 <= {2{lint_in}}; assign c26[311:310] = r_c26_310;
    reg [9:0] r_c26_602; always @(posedge lint_clk) r_c26_602 <= {10{lint_in}}; assign c26[611:602] = r_c26_602;
    reg [281:0] r_c27_0; always @(posedge lint_clk) r_c27_0 <= {282{lint_in}}; assign c27[281:0] = r_c27_0;
    reg [1:0] r_c27_310; always @(posedge lint_clk) r_c27_310 <= {2{lint_in}}; assign c27[311:310] = r_c27_310;
    reg [9:0] r_c27_602; always @(posedge lint_clk) r_c27_602 <= {10{lint_in}}; assign c27[611:602] = r_c27_602;
    reg [281:0] r_c28_0; always @(posedge lint_clk) r_c28_0 <= {282{lint_in}}; assign c28[281:0] = r_c28_0;
    reg [1:0] r_c28_310; always @(posedge lint_clk) r_c28_310 <= {2{lint_in}}; assign c28[311:310] = r_c28_310;
    reg [9:0] r_c28_602; always @(posedge lint_clk) r_c28_602 <= {10{lint_in}}; assign c28[611:602] = r_c28_602;
    reg [281:0] r_c29_0; always @(posedge lint_clk) r_c29_0 <= {282{lint_in}}; assign c29[281:0] = r_c29_0;
    reg [1:0] r_c29_310; always @(posedge lint_clk) r_c29_310 <= {2{lint_in}}; assign c29[311:310] = r_c29_310;
    reg [9:0] r_c29_602; always @(posedge lint_clk) r_c29_602 <= {10{lint_in}}; assign c29[611:602] = r_c29_602;
    reg [281:0] r_c3_0; always @(posedge lint_clk) r_c3_0 <= {282{lint_in}}; assign c3[281:0] = r_c3_0;
    reg [1:0] r_c3_310; always @(posedge lint_clk) r_c3_310 <= {2{lint_in}}; assign c3[311:310] = r_c3_310;
    reg [9:0] r_c3_602; always @(posedge lint_clk) r_c3_602 <= {10{lint_in}}; assign c3[611:602] = r_c3_602;
    reg [281:0] r_c30_0; always @(posedge lint_clk) r_c30_0 <= {282{lint_in}}; assign c30[281:0] = r_c30_0;
    reg [1:0] r_c30_310; always @(posedge lint_clk) r_c30_310 <= {2{lint_in}}; assign c30[311:310] = r_c30_310;
    reg [9:0] r_c30_602; always @(posedge lint_clk) r_c30_602 <= {10{lint_in}}; assign c30[611:602] = r_c30_602;
    reg [281:0] r_c31_0; always @(posedge lint_clk) r_c31_0 <= {282{lint_in}}; assign c31[281:0] = r_c31_0;
    reg [1:0] r_c31_310; always @(posedge lint_clk) r_c31_310 <= {2{lint_in}}; assign c31[311:310] = r_c31_310;
    reg [9:0] r_c31_602; always @(posedge lint_clk) r_c31_602 <= {10{lint_in}}; assign c31[611:602] = r_c31_602;
    reg [281:0] r_c4_0; always @(posedge lint_clk) r_c4_0 <= {282{lint_in}}; assign c4[281:0] = r_c4_0;
    reg [1:0] r_c4_310; always @(posedge lint_clk) r_c4_310 <= {2{lint_in}}; assign c4[311:310] = r_c4_310;
    reg [9:0] r_c4_602; always @(posedge lint_clk) r_c4_602 <= {10{lint_in}}; assign c4[611:602] = r_c4_602;
    reg [281:0] r_c5_0; always @(posedge lint_clk) r_c5_0 <= {282{lint_in}}; assign c5[281:0] = r_c5_0;
    reg [1:0] r_c5_310; always @(posedge lint_clk) r_c5_310 <= {2{lint_in}}; assign c5[311:310] = r_c5_310;
    reg [9:0] r_c5_602; always @(posedge lint_clk) r_c5_602 <= {10{lint_in}}; assign c5[611:602] = r_c5_602;
    reg [281:0] r_c6_0; always @(posedge lint_clk) r_c6_0 <= {282{lint_in}}; assign c6[281:0] = r_c6_0;
    reg [1:0] r_c6_310; always @(posedge lint_clk) r_c6_310 <= {2{lint_in}}; assign c6[311:310] = r_c6_310;
    reg [9:0] r_c6_602; always @(posedge lint_clk) r_c6_602 <= {10{lint_in}}; assign c6[611:602] = r_c6_602;
    reg [281:0] r_c7_0; always @(posedge lint_clk) r_c7_0 <= {282{lint_in}}; assign c7[281:0] = r_c7_0;
    reg [1:0] r_c7_310; always @(posedge lint_clk) r_c7_310 <= {2{lint_in}}; assign c7[311:310] = r_c7_310;
    reg [9:0] r_c7_602; always @(posedge lint_clk) r_c7_602 <= {10{lint_in}}; assign c7[611:602] = r_c7_602;
    reg [281:0] r_c8_0; always @(posedge lint_clk) r_c8_0 <= {282{lint_in}}; assign c8[281:0] = r_c8_0;
    reg [1:0] r_c8_310; always @(posedge lint_clk) r_c8_310 <= {2{lint_in}}; assign c8[311:310] = r_c8_310;
    reg [9:0] r_c8_602; always @(posedge lint_clk) r_c8_602 <= {10{lint_in}}; assign c8[611:602] = r_c8_602;
    reg [281:0] r_c9_0; always @(posedge lint_clk) r_c9_0 <= {282{lint_in}}; assign c9[281:0] = r_c9_0;
    reg [1:0] r_c9_310; always @(posedge lint_clk) r_c9_310 <= {2{lint_in}}; assign c9[311:310] = r_c9_310;
    reg [9:0] r_c9_602; always @(posedge lint_clk) r_c9_602 <= {10{lint_in}}; assign c9[611:602] = r_c9_602;
    reg [2:0] r_phy_0; always @(posedge lint_clk) r_phy_0 <= {3{lint_in}}; assign phy[2:0] = r_phy_0;
    reg [308:0] r_phy_4; always @(posedge lint_clk) r_phy_4 <= {309{lint_in}}; assign phy[312:4] = r_phy_4;
    reg [31:0] r_phy_345; always @(posedge lint_clk) r_phy_345 <= {32{lint_in}}; assign phy[376:345] = r_phy_345;
endmodule

module qfd_hub (
    output wire [511:0] ar,
    input wire [2:0] ck,
    output wire [2:0] ckEN,
    output wire [2:0] ckES,
    output wire [2:0] ckWN,
    output wire [2:0] ckWS,
    output wire [2:0] cks,
    inout wire [2111:0] ln,
    inout wire [1055:0] lse,
    inout wire [1055:0] lsw,
    input wire [511:0] x3
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^ln, ^lse, ^lsw, ^x3};
    reg [511:0] r_ar_0; always @(posedge lint_clk) r_ar_0 <= {512{lint_in}}; assign ar[511:0] = r_ar_0;
    reg [2:0] r_ckEN_0; always @(posedge lint_clk) r_ckEN_0 <= {3{lint_in}}; assign ckEN[2:0] = r_ckEN_0;
    reg [2:0] r_ckES_0; always @(posedge lint_clk) r_ckES_0 <= {3{lint_in}}; assign ckES[2:0] = r_ckES_0;
    reg [2:0] r_ckWN_0; always @(posedge lint_clk) r_ckWN_0 <= {3{lint_in}}; assign ckWN[2:0] = r_ckWN_0;
    reg [2:0] r_ckWS_0; always @(posedge lint_clk) r_ckWS_0 <= {3{lint_in}}; assign ckWS[2:0] = r_ckWS_0;
    reg [2:0] r_cks_0; always @(posedge lint_clk) r_cks_0 <= {3{lint_in}}; assign cks[2:0] = r_cks_0;
    reg [527:0] r_ln_0; always @(posedge lint_clk) r_ln_0 <= {528{lint_in}}; assign ln[527:0] = r_ln_0;
    reg [527:0] r_ln_1056; always @(posedge lint_clk) r_ln_1056 <= {528{lint_in}}; assign ln[1583:1056] = r_ln_1056;
    reg [527:0] r_lse_0; always @(posedge lint_clk) r_lse_0 <= {528{lint_in}}; assign lse[527:0] = r_lse_0;
    reg [527:0] r_lsw_0; always @(posedge lint_clk) r_lsw_0 <= {528{lint_in}}; assign lsw[527:0] = r_lsw_0;
endmodule

module qfd_io_collective (
    output wire [2:0] ck,
    inout wire [1023:0] s,
    inout wire [65:0] sd,
    inout wire [1023:0] u,
    output wire [511:0] vr,
    input wire [511:0] vt
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^s, ^sd, ^u, ^vt};
    reg [2:0] r_ck_0; always @(posedge lint_clk) r_ck_0 <= {3{lint_in}}; assign ck[2:0] = r_ck_0;
    reg [511:0] r_s_0; always @(posedge lint_clk) r_s_0 <= {512{lint_in}}; assign s[511:0] = r_s_0;
    reg [0:0] r_sd_65; always @(posedge lint_clk) r_sd_65 <= {1{lint_in}}; assign sd[65:65] = r_sd_65;
    reg [511:0] r_u_0; always @(posedge lint_clk) r_u_0 <= {512{lint_in}}; assign u[511:0] = r_u_0;
    reg [511:0] r_vr_0; always @(posedge lint_clk) r_vr_0 <= {512{lint_in}}; assign vr[511:0] = r_vr_0;
endmodule

module qfd_io_embedding_rom (
    output wire [511:0] o
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{1'b0};
    reg [511:0] r_o_0; always @(posedge lint_clk) r_o_0 <= {512{lint_in}}; assign o[511:0] = r_o_0;
endmodule

module qfd_io_serdes (
    inout wire [1023:0] c
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^c};
    reg [511:0] r_c_512; always @(posedge lint_clk) r_c_512 <= {512{lint_in}}; assign c[1023:512] = r_c_512;
endmodule

module qfd_io_ucie (
    inout wire [1023:0] c
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^c};
    reg [511:0] r_c_512; always @(posedge lint_clk) r_c_512 <= {512{lint_in}}; assign c[1023:512] = r_c_512;
endmodule

module qfd_lfifo (
    input wire [2:0] ck,
    inout wire [1055:0] fn,
    inout wire [1055:0] fs,
    output wire [127:0] kv,
    inout wire [1055:0] lk
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^fn, ^fs, ^lk};
    reg [527:0] r_fn_0; always @(posedge lint_clk) r_fn_0 <= {528{lint_in}}; assign fn[527:0] = r_fn_0;
    reg [527:0] r_fs_0; always @(posedge lint_clk) r_fs_0 <= {528{lint_in}}; assign fs[527:0] = r_fs_0;
    reg [127:0] r_kv_0; always @(posedge lint_clk) r_kv_0 <= {128{lint_in}}; assign kv[127:0] = r_kv_0;
    reg [527:0] r_lk_528; always @(posedge lint_clk) r_lk_528 <= {528{lint_in}}; assign lk[1055:528] = r_lk_528;
endmodule

module qfd_lst_c (
    inout wire [1055:0] e,
    inout wire [2111:0] v,
    inout wire [1055:0] w
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^e, ^v, ^w};
    reg [527:0] r_e_0; always @(posedge lint_clk) r_e_0 <= {528{lint_in}}; assign e[527:0] = r_e_0;
    reg [527:0] r_v_528; always @(posedge lint_clk) r_v_528 <= {528{lint_in}}; assign v[1055:528] = r_v_528;
    reg [527:0] r_v_1584; always @(posedge lint_clk) r_v_1584 <= {528{lint_in}}; assign v[2111:1584] = r_v_1584;
    reg [527:0] r_w_0; always @(posedge lint_clk) r_w_0 <= {528{lint_in}}; assign w[527:0] = r_w_0;
endmodule

module qfd_lst_c_split (
    inout wire [1055:0] e,
    inout wire [1055:0] v,
    inout wire [1055:0] w
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^e, ^v, ^w};
    reg [527:0] r_e_0; always @(posedge lint_clk) r_e_0 <= {528{lint_in}}; assign e[527:0] = r_e_0;
    reg [527:0] r_v_528; always @(posedge lint_clk) r_v_528 <= {528{lint_in}}; assign v[1055:528] = r_v_528;
    reg [527:0] r_w_0; always @(posedge lint_clk) r_w_0 <= {528{lint_in}}; assign w[527:0] = r_w_0;
endmodule

module qfd_lst_h (
    inout wire [1055:0] e,
    inout wire [1055:0] w
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^e, ^w};
endmodule

module qfd_lst_v (
    inout wire [2111:0] a,
    inout wire [2111:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [527:0] r_a_528; always @(posedge lint_clk) r_a_528 <= {528{lint_in}}; assign a[1055:528] = r_a_528;
    reg [527:0] r_a_1584; always @(posedge lint_clk) r_a_1584 <= {528{lint_in}}; assign a[2111:1584] = r_a_1584;
    reg [527:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {528{lint_in}}; assign b[527:0] = r_b_0;
    reg [527:0] r_b_1056; always @(posedge lint_clk) r_b_1056 <= {528{lint_in}}; assign b[1583:1056] = r_b_1056;
endmodule

module qfd_lst_v_split (
    inout wire [1055:0] a,
    inout wire [1055:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [527:0] r_a_0; always @(posedge lint_clk) r_a_0 <= {528{lint_in}}; assign a[527:0] = r_a_0;
    reg [527:0] r_b_528; always @(posedge lint_clk) r_b_528 <= {528{lint_in}}; assign b[1055:528] = r_b_528;
endmodule

module qfd_port_tiles_0 (
    input wire [511:0] bw0,
    input wire [511:0] bw1,
    input wire [511:0] bw2,
    input wire [511:0] bw3,
    input wire [511:0] bw4,
    input wire [511:0] bw5,
    input wire [511:0] bw6,
    input wire [511:0] bw7,
    input wire [511:0] cf1,
    output wire [511:0] rw
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^bw0, ^bw1, ^bw2, ^bw3, ^bw4, ^bw5, ^bw6, ^bw7, ^cf1};
    reg [511:0] r_rw_0; always @(posedge lint_clk) r_rw_0 <= {512{lint_in}}; assign rw[511:0] = r_rw_0;
endmodule

module qfd_port_tiles_0_f1 (
    input wire [511:0] bw10,
    input wire [511:0] bw11,
    input wire [511:0] bw12,
    input wire [511:0] bw13,
    input wire [511:0] bw14,
    input wire [511:0] bw15,
    input wire [511:0] bw8,
    input wire [511:0] bw9,
    output wire [511:0] cw0
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^bw10, ^bw11, ^bw12, ^bw13, ^bw14, ^bw15, ^bw8, ^bw9};
    reg [511:0] r_cw0_0; always @(posedge lint_clk) r_cw0_0 <= {512{lint_in}}; assign cw0[511:0] = r_cw0_0;
endmodule

module qfd_port_tiles_1 (
    input wire [511:0] bw0,
    input wire [511:0] bw1,
    input wire [511:0] bw2,
    input wire [511:0] bw3,
    input wire [511:0] bw4,
    input wire [511:0] bw5,
    input wire [511:0] bw6,
    input wire [511:0] bw7,
    input wire [511:0] cf1,
    output wire [511:0] rw
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^bw0, ^bw1, ^bw2, ^bw3, ^bw4, ^bw5, ^bw6, ^bw7, ^cf1};
    reg [511:0] r_rw_0; always @(posedge lint_clk) r_rw_0 <= {512{lint_in}}; assign rw[511:0] = r_rw_0;
endmodule

module qfd_port_tiles_1_f1 (
    input wire [511:0] bw10,
    input wire [511:0] bw11,
    input wire [511:0] bw12,
    input wire [511:0] bw13,
    input wire [511:0] bw14,
    input wire [511:0] bw15,
    input wire [511:0] bw8,
    input wire [511:0] bw9,
    output wire [511:0] cw1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^bw10, ^bw11, ^bw12, ^bw13, ^bw14, ^bw15, ^bw8, ^bw9};
    reg [511:0] r_cw1_0; always @(posedge lint_clk) r_cw1_0 <= {512{lint_in}}; assign cw1[511:0] = r_cw1_0;
endmodule

module qfd_port_tiles_2 (
    input wire [511:0] bw0,
    input wire [511:0] bw1,
    input wire [511:0] bw2,
    input wire [511:0] bw3,
    input wire [511:0] bw4,
    input wire [511:0] bw5,
    input wire [511:0] bw6,
    input wire [511:0] cf1,
    input wire [511:0] cf2,
    input wire [511:0] cf3,
    output wire [511:0] rw
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^bw0, ^bw1, ^bw2, ^bw3, ^bw4, ^bw5, ^bw6, ^cf1, ^cf2, ^cf3};
    reg [511:0] r_rw_0; always @(posedge lint_clk) r_rw_0 <= {512{lint_in}}; assign rw[511:0] = r_rw_0;
endmodule

module qfd_port_tiles_2_f1 (
    input wire [511:0] bw10,
    input wire [511:0] bw11,
    input wire [511:0] bw12,
    input wire [511:0] bw8,
    input wire [511:0] bw9,
    output wire [511:0] cw2
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^bw10, ^bw11, ^bw12, ^bw8, ^bw9};
    reg [511:0] r_cw2_0; always @(posedge lint_clk) r_cw2_0 <= {512{lint_in}}; assign cw2[511:0] = r_cw2_0;
endmodule

module qfd_port_tiles_2_f2 (
    input wire [511:0] bw7,
    output wire [511:0] cw2
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^bw7};
    reg [511:0] r_cw2_0; always @(posedge lint_clk) r_cw2_0 <= {512{lint_in}}; assign cw2[511:0] = r_cw2_0;
endmodule

module qfd_port_tiles_2_f3 (
    input wire [511:0] bw13,
    input wire [511:0] bw14,
    input wire [511:0] bw15,
    output wire [511:0] cw2
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^bw13, ^bw14, ^bw15};
    reg [511:0] r_cw2_0; always @(posedge lint_clk) r_cw2_0 <= {512{lint_in}}; assign cw2[511:0] = r_cw2_0;
endmodule

module qfd_port_tiles_3 (
    input wire [511:0] bw0,
    input wire [511:0] bw1,
    input wire [511:0] bw2,
    input wire [511:0] bw3,
    input wire [511:0] bw4,
    input wire [511:0] bw5,
    input wire [511:0] cf1,
    input wire [511:0] cf2,
    input wire [511:0] cf3,
    output wire [511:0] rw
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^bw0, ^bw1, ^bw2, ^bw3, ^bw4, ^bw5, ^cf1, ^cf2, ^cf3};
    reg [511:0] r_rw_0; always @(posedge lint_clk) r_rw_0 <= {512{lint_in}}; assign rw[511:0] = r_rw_0;
endmodule

module qfd_port_tiles_3_f1 (
    input wire [511:0] bw10,
    input wire [511:0] bw11,
    input wire [511:0] bw12,
    input wire [511:0] bw13,
    input wire [511:0] bw14,
    input wire [511:0] bw8,
    input wire [511:0] bw9,
    output wire [511:0] cw3
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^bw10, ^bw11, ^bw12, ^bw13, ^bw14, ^bw8, ^bw9};
    reg [511:0] r_cw3_0; always @(posedge lint_clk) r_cw3_0 <= {512{lint_in}}; assign cw3[511:0] = r_cw3_0;
endmodule

module qfd_port_tiles_3_f2 (
    input wire [511:0] bw6,
    input wire [511:0] bw7,
    output wire [511:0] cw3
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^bw6, ^bw7};
    reg [511:0] r_cw3_0; always @(posedge lint_clk) r_cw3_0 <= {512{lint_in}}; assign cw3[511:0] = r_cw3_0;
endmodule

module qfd_port_tiles_3_f3 (
    input wire [511:0] bw15,
    output wire [511:0] cw3
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^bw15};
    reg [511:0] r_cw3_0; always @(posedge lint_clk) r_cw3_0 <= {512{lint_in}}; assign cw3[511:0] = r_cw3_0;
endmodule

module qfd_port_tiles_4 (
    input wire [511:0] bw0,
    input wire [511:0] bw1,
    input wire [511:0] bw2,
    input wire [511:0] bw3,
    input wire [511:0] bw4,
    input wire [511:0] bw5,
    input wire [511:0] bw6,
    input wire [511:0] bw7,
    input wire [511:0] cf1,
    output wire [511:0] rw
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^bw0, ^bw1, ^bw2, ^bw3, ^bw4, ^bw5, ^bw6, ^bw7, ^cf1};
    reg [511:0] r_rw_0; always @(posedge lint_clk) r_rw_0 <= {512{lint_in}}; assign rw[511:0] = r_rw_0;
endmodule

module qfd_port_tiles_4_f1 (
    input wire [511:0] bw10,
    input wire [511:0] bw11,
    input wire [511:0] bw12,
    input wire [511:0] bw13,
    input wire [511:0] bw14,
    input wire [511:0] bw15,
    input wire [511:0] bw8,
    input wire [511:0] bw9,
    output wire [511:0] cw4
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^bw10, ^bw11, ^bw12, ^bw13, ^bw14, ^bw15, ^bw8, ^bw9};
    reg [511:0] r_cw4_0; always @(posedge lint_clk) r_cw4_0 <= {512{lint_in}}; assign cw4[511:0] = r_cw4_0;
endmodule

module qfd_port_tiles_5 (
    input wire [511:0] bw0,
    input wire [511:0] bw1,
    input wire [511:0] bw2,
    input wire [511:0] bw3,
    input wire [511:0] bw4,
    input wire [511:0] bw5,
    input wire [511:0] bw6,
    input wire [511:0] bw7,
    input wire [511:0] cf1,
    output wire [511:0] rw
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^bw0, ^bw1, ^bw2, ^bw3, ^bw4, ^bw5, ^bw6, ^bw7, ^cf1};
    reg [511:0] r_rw_0; always @(posedge lint_clk) r_rw_0 <= {512{lint_in}}; assign rw[511:0] = r_rw_0;
endmodule

module qfd_port_tiles_5_f1 (
    input wire [511:0] bw10,
    input wire [511:0] bw11,
    input wire [511:0] bw12,
    input wire [511:0] bw13,
    input wire [511:0] bw14,
    input wire [511:0] bw15,
    input wire [511:0] bw8,
    input wire [511:0] bw9,
    output wire [511:0] cw5
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^bw10, ^bw11, ^bw12, ^bw13, ^bw14, ^bw15, ^bw8, ^bw9};
    reg [511:0] r_cw5_0; always @(posedge lint_clk) r_cw5_0 <= {512{lint_in}}; assign cw5[511:0] = r_cw5_0;
endmodule

module qfd_reng (
    inout wire [584:0] c0,
    inout wire [584:0] c1,
    inout wire [584:0] c2,
    inout wire [584:0] c3,
    inout wire [584:0] c4,
    inout wire [584:0] c5,
    inout wire [1055:0] fn,
    inout wire [1055:0] fs
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^c0, ^c1, ^c2, ^c3, ^c4, ^c5, ^fn, ^fs};
    reg [290:0] r_c0_282; always @(posedge lint_clk) r_c0_282 <= {291{lint_in}}; assign c0[572:282] = r_c0_282;
    reg [290:0] r_c1_282; always @(posedge lint_clk) r_c1_282 <= {291{lint_in}}; assign c1[572:282] = r_c1_282;
    reg [290:0] r_c2_282; always @(posedge lint_clk) r_c2_282 <= {291{lint_in}}; assign c2[572:282] = r_c2_282;
    reg [290:0] r_c3_282; always @(posedge lint_clk) r_c3_282 <= {291{lint_in}}; assign c3[572:282] = r_c3_282;
    reg [290:0] r_c4_282; always @(posedge lint_clk) r_c4_282 <= {291{lint_in}}; assign c4[572:282] = r_c4_282;
    reg [290:0] r_c5_282; always @(posedge lint_clk) r_c5_282 <= {291{lint_in}}; assign c5[572:282] = r_c5_282;
endmodule

module qfd_sp_constants_sequencer (
    input wire [1599:0] ca,
    inout wire [65:0] cd,
    output wire [4095:0] cq,
    inout wire [381:0] ib,
    input wire [1:0] md,
    input wire [1:0] sd,
    inout wire [491:0] su
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^ca, ^cd, ^ib, ^md, ^sd, ^su};
    reg [64:0] r_cd_0; always @(posedge lint_clk) r_cd_0 <= {65{lint_in}}; assign cd[64:0] = r_cd_0;
    reg [4095:0] r_cq_0; always @(posedge lint_clk) r_cq_0 <= {4096{lint_in}}; assign cq[4095:0] = r_cq_0;
    reg [380:0] r_ib_0; always @(posedge lint_clk) r_ib_0 <= {381{lint_in}}; assign ib[380:0] = r_ib_0;
    reg [490:0] r_su_0; always @(posedge lint_clk) r_su_0 <= {491{lint_in}}; assign su[490:0] = r_su_0;
endmodule

module qfd_sp_su64_sfu (
    output wire [1599:0] ca,
    input wire [2:0] ck,
    input wire [4095:0] cq,
    output wire [511:0] q,
    output wire [1:0] sd,
    inout wire [491:0] si
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^cq, ^si};
    reg [1599:0] r_ca_0; always @(posedge lint_clk) r_ca_0 <= {1600{lint_in}}; assign ca[1599:0] = r_ca_0;
    reg [511:0] r_q_0; always @(posedge lint_clk) r_q_0 <= {512{lint_in}}; assign q[511:0] = r_q_0;
    reg [1:0] r_sd_0; always @(posedge lint_clk) r_sd_0 <= {2{lint_in}}; assign sd[1:0] = r_sd_0;
    reg [0:0] r_si_491; always @(posedge lint_clk) r_si_491 <= {1{lint_in}}; assign si[491:491] = r_si_491;
endmodule

module qfd_sp_tree_top (
    input wire [511:0] bw0,
    input wire [511:0] bw1,
    input wire [511:0] bw2,
    input wire [511:0] bw3,
    input wire [511:0] bw4,
    input wire [511:0] bw5,
    output wire [1:0] md
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^bw0, ^bw1, ^bw2, ^bw3, ^bw4, ^bw5};
    reg [1:0] r_md_0; always @(posedge lint_clk) r_md_0 <= {2{lint_in}}; assign md[1:0] = r_md_0;
endmodule

module qfd_sp_vector_memory (
    input wire [511:0] ar,
    input wire [511:0] cr,
    output wire [511:0] ct,
    input wire [511:0] em,
    inout wire [381:0] ib,
    inout wire [387:0] xe,
    inout wire [387:0] xw
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^ar, ^cr, ^em, ^ib, ^xe, ^xw};
    reg [511:0] r_ct_0; always @(posedge lint_clk) r_ct_0 <= {512{lint_in}}; assign ct[511:0] = r_ct_0;
    reg [0:0] r_ib_381; always @(posedge lint_clk) r_ib_381 <= {1{lint_in}}; assign ib[381:381] = r_ib_381;
    reg [386:0] r_xe_0; always @(posedge lint_clk) r_xe_0 <= {387{lint_in}}; assign xe[386:0] = r_xe_0;
    reg [386:0] r_xw_0; always @(posedge lint_clk) r_xw_0 <= {387{lint_in}}; assign xw[386:0] = r_xw_0;
endmodule

module qfd_tile (
    input wire [511:0] n_a,
    input wire [511:0] n_b,
    output wire [511:0] n_y,
    output wire [511:0] t_out,
    inout wire [324:0] tap
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^n_a, ^n_b, ^tap};
    reg [511:0] r_n_y_0; always @(posedge lint_clk) r_n_y_0 <= {512{lint_in}}; assign n_y[511:0] = r_n_y_0;
    reg [511:0] r_t_out_0; always @(posedge lint_clk) r_t_out_0 <= {512{lint_in}}; assign t_out[511:0] = r_t_out_0;
    reg [0:0] r_tap_324; always @(posedge lint_clk) r_tap_324 <= {1{lint_in}}; assign tap[324:324] = r_tap_324;
endmodule
