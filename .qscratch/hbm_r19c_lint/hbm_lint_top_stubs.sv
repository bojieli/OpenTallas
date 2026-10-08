// die_top_lint: port-identical REGISTERED STUBS of every placeholder master (generated abstract ports and
// widths; directions from the DIRECTION MODEL in tools/die_top_lint.py; x = conflicting across instances
// -> inout).  Outputs come from flops on the stub clock (ck[0] when the abstract has a clock port).

module hfd_attn_tile (
    output wire [1617:0] cf,
    input wire [1617:0] ci,
    input wire [0:0] ck,
    input wire [528:0] i,
    input wire [1040:0] k,
    output wire [528:0] o,
    input wire [581:0] q,
    output wire [1617:0] rf,
    input wire [1617:0] ri,
    input wire [0:0] rst
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ci, ^ck, ^i, ^k, ^q, ^ri, ^rst};
    reg [1617:0] r_cf_0; always @(posedge lint_clk) r_cf_0 <= {1618{lint_in}}; assign cf[1617:0] = r_cf_0;
    reg [528:0] r_o_0; always @(posedge lint_clk) r_o_0 <= {529{lint_in}}; assign o[528:0] = r_o_0;
    reg [1617:0] r_rf_0; always @(posedge lint_clk) r_rf_0 <= {1618{lint_in}}; assign rf[1617:0] = r_rf_0;
endmodule

module hfd_barrier (
    input wire [0:0] ck,
    input wire [63:0] f_cmdproc,
    input wire [0:0] rst,
    output wire [63:0] t_cmdproc
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^f_cmdproc, ^rst};
    reg [63:0] r_t_cmdproc_0; always @(posedge lint_clk) r_t_cmdproc_0 <= {64{lint_in}}; assign t_cmdproc[63:0] = r_t_cmdproc_0;
endmodule

module hfd_cdist_r14 (
    inout wire [826:0] a,
    inout wire [413:0] b,
    input wire [0:0] ck,
    input wire [0:0] rst,
    inout wire [102:0] t0,
    inout wire [102:0] t1,
    inout wire [102:0] t2,
    inout wire [102:0] t3
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^a, ^b, ^ck, ^rst, ^t0, ^t1, ^t2, ^t3};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [0:0] r_a_102; always @(posedge lint_clk) r_a_102 <= {1{lint_in}}; assign a[102:102] = r_a_102;
    reg [2:0] r_a_145; always @(posedge lint_clk) r_a_145 <= {3{lint_in}}; assign a[147:145] = r_a_145;
    reg [0:0] r_a_205; always @(posedge lint_clk) r_a_205 <= {1{lint_in}}; assign a[205:205] = r_a_205;
    reg [2:0] r_a_248; always @(posedge lint_clk) r_a_248 <= {3{lint_in}}; assign a[250:248] = r_a_248;
    reg [0:0] r_a_308; always @(posedge lint_clk) r_a_308 <= {1{lint_in}}; assign a[308:308] = r_a_308;
    reg [2:0] r_a_351; always @(posedge lint_clk) r_a_351 <= {3{lint_in}}; assign a[353:351] = r_a_351;
    reg [0:0] r_a_411; always @(posedge lint_clk) r_a_411 <= {1{lint_in}}; assign a[411:411] = r_a_411;
    reg [2:0] r_a_454; always @(posedge lint_clk) r_a_454 <= {3{lint_in}}; assign a[456:454] = r_a_454;
    reg [0:0] r_a_514; always @(posedge lint_clk) r_a_514 <= {1{lint_in}}; assign a[514:514] = r_a_514;
    reg [2:0] r_a_557; always @(posedge lint_clk) r_a_557 <= {3{lint_in}}; assign a[559:557] = r_a_557;
    reg [0:0] r_a_617; always @(posedge lint_clk) r_a_617 <= {1{lint_in}}; assign a[617:617] = r_a_617;
    reg [2:0] r_a_660; always @(posedge lint_clk) r_a_660 <= {3{lint_in}}; assign a[662:660] = r_a_660;
    reg [0:0] r_a_720; always @(posedge lint_clk) r_a_720 <= {1{lint_in}}; assign a[720:720] = r_a_720;
    reg [2:0] r_a_763; always @(posedge lint_clk) r_a_763 <= {3{lint_in}}; assign a[765:763] = r_a_763;
    reg [0:0] r_a_823; always @(posedge lint_clk) r_a_823 <= {1{lint_in}}; assign a[823:823] = r_a_823;
    reg [0:0] r_a_826; always @(posedge lint_clk) r_a_826 <= {1{lint_in}}; assign a[826:826] = r_a_826;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [56:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {57{lint_in}}; assign b[101:45] = r_b_45;
    reg [41:0] r_b_103; always @(posedge lint_clk) r_b_103 <= {42{lint_in}}; assign b[144:103] = r_b_103;
    reg [56:0] r_b_148; always @(posedge lint_clk) r_b_148 <= {57{lint_in}}; assign b[204:148] = r_b_148;
    reg [41:0] r_b_206; always @(posedge lint_clk) r_b_206 <= {42{lint_in}}; assign b[247:206] = r_b_206;
    reg [56:0] r_b_251; always @(posedge lint_clk) r_b_251 <= {57{lint_in}}; assign b[307:251] = r_b_251;
    reg [41:0] r_b_309; always @(posedge lint_clk) r_b_309 <= {42{lint_in}}; assign b[350:309] = r_b_309;
    reg [56:0] r_b_354; always @(posedge lint_clk) r_b_354 <= {57{lint_in}}; assign b[410:354] = r_b_354;
    reg [0:0] r_b_412; always @(posedge lint_clk) r_b_412 <= {1{lint_in}}; assign b[412:412] = r_b_412;
    reg [41:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {42{lint_in}}; assign t0[41:0] = r_t0_0;
    reg [56:0] r_t0_45; always @(posedge lint_clk) r_t0_45 <= {57{lint_in}}; assign t0[101:45] = r_t0_45;
    reg [41:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {42{lint_in}}; assign t1[41:0] = r_t1_0;
    reg [56:0] r_t1_45; always @(posedge lint_clk) r_t1_45 <= {57{lint_in}}; assign t1[101:45] = r_t1_45;
    reg [41:0] r_t2_0; always @(posedge lint_clk) r_t2_0 <= {42{lint_in}}; assign t2[41:0] = r_t2_0;
    reg [56:0] r_t2_45; always @(posedge lint_clk) r_t2_45 <= {57{lint_in}}; assign t2[101:45] = r_t2_45;
    reg [41:0] r_t3_0; always @(posedge lint_clk) r_t3_0 <= {42{lint_in}}; assign t3[41:0] = r_t3_0;
    reg [56:0] r_t3_45; always @(posedge lint_clk) r_t3_45 <= {57{lint_in}}; assign t3[101:45] = r_t3_45;
endmodule

module hfd_cdist_r15 (
    inout wire [413:0] a,
    input wire [0:0] ck,
    input wire [0:0] rst,
    inout wire [102:0] t0,
    inout wire [102:0] t1,
    inout wire [102:0] t2,
    inout wire [102:0] t3
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^a, ^ck, ^rst, ^t0, ^t1, ^t2, ^t3};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [0:0] r_a_102; always @(posedge lint_clk) r_a_102 <= {1{lint_in}}; assign a[102:102] = r_a_102;
    reg [2:0] r_a_145; always @(posedge lint_clk) r_a_145 <= {3{lint_in}}; assign a[147:145] = r_a_145;
    reg [0:0] r_a_205; always @(posedge lint_clk) r_a_205 <= {1{lint_in}}; assign a[205:205] = r_a_205;
    reg [2:0] r_a_248; always @(posedge lint_clk) r_a_248 <= {3{lint_in}}; assign a[250:248] = r_a_248;
    reg [0:0] r_a_308; always @(posedge lint_clk) r_a_308 <= {1{lint_in}}; assign a[308:308] = r_a_308;
    reg [2:0] r_a_351; always @(posedge lint_clk) r_a_351 <= {3{lint_in}}; assign a[353:351] = r_a_351;
    reg [0:0] r_a_411; always @(posedge lint_clk) r_a_411 <= {1{lint_in}}; assign a[411:411] = r_a_411;
    reg [0:0] r_a_413; always @(posedge lint_clk) r_a_413 <= {1{lint_in}}; assign a[413:413] = r_a_413;
    reg [41:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {42{lint_in}}; assign t0[41:0] = r_t0_0;
    reg [56:0] r_t0_45; always @(posedge lint_clk) r_t0_45 <= {57{lint_in}}; assign t0[101:45] = r_t0_45;
    reg [41:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {42{lint_in}}; assign t1[41:0] = r_t1_0;
    reg [56:0] r_t1_45; always @(posedge lint_clk) r_t1_45 <= {57{lint_in}}; assign t1[101:45] = r_t1_45;
    reg [41:0] r_t2_0; always @(posedge lint_clk) r_t2_0 <= {42{lint_in}}; assign t2[41:0] = r_t2_0;
    reg [56:0] r_t2_45; always @(posedge lint_clk) r_t2_45 <= {57{lint_in}}; assign t2[101:45] = r_t2_45;
    reg [41:0] r_t3_0; always @(posedge lint_clk) r_t3_0 <= {42{lint_in}}; assign t3[41:0] = r_t3_0;
    reg [56:0] r_t3_45; always @(posedge lint_clk) r_t3_45 <= {57{lint_in}}; assign t3[101:45] = r_t3_45;
endmodule

module hfd_cmdproc_n (
    inout wire [826:0] cNE,
    inout wire [826:0] cNW,
    input wire [0:0] ck,
    input wire [63:0] f_barrier,
    input wire [32:0] f_coll,
    input wire [0:0] rst,
    output wire [63:0] t_barrier,
    output wire [24:0] t_coll,
    output wire [63:0] t_su_NE,
    output wire [63:0] t_su_NW,
    input wire [15:0] xb,
    input wire [146:0] xl,
    input wire [15:0] xt
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^cNE, ^cNW, ^ck, ^f_barrier, ^f_coll, ^rst, ^xb, ^xl, ^xt};
    reg [41:0] r_cNE_0; always @(posedge lint_clk) r_cNE_0 <= {42{lint_in}}; assign cNE[41:0] = r_cNE_0;
    reg [56:0] r_cNE_45; always @(posedge lint_clk) r_cNE_45 <= {57{lint_in}}; assign cNE[101:45] = r_cNE_45;
    reg [41:0] r_cNE_103; always @(posedge lint_clk) r_cNE_103 <= {42{lint_in}}; assign cNE[144:103] = r_cNE_103;
    reg [56:0] r_cNE_148; always @(posedge lint_clk) r_cNE_148 <= {57{lint_in}}; assign cNE[204:148] = r_cNE_148;
    reg [41:0] r_cNE_206; always @(posedge lint_clk) r_cNE_206 <= {42{lint_in}}; assign cNE[247:206] = r_cNE_206;
    reg [56:0] r_cNE_251; always @(posedge lint_clk) r_cNE_251 <= {57{lint_in}}; assign cNE[307:251] = r_cNE_251;
    reg [41:0] r_cNE_309; always @(posedge lint_clk) r_cNE_309 <= {42{lint_in}}; assign cNE[350:309] = r_cNE_309;
    reg [56:0] r_cNE_354; always @(posedge lint_clk) r_cNE_354 <= {57{lint_in}}; assign cNE[410:354] = r_cNE_354;
    reg [41:0] r_cNE_412; always @(posedge lint_clk) r_cNE_412 <= {42{lint_in}}; assign cNE[453:412] = r_cNE_412;
    reg [56:0] r_cNE_457; always @(posedge lint_clk) r_cNE_457 <= {57{lint_in}}; assign cNE[513:457] = r_cNE_457;
    reg [41:0] r_cNE_515; always @(posedge lint_clk) r_cNE_515 <= {42{lint_in}}; assign cNE[556:515] = r_cNE_515;
    reg [56:0] r_cNE_560; always @(posedge lint_clk) r_cNE_560 <= {57{lint_in}}; assign cNE[616:560] = r_cNE_560;
    reg [41:0] r_cNE_618; always @(posedge lint_clk) r_cNE_618 <= {42{lint_in}}; assign cNE[659:618] = r_cNE_618;
    reg [56:0] r_cNE_663; always @(posedge lint_clk) r_cNE_663 <= {57{lint_in}}; assign cNE[719:663] = r_cNE_663;
    reg [41:0] r_cNE_721; always @(posedge lint_clk) r_cNE_721 <= {42{lint_in}}; assign cNE[762:721] = r_cNE_721;
    reg [56:0] r_cNE_766; always @(posedge lint_clk) r_cNE_766 <= {57{lint_in}}; assign cNE[822:766] = r_cNE_766;
    reg [1:0] r_cNE_824; always @(posedge lint_clk) r_cNE_824 <= {2{lint_in}}; assign cNE[825:824] = r_cNE_824;
    reg [41:0] r_cNW_0; always @(posedge lint_clk) r_cNW_0 <= {42{lint_in}}; assign cNW[41:0] = r_cNW_0;
    reg [56:0] r_cNW_45; always @(posedge lint_clk) r_cNW_45 <= {57{lint_in}}; assign cNW[101:45] = r_cNW_45;
    reg [41:0] r_cNW_103; always @(posedge lint_clk) r_cNW_103 <= {42{lint_in}}; assign cNW[144:103] = r_cNW_103;
    reg [56:0] r_cNW_148; always @(posedge lint_clk) r_cNW_148 <= {57{lint_in}}; assign cNW[204:148] = r_cNW_148;
    reg [41:0] r_cNW_206; always @(posedge lint_clk) r_cNW_206 <= {42{lint_in}}; assign cNW[247:206] = r_cNW_206;
    reg [56:0] r_cNW_251; always @(posedge lint_clk) r_cNW_251 <= {57{lint_in}}; assign cNW[307:251] = r_cNW_251;
    reg [41:0] r_cNW_309; always @(posedge lint_clk) r_cNW_309 <= {42{lint_in}}; assign cNW[350:309] = r_cNW_309;
    reg [56:0] r_cNW_354; always @(posedge lint_clk) r_cNW_354 <= {57{lint_in}}; assign cNW[410:354] = r_cNW_354;
    reg [41:0] r_cNW_412; always @(posedge lint_clk) r_cNW_412 <= {42{lint_in}}; assign cNW[453:412] = r_cNW_412;
    reg [56:0] r_cNW_457; always @(posedge lint_clk) r_cNW_457 <= {57{lint_in}}; assign cNW[513:457] = r_cNW_457;
    reg [41:0] r_cNW_515; always @(posedge lint_clk) r_cNW_515 <= {42{lint_in}}; assign cNW[556:515] = r_cNW_515;
    reg [56:0] r_cNW_560; always @(posedge lint_clk) r_cNW_560 <= {57{lint_in}}; assign cNW[616:560] = r_cNW_560;
    reg [41:0] r_cNW_618; always @(posedge lint_clk) r_cNW_618 <= {42{lint_in}}; assign cNW[659:618] = r_cNW_618;
    reg [56:0] r_cNW_663; always @(posedge lint_clk) r_cNW_663 <= {57{lint_in}}; assign cNW[719:663] = r_cNW_663;
    reg [41:0] r_cNW_721; always @(posedge lint_clk) r_cNW_721 <= {42{lint_in}}; assign cNW[762:721] = r_cNW_721;
    reg [56:0] r_cNW_766; always @(posedge lint_clk) r_cNW_766 <= {57{lint_in}}; assign cNW[822:766] = r_cNW_766;
    reg [1:0] r_cNW_824; always @(posedge lint_clk) r_cNW_824 <= {2{lint_in}}; assign cNW[825:824] = r_cNW_824;
    reg [63:0] r_t_barrier_0; always @(posedge lint_clk) r_t_barrier_0 <= {64{lint_in}}; assign t_barrier[63:0] = r_t_barrier_0;
    reg [24:0] r_t_coll_0; always @(posedge lint_clk) r_t_coll_0 <= {25{lint_in}}; assign t_coll[24:0] = r_t_coll_0;
    reg [63:0] r_t_su_NE_0; always @(posedge lint_clk) r_t_su_NE_0 <= {64{lint_in}}; assign t_su_NE[63:0] = r_t_su_NE_0;
    reg [63:0] r_t_su_NW_0; always @(posedge lint_clk) r_t_su_NW_0 <= {64{lint_in}}; assign t_su_NW[63:0] = r_t_su_NW_0;
endmodule

module hfd_cmdproc_s (
    inout wire [826:0] cSE,
    inout wire [826:0] cSW,
    input wire [0:0] ck,
    input wire [340:0] f_loader,
    input wire [63:0] f_router,
    input wire [0:0] rst,
    output wire [63:0] t_su_SE,
    output wire [63:0] t_su_SW,
    input wire [15:0] xb,
    input wire [146:0] xl,
    input wire [15:0] xt
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^cSE, ^cSW, ^ck, ^f_loader, ^f_router, ^rst, ^xb, ^xl, ^xt};
    reg [41:0] r_cSE_0; always @(posedge lint_clk) r_cSE_0 <= {42{lint_in}}; assign cSE[41:0] = r_cSE_0;
    reg [56:0] r_cSE_45; always @(posedge lint_clk) r_cSE_45 <= {57{lint_in}}; assign cSE[101:45] = r_cSE_45;
    reg [41:0] r_cSE_103; always @(posedge lint_clk) r_cSE_103 <= {42{lint_in}}; assign cSE[144:103] = r_cSE_103;
    reg [56:0] r_cSE_148; always @(posedge lint_clk) r_cSE_148 <= {57{lint_in}}; assign cSE[204:148] = r_cSE_148;
    reg [41:0] r_cSE_206; always @(posedge lint_clk) r_cSE_206 <= {42{lint_in}}; assign cSE[247:206] = r_cSE_206;
    reg [56:0] r_cSE_251; always @(posedge lint_clk) r_cSE_251 <= {57{lint_in}}; assign cSE[307:251] = r_cSE_251;
    reg [41:0] r_cSE_309; always @(posedge lint_clk) r_cSE_309 <= {42{lint_in}}; assign cSE[350:309] = r_cSE_309;
    reg [56:0] r_cSE_354; always @(posedge lint_clk) r_cSE_354 <= {57{lint_in}}; assign cSE[410:354] = r_cSE_354;
    reg [41:0] r_cSE_412; always @(posedge lint_clk) r_cSE_412 <= {42{lint_in}}; assign cSE[453:412] = r_cSE_412;
    reg [56:0] r_cSE_457; always @(posedge lint_clk) r_cSE_457 <= {57{lint_in}}; assign cSE[513:457] = r_cSE_457;
    reg [41:0] r_cSE_515; always @(posedge lint_clk) r_cSE_515 <= {42{lint_in}}; assign cSE[556:515] = r_cSE_515;
    reg [56:0] r_cSE_560; always @(posedge lint_clk) r_cSE_560 <= {57{lint_in}}; assign cSE[616:560] = r_cSE_560;
    reg [41:0] r_cSE_618; always @(posedge lint_clk) r_cSE_618 <= {42{lint_in}}; assign cSE[659:618] = r_cSE_618;
    reg [56:0] r_cSE_663; always @(posedge lint_clk) r_cSE_663 <= {57{lint_in}}; assign cSE[719:663] = r_cSE_663;
    reg [41:0] r_cSE_721; always @(posedge lint_clk) r_cSE_721 <= {42{lint_in}}; assign cSE[762:721] = r_cSE_721;
    reg [56:0] r_cSE_766; always @(posedge lint_clk) r_cSE_766 <= {57{lint_in}}; assign cSE[822:766] = r_cSE_766;
    reg [1:0] r_cSE_824; always @(posedge lint_clk) r_cSE_824 <= {2{lint_in}}; assign cSE[825:824] = r_cSE_824;
    reg [41:0] r_cSW_0; always @(posedge lint_clk) r_cSW_0 <= {42{lint_in}}; assign cSW[41:0] = r_cSW_0;
    reg [56:0] r_cSW_45; always @(posedge lint_clk) r_cSW_45 <= {57{lint_in}}; assign cSW[101:45] = r_cSW_45;
    reg [41:0] r_cSW_103; always @(posedge lint_clk) r_cSW_103 <= {42{lint_in}}; assign cSW[144:103] = r_cSW_103;
    reg [56:0] r_cSW_148; always @(posedge lint_clk) r_cSW_148 <= {57{lint_in}}; assign cSW[204:148] = r_cSW_148;
    reg [41:0] r_cSW_206; always @(posedge lint_clk) r_cSW_206 <= {42{lint_in}}; assign cSW[247:206] = r_cSW_206;
    reg [56:0] r_cSW_251; always @(posedge lint_clk) r_cSW_251 <= {57{lint_in}}; assign cSW[307:251] = r_cSW_251;
    reg [41:0] r_cSW_309; always @(posedge lint_clk) r_cSW_309 <= {42{lint_in}}; assign cSW[350:309] = r_cSW_309;
    reg [56:0] r_cSW_354; always @(posedge lint_clk) r_cSW_354 <= {57{lint_in}}; assign cSW[410:354] = r_cSW_354;
    reg [41:0] r_cSW_412; always @(posedge lint_clk) r_cSW_412 <= {42{lint_in}}; assign cSW[453:412] = r_cSW_412;
    reg [56:0] r_cSW_457; always @(posedge lint_clk) r_cSW_457 <= {57{lint_in}}; assign cSW[513:457] = r_cSW_457;
    reg [41:0] r_cSW_515; always @(posedge lint_clk) r_cSW_515 <= {42{lint_in}}; assign cSW[556:515] = r_cSW_515;
    reg [56:0] r_cSW_560; always @(posedge lint_clk) r_cSW_560 <= {57{lint_in}}; assign cSW[616:560] = r_cSW_560;
    reg [41:0] r_cSW_618; always @(posedge lint_clk) r_cSW_618 <= {42{lint_in}}; assign cSW[659:618] = r_cSW_618;
    reg [56:0] r_cSW_663; always @(posedge lint_clk) r_cSW_663 <= {57{lint_in}}; assign cSW[719:663] = r_cSW_663;
    reg [41:0] r_cSW_721; always @(posedge lint_clk) r_cSW_721 <= {42{lint_in}}; assign cSW[762:721] = r_cSW_721;
    reg [56:0] r_cSW_766; always @(posedge lint_clk) r_cSW_766 <= {57{lint_in}}; assign cSW[822:766] = r_cSW_766;
    reg [1:0] r_cSW_824; always @(posedge lint_clk) r_cSW_824 <= {2{lint_in}}; assign cSW[825:824] = r_cSW_824;
    reg [63:0] r_t_su_SE_0; always @(posedge lint_clk) r_t_su_SE_0 <= {64{lint_in}}; assign t_su_SE[63:0] = r_t_su_SE_0;
    reg [63:0] r_t_su_SW_0; always @(posedge lint_clk) r_t_su_SW_0 <= {64{lint_in}}; assign t_su_SW[63:0] = r_t_su_SW_0;
endmodule

module hfd_coll (
    input wire [24:0] f_cmdproc,
    input wire [1023:0] f_su_NE,
    input wire [1023:0] f_su_NW,
    input wire [1023:0] f_su_SE,
    input wire [1023:0] f_su_SW,
    inout wire [975:0] llk_N0,
    inout wire [975:0] llk_N1,
    inout wire [975:0] llk_N2,
    inout wire [975:0] llk_N3,
    inout wire [975:0] llk_S0,
    inout wire [975:0] llk_S1,
    inout wire [975:0] llk_S2,
    inout wire [975:0] llk_S3,
    inout wire [975:0] llk_S4,
    output wire [0:0] pll_hbm,
    output wire [0:0] pll_link,
    output wire [0:0] pll_serial,
    output wire [0:0] pll_stream,
    output wire [0:0] por_hbm,
    output wire [0:0] por_link,
    output wire [0:0] por_serial,
    output wire [0:0] por_stream,
    output wire [32:0] t_cmdproc,
    output wire [579:0] t_su_NE,
    output wire [579:0] t_su_NW,
    output wire [579:0] t_su_SE,
    output wire [579:0] t_su_SW
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^f_cmdproc, ^f_su_NE, ^f_su_NW, ^f_su_SE, ^f_su_SW, ^llk_N0, ^llk_N1, ^llk_N2, ^llk_N3, ^llk_S0, ^llk_S1, ^llk_S2, ^llk_S3, ^llk_S4};
    reg [486:0] r_llk_N0_0; always @(posedge lint_clk) r_llk_N0_0 <= {487{lint_in}}; assign llk_N0[486:0] = r_llk_N0_0;
    reg [0:0] r_llk_N0_974; always @(posedge lint_clk) r_llk_N0_974 <= {1{lint_in}}; assign llk_N0[974:974] = r_llk_N0_974;
    reg [486:0] r_llk_N1_0; always @(posedge lint_clk) r_llk_N1_0 <= {487{lint_in}}; assign llk_N1[486:0] = r_llk_N1_0;
    reg [0:0] r_llk_N1_974; always @(posedge lint_clk) r_llk_N1_974 <= {1{lint_in}}; assign llk_N1[974:974] = r_llk_N1_974;
    reg [486:0] r_llk_N2_0; always @(posedge lint_clk) r_llk_N2_0 <= {487{lint_in}}; assign llk_N2[486:0] = r_llk_N2_0;
    reg [0:0] r_llk_N2_974; always @(posedge lint_clk) r_llk_N2_974 <= {1{lint_in}}; assign llk_N2[974:974] = r_llk_N2_974;
    reg [486:0] r_llk_N3_0; always @(posedge lint_clk) r_llk_N3_0 <= {487{lint_in}}; assign llk_N3[486:0] = r_llk_N3_0;
    reg [0:0] r_llk_N3_974; always @(posedge lint_clk) r_llk_N3_974 <= {1{lint_in}}; assign llk_N3[974:974] = r_llk_N3_974;
    reg [486:0] r_llk_S0_0; always @(posedge lint_clk) r_llk_S0_0 <= {487{lint_in}}; assign llk_S0[486:0] = r_llk_S0_0;
    reg [0:0] r_llk_S0_974; always @(posedge lint_clk) r_llk_S0_974 <= {1{lint_in}}; assign llk_S0[974:974] = r_llk_S0_974;
    reg [486:0] r_llk_S1_0; always @(posedge lint_clk) r_llk_S1_0 <= {487{lint_in}}; assign llk_S1[486:0] = r_llk_S1_0;
    reg [0:0] r_llk_S1_974; always @(posedge lint_clk) r_llk_S1_974 <= {1{lint_in}}; assign llk_S1[974:974] = r_llk_S1_974;
    reg [486:0] r_llk_S2_0; always @(posedge lint_clk) r_llk_S2_0 <= {487{lint_in}}; assign llk_S2[486:0] = r_llk_S2_0;
    reg [0:0] r_llk_S2_974; always @(posedge lint_clk) r_llk_S2_974 <= {1{lint_in}}; assign llk_S2[974:974] = r_llk_S2_974;
    reg [486:0] r_llk_S3_0; always @(posedge lint_clk) r_llk_S3_0 <= {487{lint_in}}; assign llk_S3[486:0] = r_llk_S3_0;
    reg [0:0] r_llk_S3_974; always @(posedge lint_clk) r_llk_S3_974 <= {1{lint_in}}; assign llk_S3[974:974] = r_llk_S3_974;
    reg [486:0] r_llk_S4_0; always @(posedge lint_clk) r_llk_S4_0 <= {487{lint_in}}; assign llk_S4[486:0] = r_llk_S4_0;
    reg [0:0] r_llk_S4_974; always @(posedge lint_clk) r_llk_S4_974 <= {1{lint_in}}; assign llk_S4[974:974] = r_llk_S4_974;
    reg [0:0] r_pll_hbm_0; always @(posedge lint_clk) r_pll_hbm_0 <= {1{lint_in}}; assign pll_hbm[0:0] = r_pll_hbm_0;
    reg [0:0] r_pll_link_0; always @(posedge lint_clk) r_pll_link_0 <= {1{lint_in}}; assign pll_link[0:0] = r_pll_link_0;
    reg [0:0] r_pll_serial_0; always @(posedge lint_clk) r_pll_serial_0 <= {1{lint_in}}; assign pll_serial[0:0] = r_pll_serial_0;
    reg [0:0] r_pll_stream_0; always @(posedge lint_clk) r_pll_stream_0 <= {1{lint_in}}; assign pll_stream[0:0] = r_pll_stream_0;
    reg [0:0] r_por_hbm_0; always @(posedge lint_clk) r_por_hbm_0 <= {1{lint_in}}; assign por_hbm[0:0] = r_por_hbm_0;
    reg [0:0] r_por_link_0; always @(posedge lint_clk) r_por_link_0 <= {1{lint_in}}; assign por_link[0:0] = r_por_link_0;
    reg [0:0] r_por_serial_0; always @(posedge lint_clk) r_por_serial_0 <= {1{lint_in}}; assign por_serial[0:0] = r_por_serial_0;
    reg [0:0] r_por_stream_0; always @(posedge lint_clk) r_por_stream_0 <= {1{lint_in}}; assign por_stream[0:0] = r_por_stream_0;
    reg [32:0] r_t_cmdproc_0; always @(posedge lint_clk) r_t_cmdproc_0 <= {33{lint_in}}; assign t_cmdproc[32:0] = r_t_cmdproc_0;
    reg [579:0] r_t_su_NE_0; always @(posedge lint_clk) r_t_su_NE_0 <= {580{lint_in}}; assign t_su_NE[579:0] = r_t_su_NE_0;
    reg [579:0] r_t_su_NW_0; always @(posedge lint_clk) r_t_su_NW_0 <= {580{lint_in}}; assign t_su_NW[579:0] = r_t_su_NW_0;
    reg [579:0] r_t_su_SE_0; always @(posedge lint_clk) r_t_su_SE_0 <= {580{lint_in}}; assign t_su_SE[579:0] = r_t_su_SE_0;
    reg [579:0] r_t_su_SW_0; always @(posedge lint_clk) r_t_su_SW_0 <= {580{lint_in}}; assign t_su_SW[579:0] = r_t_su_SW_0;
endmodule

module hfd_gath_r10 (
    input wire [539:0] a,
    input wire [1082:0] a2,
    output wire [2164:0] b,
    input wire [0:0] ck,
    input wire [0:0] rst,
    input wire [269:0] t0,
    input wire [269:0] t1
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^a, ^a2, ^ck, ^rst, ^t0, ^t1};
    reg [2164:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2165{lint_in}}; assign b[2164:0] = r_b_0;
endmodule

module hfd_gath_r24 (
    input wire [539:0] a,
    output wire [1082:0] b,
    input wire [0:0] ck,
    input wire [0:0] rst,
    input wire [269:0] t0,
    input wire [269:0] t1
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^a, ^ck, ^rst, ^t0, ^t1};
    reg [1082:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1083{lint_in}}; assign b[1082:0] = r_b_0;
endmodule

module hfd_gath_r25 (
    input wire [539:0] a,
    input wire [1082:0] a2,
    output wire [2164:0] b,
    input wire [0:0] ck,
    input wire [0:0] rst,
    input wire [269:0] t0,
    input wire [269:0] t1
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^a, ^a2, ^ck, ^rst, ^t0, ^t1};
    reg [2164:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2165{lint_in}}; assign b[2164:0] = r_b_0;
endmodule

module hfd_gath_r8 (
    output wire [539:0] b,
    input wire [0:0] ck,
    input wire [0:0] rst,
    input wire [269:0] t0,
    input wire [269:0] t1
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^rst, ^t0, ^t1};
    reg [539:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {540{lint_in}}; assign b[539:0] = r_b_0;
endmodule

module hfd_gath_r9 (
    input wire [539:0] a,
    output wire [1082:0] b,
    input wire [0:0] ck,
    input wire [0:0] rst,
    input wire [269:0] t0,
    input wire [269:0] t1
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^a, ^ck, ^rst, ^t0, ^t1};
    reg [1082:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1083{lint_in}}; assign b[1082:0] = r_b_0;
endmodule

module hfd_hc (
    input wire [0:0] ck,
    input wire [1023:0] f_sfu,
    input wire [0:0] rst,
    output wire [1023:0] t_sfu
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^f_sfu, ^rst};
    reg [1023:0] r_t_sfu_0; always @(posedge lint_clk) r_t_sfu_0 <= {1024{lint_in}}; assign t_sfu[1023:0] = r_t_sfu_0;
endmodule

module hfd_host_slab (

);  // NO PORTS: reservation slab, no die net
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{1'b0};
endmodule

module hfd_index_q_b0 (
    input wire [528:0] a0,
    input wire [528:0] a0o,
    input wire [0:0] ck,
    input wire [1025:0] k,
    input wire [512:0] kout,
    input wire [0:0] rst
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^a0, ^a0o, ^ck, ^k, ^kout, ^rst};
endmodule

module hfd_index_q_b1 (
    input wire [528:0] a0i,
    input wire [528:0] a0o,
    input wire [0:0] ck,
    input wire [512:0] kin,
    input wire [512:0] kout,
    input wire [0:0] rst
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^a0i, ^a0o, ^ck, ^kin, ^kout, ^rst};
endmodule

module hfd_index_q_b2 (
    input wire [528:0] a0i,
    input wire [528:0] a1,
    input wire [528:0] a2i,
    input wire [528:0] a3i,
    input wire [0:0] ck,
    input wire [512:0] kin,
    input wire [512:0] kout,
    input wire [0:0] rst,
    output wire [1057:0] t_su
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^a0i, ^a1, ^a2i, ^a3i, ^ck, ^kin, ^kout, ^rst};
    reg [1057:0] r_t_su_0; always @(posedge lint_clk) r_t_su_0 <= {1058{lint_in}}; assign t_su[1057:0] = r_t_su_0;
endmodule

module hfd_index_q_b3 (
    input wire [528:0] a2,
    input wire [528:0] a2o,
    input wire [528:0] a3i,
    input wire [528:0] a3o,
    input wire [0:0] ck,
    input wire [512:0] kin,
    input wire [512:0] kout,
    input wire [0:0] rst
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^a2, ^a2o, ^a3i, ^a3o, ^ck, ^kin, ^kout, ^rst};
endmodule

module hfd_index_q_b4 (
    input wire [528:0] a3i,
    input wire [528:0] a3o,
    input wire [0:0] ck,
    input wire [512:0] kin,
    input wire [512:0] kout,
    input wire [0:0] rst
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^a3i, ^a3o, ^ck, ^kin, ^kout, ^rst};
endmodule

module hfd_index_q_b5 (
    input wire [528:0] a3,
    input wire [528:0] a3o,
    input wire [0:0] ck,
    input wire [512:0] kin,
    input wire [0:0] rst,
    output wire [511:0] t_vm
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^a3, ^a3o, ^ck, ^kin, ^rst};
    reg [511:0] r_t_vm_0; always @(posedge lint_clk) r_t_vm_0 <= {512{lint_in}}; assign t_vm[511:0] = r_t_vm_0;
endmodule

module hfd_loader (
    input wire [0:0] ck,
    inout wire [513:0] h,
    input wire [0:0] rst,
    output wire [340:0] t_cmdproc
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^h, ^rst};
    reg [255:0] r_h_0; always @(posedge lint_clk) r_h_0 <= {256{lint_in}}; assign h[255:0] = r_h_0;
    reg [0:0] r_h_512; always @(posedge lint_clk) r_h_512 <= {1{lint_in}}; assign h[512:512] = r_h_512;
    reg [340:0] r_t_cmdproc_0; always @(posedge lint_clk) r_t_cmdproc_0 <= {341{lint_in}}; assign t_cmdproc[340:0] = r_t_cmdproc_0;
endmodule

module hfd_mcast_r5 (
    input wire [2067:0] a,
    output wire [2067:0] b,
    input wire [0:0] ck,
    input wire [0:0] rst,
    output wire [2062:0] t0,
    output wire [2062:0] t1
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^a, ^ck, ^rst};
    reg [2067:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2068{lint_in}}; assign b[2067:0] = r_b_0;
    reg [2062:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {2063{lint_in}}; assign t0[2062:0] = r_t0_0;
    reg [2062:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {2063{lint_in}}; assign t1[2062:0] = r_t1_0;
endmodule

module hfd_mcast_r6 (
    input wire [2067:0] a,
    output wire [2067:0] b,
    input wire [0:0] ck,
    input wire [0:0] rst,
    output wire [2062:0] t0,
    output wire [2062:0] t1
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^a, ^ck, ^rst};
    reg [2067:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2068{lint_in}}; assign b[2067:0] = r_b_0;
    reg [2062:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {2063{lint_in}}; assign t0[2062:0] = r_t0_0;
    reg [2062:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {2063{lint_in}}; assign t1[2062:0] = r_t1_0;
endmodule

module hfd_mcast_r7 (
    input wire [2067:0] a,
    input wire [0:0] ck,
    input wire [0:0] rst,
    output wire [2062:0] t0,
    output wire [2062:0] t1
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^a, ^ck, ^rst};
    reg [2062:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {2063{lint_in}}; assign t0[2062:0] = r_t0_0;
    reg [2062:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {2063{lint_in}}; assign t1[2062:0] = r_t1_0;
endmodule

module hfd_meso_r1 (
    input wire [1101:0] a,
    output wire [1098:0] b,
    input wire [0:0] ck,
    input wire [0:0] rst
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^a, ^ck, ^rst};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_meso_r28 (
    inout wire [975:0] a,
    inout wire [973:0] b,
    input wire [0:0] ck,
    input wire [0:0] rst
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^a, ^b, ^ck, ^rst};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [0:0] r_a_975; always @(posedge lint_clk) r_a_975 <= {1{lint_in}}; assign a[975:975] = r_a_975;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_meso_r32 (
    inout wire [513:0] a,
    inout wire [511:0] b,
    input wire [0:0] ck,
    input wire [0:0] rst
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^a, ^b, ^ck, ^rst};
    reg [255:0] r_a_256; always @(posedge lint_clk) r_a_256 <= {256{lint_in}}; assign a[511:256] = r_a_256;
    reg [0:0] r_a_513; always @(posedge lint_clk) r_a_513 <= {1{lint_in}}; assign a[513:513] = r_a_513;
    reg [255:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {256{lint_in}}; assign b[255:0] = r_b_0;
endmodule

module hfd_meso_r35 (
    input wire [512:0] a,
    output wire [511:0] b,
    input wire [0:0] ck,
    input wire [0:0] rst
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^a, ^ck, ^rst};
    reg [511:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {512{lint_in}}; assign b[511:0] = r_b_0;
endmodule

module hfd_meso_r37 (
    input wire [512:0] a,
    output wire [511:0] b,
    input wire [0:0] ck,
    input wire [0:0] rst
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^a, ^ck, ^rst};
    reg [511:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {512{lint_in}}; assign b[511:0] = r_b_0;
endmodule

module hfd_quant (
    input wire [0:0] ck,
    input wire [1023:0] f_vm,
    input wire [0:0] rst,
    output wire [511:0] t_su_NE,
    output wire [511:0] t_su_NW,
    output wire [511:0] t_su_SE,
    output wire [511:0] t_su_SW
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^f_vm, ^rst};
    reg [511:0] r_t_su_NE_0; always @(posedge lint_clk) r_t_su_NE_0 <= {512{lint_in}}; assign t_su_NE[511:0] = r_t_su_NE_0;
    reg [511:0] r_t_su_NW_0; always @(posedge lint_clk) r_t_su_NW_0 <= {512{lint_in}}; assign t_su_NW[511:0] = r_t_su_NW_0;
    reg [511:0] r_t_su_SE_0; always @(posedge lint_clk) r_t_su_SE_0 <= {512{lint_in}}; assign t_su_SE[511:0] = r_t_su_SE_0;
    reg [511:0] r_t_su_SW_0; always @(posedge lint_clk) r_t_su_SW_0 <= {512{lint_in}}; assign t_su_SW[511:0] = r_t_su_SW_0;
endmodule

module hfd_router (
    input wire [0:0] ck,
    output wire [128:0] eNE,
    output wire [128:0] eNW,
    output wire [128:0] eSE,
    output wire [128:0] eSW,
    input wire [255:0] f_su_NE,
    input wire [255:0] f_su_NW,
    input wire [255:0] f_su_SE,
    input wire [255:0] f_su_SW,
    input wire [511:0] f_vm,
    input wire [0:0] rst,
    output wire [63:0] t_cmdproc
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^f_su_NE, ^f_su_NW, ^f_su_SE, ^f_su_SW, ^f_vm, ^rst};
    reg [128:0] r_eNE_0; always @(posedge lint_clk) r_eNE_0 <= {129{lint_in}}; assign eNE[128:0] = r_eNE_0;
    reg [128:0] r_eNW_0; always @(posedge lint_clk) r_eNW_0 <= {129{lint_in}}; assign eNW[128:0] = r_eNW_0;
    reg [128:0] r_eSE_0; always @(posedge lint_clk) r_eSE_0 <= {129{lint_in}}; assign eSE[128:0] = r_eSE_0;
    reg [128:0] r_eSW_0; always @(posedge lint_clk) r_eSW_0 <= {129{lint_in}}; assign eSW[128:0] = r_eSW_0;
    reg [63:0] r_t_cmdproc_0; always @(posedge lint_clk) r_t_cmdproc_0 <= {64{lint_in}}; assign t_cmdproc[63:0] = r_t_cmdproc_0;
endmodule

module hfd_serdes_slab (

);  // NO PORTS: reservation slab, no die net
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{1'b0};
endmodule

module hfd_sfu (
    input wire [0:0] ck,
    input wire [1023:0] f_hc,
    input wire [1023:0] f_su,
    input wire [0:0] rst,
    output wire [1023:0] t_hc,
    output wire [1023:0] t_su
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^f_hc, ^f_su, ^rst};
    reg [1023:0] r_t_hc_0; always @(posedge lint_clk) r_t_hc_0 <= {1024{lint_in}}; assign t_hc[1023:0] = r_t_hc_0;
    reg [1023:0] r_t_su_0; always @(posedge lint_clk) r_t_su_0 <= {1024{lint_in}}; assign t_su[1023:0] = r_t_su_0;
endmodule

module hfd_stn_r0 (
    input wire [1101:0] a,
    output wire [1101:0] b,
    input wire [0:0] rst
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^rst};
    reg [1101:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1102{lint_in}}; assign b[1101:0] = r_b_0;
endmodule

module hfd_stn_r11 (
    input wire [2164:0] a,
    output wire [2164:0] b,
    input wire [0:0] rst
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^rst};
    reg [2164:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2165{lint_in}}; assign b[2164:0] = r_b_0;
endmodule

module hfd_stn_r12 (
    inout wire [826:0] a,
    inout wire [826:0] b,
    input wire [0:0] rst
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b, ^rst};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [0:0] r_a_102; always @(posedge lint_clk) r_a_102 <= {1{lint_in}}; assign a[102:102] = r_a_102;
    reg [2:0] r_a_145; always @(posedge lint_clk) r_a_145 <= {3{lint_in}}; assign a[147:145] = r_a_145;
    reg [0:0] r_a_205; always @(posedge lint_clk) r_a_205 <= {1{lint_in}}; assign a[205:205] = r_a_205;
    reg [2:0] r_a_248; always @(posedge lint_clk) r_a_248 <= {3{lint_in}}; assign a[250:248] = r_a_248;
    reg [0:0] r_a_308; always @(posedge lint_clk) r_a_308 <= {1{lint_in}}; assign a[308:308] = r_a_308;
    reg [2:0] r_a_351; always @(posedge lint_clk) r_a_351 <= {3{lint_in}}; assign a[353:351] = r_a_351;
    reg [0:0] r_a_411; always @(posedge lint_clk) r_a_411 <= {1{lint_in}}; assign a[411:411] = r_a_411;
    reg [2:0] r_a_454; always @(posedge lint_clk) r_a_454 <= {3{lint_in}}; assign a[456:454] = r_a_454;
    reg [0:0] r_a_514; always @(posedge lint_clk) r_a_514 <= {1{lint_in}}; assign a[514:514] = r_a_514;
    reg [2:0] r_a_557; always @(posedge lint_clk) r_a_557 <= {3{lint_in}}; assign a[559:557] = r_a_557;
    reg [0:0] r_a_617; always @(posedge lint_clk) r_a_617 <= {1{lint_in}}; assign a[617:617] = r_a_617;
    reg [2:0] r_a_660; always @(posedge lint_clk) r_a_660 <= {3{lint_in}}; assign a[662:660] = r_a_660;
    reg [0:0] r_a_720; always @(posedge lint_clk) r_a_720 <= {1{lint_in}}; assign a[720:720] = r_a_720;
    reg [2:0] r_a_763; always @(posedge lint_clk) r_a_763 <= {3{lint_in}}; assign a[765:763] = r_a_763;
    reg [0:0] r_a_823; always @(posedge lint_clk) r_a_823 <= {1{lint_in}}; assign a[823:823] = r_a_823;
    reg [0:0] r_a_826; always @(posedge lint_clk) r_a_826 <= {1{lint_in}}; assign a[826:826] = r_a_826;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [56:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {57{lint_in}}; assign b[101:45] = r_b_45;
    reg [41:0] r_b_103; always @(posedge lint_clk) r_b_103 <= {42{lint_in}}; assign b[144:103] = r_b_103;
    reg [56:0] r_b_148; always @(posedge lint_clk) r_b_148 <= {57{lint_in}}; assign b[204:148] = r_b_148;
    reg [41:0] r_b_206; always @(posedge lint_clk) r_b_206 <= {42{lint_in}}; assign b[247:206] = r_b_206;
    reg [56:0] r_b_251; always @(posedge lint_clk) r_b_251 <= {57{lint_in}}; assign b[307:251] = r_b_251;
    reg [41:0] r_b_309; always @(posedge lint_clk) r_b_309 <= {42{lint_in}}; assign b[350:309] = r_b_309;
    reg [56:0] r_b_354; always @(posedge lint_clk) r_b_354 <= {57{lint_in}}; assign b[410:354] = r_b_354;
    reg [41:0] r_b_412; always @(posedge lint_clk) r_b_412 <= {42{lint_in}}; assign b[453:412] = r_b_412;
    reg [56:0] r_b_457; always @(posedge lint_clk) r_b_457 <= {57{lint_in}}; assign b[513:457] = r_b_457;
    reg [41:0] r_b_515; always @(posedge lint_clk) r_b_515 <= {42{lint_in}}; assign b[556:515] = r_b_515;
    reg [56:0] r_b_560; always @(posedge lint_clk) r_b_560 <= {57{lint_in}}; assign b[616:560] = r_b_560;
    reg [41:0] r_b_618; always @(posedge lint_clk) r_b_618 <= {42{lint_in}}; assign b[659:618] = r_b_618;
    reg [56:0] r_b_663; always @(posedge lint_clk) r_b_663 <= {57{lint_in}}; assign b[719:663] = r_b_663;
    reg [41:0] r_b_721; always @(posedge lint_clk) r_b_721 <= {42{lint_in}}; assign b[762:721] = r_b_721;
    reg [56:0] r_b_766; always @(posedge lint_clk) r_b_766 <= {57{lint_in}}; assign b[822:766] = r_b_766;
    reg [1:0] r_b_824; always @(posedge lint_clk) r_b_824 <= {2{lint_in}}; assign b[825:824] = r_b_824;
endmodule

module hfd_stn_r13 (
    inout wire [826:0] a,
    inout wire [826:0] b,
    input wire [0:0] rst
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b, ^rst};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [0:0] r_a_102; always @(posedge lint_clk) r_a_102 <= {1{lint_in}}; assign a[102:102] = r_a_102;
    reg [2:0] r_a_145; always @(posedge lint_clk) r_a_145 <= {3{lint_in}}; assign a[147:145] = r_a_145;
    reg [0:0] r_a_205; always @(posedge lint_clk) r_a_205 <= {1{lint_in}}; assign a[205:205] = r_a_205;
    reg [2:0] r_a_248; always @(posedge lint_clk) r_a_248 <= {3{lint_in}}; assign a[250:248] = r_a_248;
    reg [0:0] r_a_308; always @(posedge lint_clk) r_a_308 <= {1{lint_in}}; assign a[308:308] = r_a_308;
    reg [2:0] r_a_351; always @(posedge lint_clk) r_a_351 <= {3{lint_in}}; assign a[353:351] = r_a_351;
    reg [0:0] r_a_411; always @(posedge lint_clk) r_a_411 <= {1{lint_in}}; assign a[411:411] = r_a_411;
    reg [2:0] r_a_454; always @(posedge lint_clk) r_a_454 <= {3{lint_in}}; assign a[456:454] = r_a_454;
    reg [0:0] r_a_514; always @(posedge lint_clk) r_a_514 <= {1{lint_in}}; assign a[514:514] = r_a_514;
    reg [2:0] r_a_557; always @(posedge lint_clk) r_a_557 <= {3{lint_in}}; assign a[559:557] = r_a_557;
    reg [0:0] r_a_617; always @(posedge lint_clk) r_a_617 <= {1{lint_in}}; assign a[617:617] = r_a_617;
    reg [2:0] r_a_660; always @(posedge lint_clk) r_a_660 <= {3{lint_in}}; assign a[662:660] = r_a_660;
    reg [0:0] r_a_720; always @(posedge lint_clk) r_a_720 <= {1{lint_in}}; assign a[720:720] = r_a_720;
    reg [2:0] r_a_763; always @(posedge lint_clk) r_a_763 <= {3{lint_in}}; assign a[765:763] = r_a_763;
    reg [0:0] r_a_823; always @(posedge lint_clk) r_a_823 <= {1{lint_in}}; assign a[823:823] = r_a_823;
    reg [0:0] r_a_826; always @(posedge lint_clk) r_a_826 <= {1{lint_in}}; assign a[826:826] = r_a_826;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [56:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {57{lint_in}}; assign b[101:45] = r_b_45;
    reg [41:0] r_b_103; always @(posedge lint_clk) r_b_103 <= {42{lint_in}}; assign b[144:103] = r_b_103;
    reg [56:0] r_b_148; always @(posedge lint_clk) r_b_148 <= {57{lint_in}}; assign b[204:148] = r_b_148;
    reg [41:0] r_b_206; always @(posedge lint_clk) r_b_206 <= {42{lint_in}}; assign b[247:206] = r_b_206;
    reg [56:0] r_b_251; always @(posedge lint_clk) r_b_251 <= {57{lint_in}}; assign b[307:251] = r_b_251;
    reg [41:0] r_b_309; always @(posedge lint_clk) r_b_309 <= {42{lint_in}}; assign b[350:309] = r_b_309;
    reg [56:0] r_b_354; always @(posedge lint_clk) r_b_354 <= {57{lint_in}}; assign b[410:354] = r_b_354;
    reg [41:0] r_b_412; always @(posedge lint_clk) r_b_412 <= {42{lint_in}}; assign b[453:412] = r_b_412;
    reg [56:0] r_b_457; always @(posedge lint_clk) r_b_457 <= {57{lint_in}}; assign b[513:457] = r_b_457;
    reg [41:0] r_b_515; always @(posedge lint_clk) r_b_515 <= {42{lint_in}}; assign b[556:515] = r_b_515;
    reg [56:0] r_b_560; always @(posedge lint_clk) r_b_560 <= {57{lint_in}}; assign b[616:560] = r_b_560;
    reg [41:0] r_b_618; always @(posedge lint_clk) r_b_618 <= {42{lint_in}}; assign b[659:618] = r_b_618;
    reg [56:0] r_b_663; always @(posedge lint_clk) r_b_663 <= {57{lint_in}}; assign b[719:663] = r_b_663;
    reg [41:0] r_b_721; always @(posedge lint_clk) r_b_721 <= {42{lint_in}}; assign b[762:721] = r_b_721;
    reg [56:0] r_b_766; always @(posedge lint_clk) r_b_766 <= {57{lint_in}}; assign b[822:766] = r_b_766;
    reg [1:0] r_b_824; always @(posedge lint_clk) r_b_824 <= {2{lint_in}}; assign b[825:824] = r_b_824;
endmodule

module hfd_stn_r16 (
    input wire [128:0] a,
    output wire [128:0] b,
    input wire [0:0] rst
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^rst};
    reg [128:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {129{lint_in}}; assign b[128:0] = r_b_0;
endmodule

module hfd_stn_r17 (
    input wire [128:0] a,
    output wire [128:0] b,
    input wire [0:0] rst
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^rst};
    reg [128:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {129{lint_in}}; assign b[128:0] = r_b_0;
endmodule

module hfd_stn_r18 (
    input wire [1040:0] a,
    output wire [1040:0] b,
    input wire [0:0] rst
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^rst};
    reg [1040:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1041{lint_in}}; assign b[1040:0] = r_b_0;
endmodule

module hfd_stn_r19 (
    input wire [1040:0] a,
    output wire [1040:0] b,
    input wire [0:0] rst
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^rst};
    reg [1040:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1041{lint_in}}; assign b[1040:0] = r_b_0;
endmodule

module hfd_stn_r2 (
    inout wire [43:0] a,
    output wire [44:0] b,
    input wire [0:0] ck,
    input wire [0:0] rst
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^a, ^ck, ^rst};
    reg [0:0] r_a_43; always @(posedge lint_clk) r_a_43 <= {1{lint_in}}; assign a[43:43] = r_a_43;
    reg [44:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {45{lint_in}}; assign b[44:0] = r_b_0;
endmodule

module hfd_stn_r20 (
    input wire [1025:0] a,
    output wire [1025:0] b,
    input wire [0:0] rst
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^rst};
    reg [1025:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1026{lint_in}}; assign b[1025:0] = r_b_0;
endmodule

module hfd_stn_r21 (
    input wire [1025:0] a,
    output wire [1025:0] b,
    input wire [0:0] rst
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^rst};
    reg [1025:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1026{lint_in}}; assign b[1025:0] = r_b_0;
endmodule

module hfd_stn_r22 (
    input wire [581:0] a,
    output wire [581:0] b,
    input wire [0:0] rst
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^rst};
    reg [581:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {582{lint_in}}; assign b[581:0] = r_b_0;
endmodule

module hfd_stn_r23 (
    input wire [581:0] a,
    output wire [581:0] b,
    input wire [0:0] rst
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^rst};
    reg [581:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {582{lint_in}}; assign b[581:0] = r_b_0;
endmodule

module hfd_stn_r26 (
    input wire [2164:0] a,
    output wire [2164:0] b,
    input wire [0:0] rst
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^rst};
    reg [2164:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2165{lint_in}}; assign b[2164:0] = r_b_0;
endmodule

module hfd_stn_r27 (
    inout wire [975:0] a,
    inout wire [975:0] b,
    input wire [0:0] rst
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b, ^rst};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [0:0] r_a_975; always @(posedge lint_clk) r_a_975 <= {1{lint_in}}; assign a[975:975] = r_a_975;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
    reg [0:0] r_b_974; always @(posedge lint_clk) r_b_974 <= {1{lint_in}}; assign b[974:974] = r_b_974;
endmodule

module hfd_stn_r29 (
    inout wire [975:0] a,
    inout wire [975:0] b,
    input wire [0:0] rst
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b, ^rst};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [0:0] r_a_975; always @(posedge lint_clk) r_a_975 <= {1{lint_in}}; assign a[975:975] = r_a_975;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
    reg [0:0] r_b_974; always @(posedge lint_clk) r_b_974 <= {1{lint_in}}; assign b[974:974] = r_b_974;
endmodule

module hfd_stn_r3 (
    input wire [44:0] a,
    output wire [44:0] b,
    input wire [0:0] rst
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^rst};
    reg [44:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {45{lint_in}}; assign b[44:0] = r_b_0;
endmodule

module hfd_stn_r30 (
    inout wire [513:0] a,
    inout wire [513:0] b,
    input wire [0:0] rst
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b, ^rst};
    reg [255:0] r_a_256; always @(posedge lint_clk) r_a_256 <= {256{lint_in}}; assign a[511:256] = r_a_256;
    reg [0:0] r_a_513; always @(posedge lint_clk) r_a_513 <= {1{lint_in}}; assign a[513:513] = r_a_513;
    reg [255:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {256{lint_in}}; assign b[255:0] = r_b_0;
    reg [0:0] r_b_512; always @(posedge lint_clk) r_b_512 <= {1{lint_in}}; assign b[512:512] = r_b_512;
endmodule

module hfd_stn_r31 (
    inout wire [513:0] a,
    inout wire [513:0] b,
    input wire [0:0] rst
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b, ^rst};
    reg [255:0] r_a_256; always @(posedge lint_clk) r_a_256 <= {256{lint_in}}; assign a[511:256] = r_a_256;
    reg [0:0] r_a_513; always @(posedge lint_clk) r_a_513 <= {1{lint_in}}; assign a[513:513] = r_a_513;
    reg [255:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {256{lint_in}}; assign b[255:0] = r_b_0;
    reg [0:0] r_b_512; always @(posedge lint_clk) r_b_512 <= {1{lint_in}}; assign b[512:512] = r_b_512;
endmodule

module hfd_stn_r33 (
    input wire [511:0] a,
    output wire [512:0] b,
    input wire [0:0] ck,
    input wire [0:0] rst
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^a, ^ck, ^rst};
    reg [512:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {513{lint_in}}; assign b[512:0] = r_b_0;
endmodule

module hfd_stn_r34 (
    input wire [512:0] a,
    output wire [512:0] b,
    input wire [0:0] rst
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^rst};
    reg [512:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {513{lint_in}}; assign b[512:0] = r_b_0;
endmodule

module hfd_stn_r36 (
    input wire [512:0] a,
    output wire [512:0] b,
    input wire [0:0] rst
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^rst};
    reg [512:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {513{lint_in}}; assign b[512:0] = r_b_0;
endmodule

module hfd_stn_r4 (
    input wire [2067:0] a,
    output wire [2067:0] b,
    input wire [0:0] rst
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^rst};
    reg [2067:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2068{lint_in}}; assign b[2067:0] = r_b_0;
endmodule

module hfd_su (
    input wire [1057:0] a,
    input wire [0:0] ck,
    input wire [63:0] f_cmdproc,
    input wire [579:0] f_coll,
    input wire [511:0] f_quant,
    input wire [1023:0] f_sfu,
    input wire [1023:0] f_su_ew,
    input wire [1023:0] f_su_ns,
    input wire [2047:0] f_vm,
    input wire [2164:0] r,
    input wire [0:0] rst,
    output wire [1023:0] t_coll,
    output wire [255:0] t_router,
    output wire [1023:0] t_sfu,
    output wire [1023:0] t_su_ew,
    output wire [1023:0] t_su_ns,
    output wire [2047:0] t_vm
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^a, ^ck, ^f_cmdproc, ^f_coll, ^f_quant, ^f_sfu, ^f_su_ew, ^f_su_ns, ^f_vm, ^r, ^rst};
    reg [1023:0] r_t_coll_0; always @(posedge lint_clk) r_t_coll_0 <= {1024{lint_in}}; assign t_coll[1023:0] = r_t_coll_0;
    reg [255:0] r_t_router_0; always @(posedge lint_clk) r_t_router_0 <= {256{lint_in}}; assign t_router[255:0] = r_t_router_0;
    reg [1023:0] r_t_sfu_0; always @(posedge lint_clk) r_t_sfu_0 <= {1024{lint_in}}; assign t_sfu[1023:0] = r_t_sfu_0;
    reg [1023:0] r_t_su_ew_0; always @(posedge lint_clk) r_t_su_ew_0 <= {1024{lint_in}}; assign t_su_ew[1023:0] = r_t_su_ew_0;
    reg [1023:0] r_t_su_ns_0; always @(posedge lint_clk) r_t_su_ns_0 <= {1024{lint_in}}; assign t_su_ns[1023:0] = r_t_su_ns_0;
    reg [2047:0] r_t_vm_0; always @(posedge lint_clk) r_t_vm_0 <= {2048{lint_in}}; assign t_vm[2047:0] = r_t_vm_0;
endmodule

module hfd_su_full (
    input wire [0:0] ck,
    input wire [0:0] rst
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^rst};
endmodule

module hfd_su_red (
    input wire [0:0] ck,
    input wire [0:0] rst
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^rst};
endmodule

module hfd_svc_SE_s0 (
    input wire [0:0] ck,
    input wire [1174:0] ei,
    input wire [596:0] eo,
    output wire [1101:0] l0,
    output wire [1098:0] l1,
    inout wire [3625:0] phy,
    input wire [44:0] q0,
    inout wire [43:0] q1,
    input wire [0:0] rst
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^ei, ^eo, ^phy, ^q0, ^q1, ^rst};
    reg [1101:0] r_l0_0; always @(posedge lint_clk) r_l0_0 <= {1102{lint_in}}; assign l0[1101:0] = r_l0_0;
    reg [1098:0] r_l1_0; always @(posedge lint_clk) r_l1_0 <= {1099{lint_in}}; assign l1[1098:0] = r_l1_0;
    reg [0:0] r_phy_0; always @(posedge lint_clk) r_phy_0 <= {1{lint_in}}; assign phy[0:0] = r_phy_0;
    reg [339:0] r_phy_2; always @(posedge lint_clk) r_phy_2 <= {340{lint_in}}; assign phy[341:2] = r_phy_2;
    reg [0:0] r_phy_344; always @(posedge lint_clk) r_phy_344 <= {1{lint_in}}; assign phy[344:344] = r_phy_344;
    reg [0:0] r_phy_622; always @(posedge lint_clk) r_phy_622 <= {1{lint_in}}; assign phy[622:622] = r_phy_622;
    reg [39:0] r_phy_624; always @(posedge lint_clk) r_phy_624 <= {40{lint_in}}; assign phy[663:624] = r_phy_624;
    reg [0:0] r_phy_666; always @(posedge lint_clk) r_phy_666 <= {1{lint_in}}; assign phy[666:666] = r_phy_666;
    reg [0:0] r_phy_938; always @(posedge lint_clk) r_phy_938 <= {1{lint_in}}; assign phy[938:938] = r_phy_938;
    reg [339:0] r_phy_940; always @(posedge lint_clk) r_phy_940 <= {340{lint_in}}; assign phy[1279:940] = r_phy_940;
    reg [0:0] r_phy_1282; always @(posedge lint_clk) r_phy_1282 <= {1{lint_in}}; assign phy[1282:1282] = r_phy_1282;
    reg [0:0] r_phy_1562; always @(posedge lint_clk) r_phy_1562 <= {1{lint_in}}; assign phy[1562:1562] = r_phy_1562;
    reg [0:0] r_phy_1834; always @(posedge lint_clk) r_phy_1834 <= {1{lint_in}}; assign phy[1834:1834] = r_phy_1834;
    reg [339:0] r_phy_1836; always @(posedge lint_clk) r_phy_1836 <= {340{lint_in}}; assign phy[2175:1836] = r_phy_1836;
    reg [0:0] r_phy_2178; always @(posedge lint_clk) r_phy_2178 <= {1{lint_in}}; assign phy[2178:2178] = r_phy_2178;
    reg [0:0] r_phy_2458; always @(posedge lint_clk) r_phy_2458 <= {1{lint_in}}; assign phy[2458:2458] = r_phy_2458;
    reg [0:0] r_phy_2730; always @(posedge lint_clk) r_phy_2730 <= {1{lint_in}}; assign phy[2730:2730] = r_phy_2730;
    reg [339:0] r_phy_2732; always @(posedge lint_clk) r_phy_2732 <= {340{lint_in}}; assign phy[3071:2732] = r_phy_2732;
    reg [0:0] r_phy_3074; always @(posedge lint_clk) r_phy_3074 <= {1{lint_in}}; assign phy[3074:3074] = r_phy_3074;
    reg [0:0] r_phy_3354; always @(posedge lint_clk) r_phy_3354 <= {1{lint_in}}; assign phy[3354:3354] = r_phy_3354;
    reg [0:0] r_q1_43; always @(posedge lint_clk) r_q1_43 <= {1{lint_in}}; assign q1[43:43] = r_q1_43;
endmodule

module hfd_svc_SE_s1 (
    input wire [0:0] ck,
    input wire [938:0] ei,
    input wire [1412:0] eo,
    output wire [1101:0] l2,
    inout wire [4205:0] phy,
    input wire [44:0] q2,
    input wire [0:0] rst,
    input wire [596:0] wi,
    input wire [1174:0] wo
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^ei, ^eo, ^phy, ^q2, ^rst, ^wi, ^wo};
    reg [1101:0] r_l2_0; always @(posedge lint_clk) r_l2_0 <= {1102{lint_in}}; assign l2[1101:0] = r_l2_0;
    reg [0:0] r_phy_0; always @(posedge lint_clk) r_phy_0 <= {1{lint_in}}; assign phy[0:0] = r_phy_0;
    reg [339:0] r_phy_2; always @(posedge lint_clk) r_phy_2 <= {340{lint_in}}; assign phy[341:2] = r_phy_2;
    reg [0:0] r_phy_344; always @(posedge lint_clk) r_phy_344 <= {1{lint_in}}; assign phy[344:344] = r_phy_344;
    reg [0:0] r_phy_624; always @(posedge lint_clk) r_phy_624 <= {1{lint_in}}; assign phy[624:624] = r_phy_624;
    reg [0:0] r_phy_896; always @(posedge lint_clk) r_phy_896 <= {1{lint_in}}; assign phy[896:896] = r_phy_896;
    reg [339:0] r_phy_898; always @(posedge lint_clk) r_phy_898 <= {340{lint_in}}; assign phy[1237:898] = r_phy_898;
    reg [0:0] r_phy_1240; always @(posedge lint_clk) r_phy_1240 <= {1{lint_in}}; assign phy[1240:1240] = r_phy_1240;
    reg [0:0] r_phy_1520; always @(posedge lint_clk) r_phy_1520 <= {1{lint_in}}; assign phy[1520:1520] = r_phy_1520;
    reg [0:0] r_phy_1792; always @(posedge lint_clk) r_phy_1792 <= {1{lint_in}}; assign phy[1792:1792] = r_phy_1792;
    reg [339:0] r_phy_1794; always @(posedge lint_clk) r_phy_1794 <= {340{lint_in}}; assign phy[2133:1794] = r_phy_1794;
    reg [0:0] r_phy_2136; always @(posedge lint_clk) r_phy_2136 <= {1{lint_in}}; assign phy[2136:2136] = r_phy_2136;
    reg [0:0] r_phy_2416; always @(posedge lint_clk) r_phy_2416 <= {1{lint_in}}; assign phy[2416:2416] = r_phy_2416;
    reg [0:0] r_phy_2688; always @(posedge lint_clk) r_phy_2688 <= {1{lint_in}}; assign phy[2688:2688] = r_phy_2688;
    reg [339:0] r_phy_2690; always @(posedge lint_clk) r_phy_2690 <= {340{lint_in}}; assign phy[3029:2690] = r_phy_2690;
    reg [0:0] r_phy_3032; always @(posedge lint_clk) r_phy_3032 <= {1{lint_in}}; assign phy[3032:3032] = r_phy_3032;
    reg [0:0] r_phy_3312; always @(posedge lint_clk) r_phy_3312 <= {1{lint_in}}; assign phy[3312:3312] = r_phy_3312;
    reg [0:0] r_phy_3584; always @(posedge lint_clk) r_phy_3584 <= {1{lint_in}}; assign phy[3584:3584] = r_phy_3584;
    reg [339:0] r_phy_3586; always @(posedge lint_clk) r_phy_3586 <= {340{lint_in}}; assign phy[3925:3586] = r_phy_3586;
    reg [0:0] r_phy_3928; always @(posedge lint_clk) r_phy_3928 <= {1{lint_in}}; assign phy[3928:3928] = r_phy_3928;
endmodule

module hfd_svc_SE_s2 (
    input wire [0:0] ck,
    input wire [936:0] ei,
    input wire [1140:0] eo,
    output wire [1098:0] l3,
    inout wire [2487:0] phy,
    inout wire [43:0] q3,
    input wire [0:0] rst,
    input wire [1412:0] wi,
    input wire [938:0] wo
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^ei, ^eo, ^phy, ^q3, ^rst, ^wi, ^wo};
    reg [1098:0] r_l3_0; always @(posedge lint_clk) r_l3_0 <= {1099{lint_in}}; assign l3[1098:0] = r_l3_0;
    reg [0:0] r_phy_0; always @(posedge lint_clk) r_phy_0 <= {1{lint_in}}; assign phy[0:0] = r_phy_0;
    reg [339:0] r_phy_2; always @(posedge lint_clk) r_phy_2 <= {340{lint_in}}; assign phy[341:2] = r_phy_2;
    reg [0:0] r_phy_344; always @(posedge lint_clk) r_phy_344 <= {1{lint_in}}; assign phy[344:344] = r_phy_344;
    reg [0:0] r_phy_622; always @(posedge lint_clk) r_phy_622 <= {1{lint_in}}; assign phy[622:622] = r_phy_622;
    reg [339:0] r_phy_624; always @(posedge lint_clk) r_phy_624 <= {340{lint_in}}; assign phy[963:624] = r_phy_624;
    reg [0:0] r_phy_966; always @(posedge lint_clk) r_phy_966 <= {1{lint_in}}; assign phy[966:966] = r_phy_966;
    reg [0:0] r_phy_1244; always @(posedge lint_clk) r_phy_1244 <= {1{lint_in}}; assign phy[1244:1244] = r_phy_1244;
    reg [339:0] r_phy_1246; always @(posedge lint_clk) r_phy_1246 <= {340{lint_in}}; assign phy[1585:1246] = r_phy_1246;
    reg [0:0] r_phy_1588; always @(posedge lint_clk) r_phy_1588 <= {1{lint_in}}; assign phy[1588:1588] = r_phy_1588;
    reg [0:0] r_phy_1866; always @(posedge lint_clk) r_phy_1866 <= {1{lint_in}}; assign phy[1866:1866] = r_phy_1866;
    reg [339:0] r_phy_1868; always @(posedge lint_clk) r_phy_1868 <= {340{lint_in}}; assign phy[2207:1868] = r_phy_1868;
    reg [0:0] r_phy_2210; always @(posedge lint_clk) r_phy_2210 <= {1{lint_in}}; assign phy[2210:2210] = r_phy_2210;
    reg [0:0] r_q3_43; always @(posedge lint_clk) r_q3_43 <= {1{lint_in}}; assign q3[43:43] = r_q3_43;
endmodule

module hfd_svc_SE_s3 (
    input wire [0:0] ck,
    input wire [128:0] e,
    input wire [561:0] ei,
    input wire [919:0] eo,
    output wire [1025:0] ik,
    output wire [1040:0] kv,
    output wire [1101:0] l4,
    inout wire [3209:0] phy,
    input wire [44:0] q4,
    input wire [0:0] rst,
    input wire [1140:0] wi,
    input wire [936:0] wo
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^e, ^ei, ^eo, ^phy, ^q4, ^rst, ^wi, ^wo};
    reg [1025:0] r_ik_0; always @(posedge lint_clk) r_ik_0 <= {1026{lint_in}}; assign ik[1025:0] = r_ik_0;
    reg [1040:0] r_kv_0; always @(posedge lint_clk) r_kv_0 <= {1041{lint_in}}; assign kv[1040:0] = r_kv_0;
    reg [1101:0] r_l4_0; always @(posedge lint_clk) r_l4_0 <= {1102{lint_in}}; assign l4[1101:0] = r_l4_0;
    reg [0:0] r_phy_0; always @(posedge lint_clk) r_phy_0 <= {1{lint_in}}; assign phy[0:0] = r_phy_0;
    reg [339:0] r_phy_2; always @(posedge lint_clk) r_phy_2 <= {340{lint_in}}; assign phy[341:2] = r_phy_2;
    reg [0:0] r_phy_344; always @(posedge lint_clk) r_phy_344 <= {1{lint_in}}; assign phy[344:344] = r_phy_344;
    reg [0:0] r_phy_622; always @(posedge lint_clk) r_phy_622 <= {1{lint_in}}; assign phy[622:622] = r_phy_622;
    reg [339:0] r_phy_624; always @(posedge lint_clk) r_phy_624 <= {340{lint_in}}; assign phy[963:624] = r_phy_624;
    reg [0:0] r_phy_966; always @(posedge lint_clk) r_phy_966 <= {1{lint_in}}; assign phy[966:966] = r_phy_966;
    reg [0:0] r_phy_1244; always @(posedge lint_clk) r_phy_1244 <= {1{lint_in}}; assign phy[1244:1244] = r_phy_1244;
    reg [339:0] r_phy_1246; always @(posedge lint_clk) r_phy_1246 <= {340{lint_in}}; assign phy[1585:1246] = r_phy_1246;
    reg [0:0] r_phy_1588; always @(posedge lint_clk) r_phy_1588 <= {1{lint_in}}; assign phy[1588:1588] = r_phy_1588;
    reg [0:0] r_phy_1866; always @(posedge lint_clk) r_phy_1866 <= {1{lint_in}}; assign phy[1866:1866] = r_phy_1866;
    reg [339:0] r_phy_1868; always @(posedge lint_clk) r_phy_1868 <= {340{lint_in}}; assign phy[2207:1868] = r_phy_1868;
    reg [0:0] r_phy_2210; always @(posedge lint_clk) r_phy_2210 <= {1{lint_in}}; assign phy[2210:2210] = r_phy_2210;
    reg [1:0] r_phy_2488; always @(posedge lint_clk) r_phy_2488 <= {2{lint_in}}; assign phy[2489:2488] = r_phy_2488;
    reg [0:0] r_phy_2588; always @(posedge lint_clk) r_phy_2588 <= {1{lint_in}}; assign phy[2588:2588] = r_phy_2588;
    reg [339:0] r_phy_2590; always @(posedge lint_clk) r_phy_2590 <= {340{lint_in}}; assign phy[2929:2590] = r_phy_2590;
    reg [0:0] r_phy_2932; always @(posedge lint_clk) r_phy_2932 <= {1{lint_in}}; assign phy[2932:2932] = r_phy_2932;
endmodule

module hfd_svc_SE_s4 (
    input wire [0:0] ck,
    input wire [559:0] ei,
    input wire [647:0] eo,
    output wire [1098:0] l5,
    inout wire [2487:0] phy,
    inout wire [43:0] q5,
    input wire [0:0] rst,
    input wire [919:0] wi,
    input wire [561:0] wo
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^ei, ^eo, ^phy, ^q5, ^rst, ^wi, ^wo};
    reg [1098:0] r_l5_0; always @(posedge lint_clk) r_l5_0 <= {1099{lint_in}}; assign l5[1098:0] = r_l5_0;
    reg [0:0] r_phy_0; always @(posedge lint_clk) r_phy_0 <= {1{lint_in}}; assign phy[0:0] = r_phy_0;
    reg [339:0] r_phy_2; always @(posedge lint_clk) r_phy_2 <= {340{lint_in}}; assign phy[341:2] = r_phy_2;
    reg [0:0] r_phy_344; always @(posedge lint_clk) r_phy_344 <= {1{lint_in}}; assign phy[344:344] = r_phy_344;
    reg [0:0] r_phy_622; always @(posedge lint_clk) r_phy_622 <= {1{lint_in}}; assign phy[622:622] = r_phy_622;
    reg [339:0] r_phy_624; always @(posedge lint_clk) r_phy_624 <= {340{lint_in}}; assign phy[963:624] = r_phy_624;
    reg [0:0] r_phy_966; always @(posedge lint_clk) r_phy_966 <= {1{lint_in}}; assign phy[966:966] = r_phy_966;
    reg [0:0] r_phy_1244; always @(posedge lint_clk) r_phy_1244 <= {1{lint_in}}; assign phy[1244:1244] = r_phy_1244;
    reg [339:0] r_phy_1246; always @(posedge lint_clk) r_phy_1246 <= {340{lint_in}}; assign phy[1585:1246] = r_phy_1246;
    reg [0:0] r_phy_1588; always @(posedge lint_clk) r_phy_1588 <= {1{lint_in}}; assign phy[1588:1588] = r_phy_1588;
    reg [0:0] r_phy_1866; always @(posedge lint_clk) r_phy_1866 <= {1{lint_in}}; assign phy[1866:1866] = r_phy_1866;
    reg [339:0] r_phy_1868; always @(posedge lint_clk) r_phy_1868 <= {340{lint_in}}; assign phy[2207:1868] = r_phy_1868;
    reg [0:0] r_phy_2210; always @(posedge lint_clk) r_phy_2210 <= {1{lint_in}}; assign phy[2210:2210] = r_phy_2210;
    reg [0:0] r_q5_43; always @(posedge lint_clk) r_q5_43 <= {1{lint_in}}; assign q5[43:43] = r_q5_43;
endmodule

module hfd_svc_SE_s5 (
    input wire [0:0] ck,
    input wire [557:0] ei,
    input wire [375:0] eo,
    output wire [1101:0] l6,
    inout wire [2487:0] phy,
    input wire [44:0] q6,
    input wire [0:0] rst,
    input wire [647:0] wi,
    input wire [559:0] wo
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^ei, ^eo, ^phy, ^q6, ^rst, ^wi, ^wo};
    reg [1101:0] r_l6_0; always @(posedge lint_clk) r_l6_0 <= {1102{lint_in}}; assign l6[1101:0] = r_l6_0;
    reg [0:0] r_phy_0; always @(posedge lint_clk) r_phy_0 <= {1{lint_in}}; assign phy[0:0] = r_phy_0;
    reg [339:0] r_phy_2; always @(posedge lint_clk) r_phy_2 <= {340{lint_in}}; assign phy[341:2] = r_phy_2;
    reg [0:0] r_phy_344; always @(posedge lint_clk) r_phy_344 <= {1{lint_in}}; assign phy[344:344] = r_phy_344;
    reg [0:0] r_phy_622; always @(posedge lint_clk) r_phy_622 <= {1{lint_in}}; assign phy[622:622] = r_phy_622;
    reg [339:0] r_phy_624; always @(posedge lint_clk) r_phy_624 <= {340{lint_in}}; assign phy[963:624] = r_phy_624;
    reg [0:0] r_phy_966; always @(posedge lint_clk) r_phy_966 <= {1{lint_in}}; assign phy[966:966] = r_phy_966;
    reg [0:0] r_phy_1244; always @(posedge lint_clk) r_phy_1244 <= {1{lint_in}}; assign phy[1244:1244] = r_phy_1244;
    reg [339:0] r_phy_1246; always @(posedge lint_clk) r_phy_1246 <= {340{lint_in}}; assign phy[1585:1246] = r_phy_1246;
    reg [0:0] r_phy_1588; always @(posedge lint_clk) r_phy_1588 <= {1{lint_in}}; assign phy[1588:1588] = r_phy_1588;
    reg [0:0] r_phy_1866; always @(posedge lint_clk) r_phy_1866 <= {1{lint_in}}; assign phy[1866:1866] = r_phy_1866;
    reg [339:0] r_phy_1868; always @(posedge lint_clk) r_phy_1868 <= {340{lint_in}}; assign phy[2207:1868] = r_phy_1868;
    reg [0:0] r_phy_2210; always @(posedge lint_clk) r_phy_2210 <= {1{lint_in}}; assign phy[2210:2210] = r_phy_2210;
endmodule

module hfd_svc_SE_s6 (
    input wire [0:0] ck,
    input wire [53:0] ei,
    input wire [549:0] eo,
    inout wire [1865:0] phy,
    input wire [0:0] rst,
    input wire [375:0] wi,
    input wire [557:0] wo
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^ei, ^eo, ^phy, ^rst, ^wi, ^wo};
    reg [0:0] r_phy_0; always @(posedge lint_clk) r_phy_0 <= {1{lint_in}}; assign phy[0:0] = r_phy_0;
    reg [339:0] r_phy_2; always @(posedge lint_clk) r_phy_2 <= {340{lint_in}}; assign phy[341:2] = r_phy_2;
    reg [0:0] r_phy_344; always @(posedge lint_clk) r_phy_344 <= {1{lint_in}}; assign phy[344:344] = r_phy_344;
    reg [0:0] r_phy_622; always @(posedge lint_clk) r_phy_622 <= {1{lint_in}}; assign phy[622:622] = r_phy_622;
    reg [339:0] r_phy_624; always @(posedge lint_clk) r_phy_624 <= {340{lint_in}}; assign phy[963:624] = r_phy_624;
    reg [0:0] r_phy_966; always @(posedge lint_clk) r_phy_966 <= {1{lint_in}}; assign phy[966:966] = r_phy_966;
    reg [0:0] r_phy_1244; always @(posedge lint_clk) r_phy_1244 <= {1{lint_in}}; assign phy[1244:1244] = r_phy_1244;
    reg [339:0] r_phy_1246; always @(posedge lint_clk) r_phy_1246 <= {340{lint_in}}; assign phy[1585:1246] = r_phy_1246;
    reg [0:0] r_phy_1588; always @(posedge lint_clk) r_phy_1588 <= {1{lint_in}}; assign phy[1588:1588] = r_phy_1588;
endmodule

module hfd_svc_SE_s7 (
    input wire [0:0] ck,
    output wire [1098:0] l7,
    inout wire [1865:0] phy,
    inout wire [43:0] q7,
    input wire [0:0] rst,
    input wire [549:0] wi,
    input wire [53:0] wo
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^phy, ^q7, ^rst, ^wi, ^wo};
    reg [1098:0] r_l7_0; always @(posedge lint_clk) r_l7_0 <= {1099{lint_in}}; assign l7[1098:0] = r_l7_0;
    reg [0:0] r_phy_0; always @(posedge lint_clk) r_phy_0 <= {1{lint_in}}; assign phy[0:0] = r_phy_0;
    reg [339:0] r_phy_2; always @(posedge lint_clk) r_phy_2 <= {340{lint_in}}; assign phy[341:2] = r_phy_2;
    reg [0:0] r_phy_344; always @(posedge lint_clk) r_phy_344 <= {1{lint_in}}; assign phy[344:344] = r_phy_344;
    reg [0:0] r_phy_622; always @(posedge lint_clk) r_phy_622 <= {1{lint_in}}; assign phy[622:622] = r_phy_622;
    reg [339:0] r_phy_624; always @(posedge lint_clk) r_phy_624 <= {340{lint_in}}; assign phy[963:624] = r_phy_624;
    reg [0:0] r_phy_966; always @(posedge lint_clk) r_phy_966 <= {1{lint_in}}; assign phy[966:966] = r_phy_966;
    reg [0:0] r_phy_1244; always @(posedge lint_clk) r_phy_1244 <= {1{lint_in}}; assign phy[1244:1244] = r_phy_1244;
    reg [339:0] r_phy_1246; always @(posedge lint_clk) r_phy_1246 <= {340{lint_in}}; assign phy[1585:1246] = r_phy_1246;
    reg [0:0] r_phy_1588; always @(posedge lint_clk) r_phy_1588 <= {1{lint_in}}; assign phy[1588:1588] = r_phy_1588;
    reg [0:0] r_q7_43; always @(posedge lint_clk) r_q7_43 <= {1{lint_in}}; assign q7[43:43] = r_q7_43;
endmodule

module hfd_svc_SW_s0 (
    input wire [0:0] ck,
    input wire [1174:0] ei,
    input wire [596:0] eo,
    output wire [1101:0] l0,
    output wire [1098:0] l1,
    inout wire [3625:0] phy,
    input wire [44:0] q0,
    inout wire [43:0] q1,
    input wire [0:0] rst
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^ei, ^eo, ^phy, ^q0, ^q1, ^rst};
    reg [1101:0] r_l0_0; always @(posedge lint_clk) r_l0_0 <= {1102{lint_in}}; assign l0[1101:0] = r_l0_0;
    reg [1098:0] r_l1_0; always @(posedge lint_clk) r_l1_0 <= {1099{lint_in}}; assign l1[1098:0] = r_l1_0;
    reg [0:0] r_phy_0; always @(posedge lint_clk) r_phy_0 <= {1{lint_in}}; assign phy[0:0] = r_phy_0;
    reg [339:0] r_phy_2; always @(posedge lint_clk) r_phy_2 <= {340{lint_in}}; assign phy[341:2] = r_phy_2;
    reg [0:0] r_phy_344; always @(posedge lint_clk) r_phy_344 <= {1{lint_in}}; assign phy[344:344] = r_phy_344;
    reg [0:0] r_phy_622; always @(posedge lint_clk) r_phy_622 <= {1{lint_in}}; assign phy[622:622] = r_phy_622;
    reg [39:0] r_phy_624; always @(posedge lint_clk) r_phy_624 <= {40{lint_in}}; assign phy[663:624] = r_phy_624;
    reg [0:0] r_phy_666; always @(posedge lint_clk) r_phy_666 <= {1{lint_in}}; assign phy[666:666] = r_phy_666;
    reg [0:0] r_phy_938; always @(posedge lint_clk) r_phy_938 <= {1{lint_in}}; assign phy[938:938] = r_phy_938;
    reg [339:0] r_phy_940; always @(posedge lint_clk) r_phy_940 <= {340{lint_in}}; assign phy[1279:940] = r_phy_940;
    reg [0:0] r_phy_1282; always @(posedge lint_clk) r_phy_1282 <= {1{lint_in}}; assign phy[1282:1282] = r_phy_1282;
    reg [0:0] r_phy_1562; always @(posedge lint_clk) r_phy_1562 <= {1{lint_in}}; assign phy[1562:1562] = r_phy_1562;
    reg [0:0] r_phy_1834; always @(posedge lint_clk) r_phy_1834 <= {1{lint_in}}; assign phy[1834:1834] = r_phy_1834;
    reg [339:0] r_phy_1836; always @(posedge lint_clk) r_phy_1836 <= {340{lint_in}}; assign phy[2175:1836] = r_phy_1836;
    reg [0:0] r_phy_2178; always @(posedge lint_clk) r_phy_2178 <= {1{lint_in}}; assign phy[2178:2178] = r_phy_2178;
    reg [0:0] r_phy_2458; always @(posedge lint_clk) r_phy_2458 <= {1{lint_in}}; assign phy[2458:2458] = r_phy_2458;
    reg [0:0] r_phy_2730; always @(posedge lint_clk) r_phy_2730 <= {1{lint_in}}; assign phy[2730:2730] = r_phy_2730;
    reg [339:0] r_phy_2732; always @(posedge lint_clk) r_phy_2732 <= {340{lint_in}}; assign phy[3071:2732] = r_phy_2732;
    reg [0:0] r_phy_3074; always @(posedge lint_clk) r_phy_3074 <= {1{lint_in}}; assign phy[3074:3074] = r_phy_3074;
    reg [0:0] r_phy_3354; always @(posedge lint_clk) r_phy_3354 <= {1{lint_in}}; assign phy[3354:3354] = r_phy_3354;
    reg [0:0] r_q1_43; always @(posedge lint_clk) r_q1_43 <= {1{lint_in}}; assign q1[43:43] = r_q1_43;
endmodule

module hfd_svc_SW_s1 (
    input wire [0:0] ck,
    input wire [979:0] ei,
    input wire [1416:0] eo,
    output wire [1025:0] ik,
    output wire [1040:0] kv,
    output wire [1101:0] l2,
    inout wire [4205:0] phy,
    input wire [44:0] q2,
    input wire [0:0] rst,
    input wire [596:0] wi,
    input wire [1174:0] wo
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^ei, ^eo, ^phy, ^q2, ^rst, ^wi, ^wo};
    reg [1025:0] r_ik_0; always @(posedge lint_clk) r_ik_0 <= {1026{lint_in}}; assign ik[1025:0] = r_ik_0;
    reg [1040:0] r_kv_0; always @(posedge lint_clk) r_kv_0 <= {1041{lint_in}}; assign kv[1040:0] = r_kv_0;
    reg [1101:0] r_l2_0; always @(posedge lint_clk) r_l2_0 <= {1102{lint_in}}; assign l2[1101:0] = r_l2_0;
    reg [0:0] r_phy_0; always @(posedge lint_clk) r_phy_0 <= {1{lint_in}}; assign phy[0:0] = r_phy_0;
    reg [339:0] r_phy_2; always @(posedge lint_clk) r_phy_2 <= {340{lint_in}}; assign phy[341:2] = r_phy_2;
    reg [0:0] r_phy_344; always @(posedge lint_clk) r_phy_344 <= {1{lint_in}}; assign phy[344:344] = r_phy_344;
    reg [0:0] r_phy_624; always @(posedge lint_clk) r_phy_624 <= {1{lint_in}}; assign phy[624:624] = r_phy_624;
    reg [0:0] r_phy_896; always @(posedge lint_clk) r_phy_896 <= {1{lint_in}}; assign phy[896:896] = r_phy_896;
    reg [339:0] r_phy_898; always @(posedge lint_clk) r_phy_898 <= {340{lint_in}}; assign phy[1237:898] = r_phy_898;
    reg [0:0] r_phy_1240; always @(posedge lint_clk) r_phy_1240 <= {1{lint_in}}; assign phy[1240:1240] = r_phy_1240;
    reg [0:0] r_phy_1520; always @(posedge lint_clk) r_phy_1520 <= {1{lint_in}}; assign phy[1520:1520] = r_phy_1520;
    reg [0:0] r_phy_1792; always @(posedge lint_clk) r_phy_1792 <= {1{lint_in}}; assign phy[1792:1792] = r_phy_1792;
    reg [339:0] r_phy_1794; always @(posedge lint_clk) r_phy_1794 <= {340{lint_in}}; assign phy[2133:1794] = r_phy_1794;
    reg [0:0] r_phy_2136; always @(posedge lint_clk) r_phy_2136 <= {1{lint_in}}; assign phy[2136:2136] = r_phy_2136;
    reg [0:0] r_phy_2416; always @(posedge lint_clk) r_phy_2416 <= {1{lint_in}}; assign phy[2416:2416] = r_phy_2416;
    reg [0:0] r_phy_2688; always @(posedge lint_clk) r_phy_2688 <= {1{lint_in}}; assign phy[2688:2688] = r_phy_2688;
    reg [339:0] r_phy_2690; always @(posedge lint_clk) r_phy_2690 <= {340{lint_in}}; assign phy[3029:2690] = r_phy_2690;
    reg [0:0] r_phy_3032; always @(posedge lint_clk) r_phy_3032 <= {1{lint_in}}; assign phy[3032:3032] = r_phy_3032;
    reg [0:0] r_phy_3312; always @(posedge lint_clk) r_phy_3312 <= {1{lint_in}}; assign phy[3312:3312] = r_phy_3312;
    reg [0:0] r_phy_3584; always @(posedge lint_clk) r_phy_3584 <= {1{lint_in}}; assign phy[3584:3584] = r_phy_3584;
    reg [339:0] r_phy_3586; always @(posedge lint_clk) r_phy_3586 <= {340{lint_in}}; assign phy[3925:3586] = r_phy_3586;
    reg [0:0] r_phy_3928; always @(posedge lint_clk) r_phy_3928 <= {1{lint_in}}; assign phy[3928:3928] = r_phy_3928;
endmodule

module hfd_svc_SW_s2 (
    input wire [0:0] ck,
    input wire [1018:0] ei,
    input wire [1144:0] eo,
    output wire [1098:0] l3,
    inout wire [2487:0] phy,
    inout wire [43:0] q3,
    input wire [0:0] rst,
    input wire [1416:0] wi,
    input wire [979:0] wo
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^ei, ^eo, ^phy, ^q3, ^rst, ^wi, ^wo};
    reg [1098:0] r_l3_0; always @(posedge lint_clk) r_l3_0 <= {1099{lint_in}}; assign l3[1098:0] = r_l3_0;
    reg [0:0] r_phy_0; always @(posedge lint_clk) r_phy_0 <= {1{lint_in}}; assign phy[0:0] = r_phy_0;
    reg [339:0] r_phy_2; always @(posedge lint_clk) r_phy_2 <= {340{lint_in}}; assign phy[341:2] = r_phy_2;
    reg [0:0] r_phy_344; always @(posedge lint_clk) r_phy_344 <= {1{lint_in}}; assign phy[344:344] = r_phy_344;
    reg [0:0] r_phy_622; always @(posedge lint_clk) r_phy_622 <= {1{lint_in}}; assign phy[622:622] = r_phy_622;
    reg [339:0] r_phy_624; always @(posedge lint_clk) r_phy_624 <= {340{lint_in}}; assign phy[963:624] = r_phy_624;
    reg [0:0] r_phy_966; always @(posedge lint_clk) r_phy_966 <= {1{lint_in}}; assign phy[966:966] = r_phy_966;
    reg [0:0] r_phy_1244; always @(posedge lint_clk) r_phy_1244 <= {1{lint_in}}; assign phy[1244:1244] = r_phy_1244;
    reg [339:0] r_phy_1246; always @(posedge lint_clk) r_phy_1246 <= {340{lint_in}}; assign phy[1585:1246] = r_phy_1246;
    reg [0:0] r_phy_1588; always @(posedge lint_clk) r_phy_1588 <= {1{lint_in}}; assign phy[1588:1588] = r_phy_1588;
    reg [0:0] r_phy_1866; always @(posedge lint_clk) r_phy_1866 <= {1{lint_in}}; assign phy[1866:1866] = r_phy_1866;
    reg [339:0] r_phy_1868; always @(posedge lint_clk) r_phy_1868 <= {340{lint_in}}; assign phy[2207:1868] = r_phy_1868;
    reg [0:0] r_phy_2210; always @(posedge lint_clk) r_phy_2210 <= {1{lint_in}}; assign phy[2210:2210] = r_phy_2210;
    reg [0:0] r_q3_43; always @(posedge lint_clk) r_q3_43 <= {1{lint_in}}; assign q3[43:43] = r_q3_43;
endmodule

module hfd_svc_SW_s3 (
    input wire [0:0] ck,
    input wire [128:0] e,
    input wire [893:0] ei,
    input wire [866:0] eo,
    output wire [1101:0] l4,
    inout wire [2587:0] phy,
    input wire [44:0] q4,
    input wire [0:0] rst,
    input wire [1144:0] wi,
    input wire [1018:0] wo
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^e, ^ei, ^eo, ^phy, ^q4, ^rst, ^wi, ^wo};
    reg [1101:0] r_l4_0; always @(posedge lint_clk) r_l4_0 <= {1102{lint_in}}; assign l4[1101:0] = r_l4_0;
    reg [0:0] r_phy_0; always @(posedge lint_clk) r_phy_0 <= {1{lint_in}}; assign phy[0:0] = r_phy_0;
    reg [339:0] r_phy_2; always @(posedge lint_clk) r_phy_2 <= {340{lint_in}}; assign phy[341:2] = r_phy_2;
    reg [0:0] r_phy_344; always @(posedge lint_clk) r_phy_344 <= {1{lint_in}}; assign phy[344:344] = r_phy_344;
    reg [0:0] r_phy_622; always @(posedge lint_clk) r_phy_622 <= {1{lint_in}}; assign phy[622:622] = r_phy_622;
    reg [339:0] r_phy_624; always @(posedge lint_clk) r_phy_624 <= {340{lint_in}}; assign phy[963:624] = r_phy_624;
    reg [0:0] r_phy_966; always @(posedge lint_clk) r_phy_966 <= {1{lint_in}}; assign phy[966:966] = r_phy_966;
    reg [0:0] r_phy_1244; always @(posedge lint_clk) r_phy_1244 <= {1{lint_in}}; assign phy[1244:1244] = r_phy_1244;
    reg [339:0] r_phy_1246; always @(posedge lint_clk) r_phy_1246 <= {340{lint_in}}; assign phy[1585:1246] = r_phy_1246;
    reg [0:0] r_phy_1588; always @(posedge lint_clk) r_phy_1588 <= {1{lint_in}}; assign phy[1588:1588] = r_phy_1588;
    reg [0:0] r_phy_1866; always @(posedge lint_clk) r_phy_1866 <= {1{lint_in}}; assign phy[1866:1866] = r_phy_1866;
    reg [339:0] r_phy_1868; always @(posedge lint_clk) r_phy_1868 <= {340{lint_in}}; assign phy[2207:1868] = r_phy_1868;
    reg [0:0] r_phy_2210; always @(posedge lint_clk) r_phy_2210 <= {1{lint_in}}; assign phy[2210:2210] = r_phy_2210;
    reg [1:0] r_phy_2488; always @(posedge lint_clk) r_phy_2488 <= {2{lint_in}}; assign phy[2489:2488] = r_phy_2488;
endmodule

module hfd_svc_SW_s4 (
    input wire [0:0] ck,
    input wire [5:0] ei,
    input wire [815:0] eo,
    inout wire [1865:0] phy,
    input wire [0:0] rst,
    input wire [866:0] wi,
    input wire [893:0] wo
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^ei, ^eo, ^phy, ^rst, ^wi, ^wo};
    reg [0:0] r_phy_0; always @(posedge lint_clk) r_phy_0 <= {1{lint_in}}; assign phy[0:0] = r_phy_0;
    reg [339:0] r_phy_2; always @(posedge lint_clk) r_phy_2 <= {340{lint_in}}; assign phy[341:2] = r_phy_2;
    reg [0:0] r_phy_344; always @(posedge lint_clk) r_phy_344 <= {1{lint_in}}; assign phy[344:344] = r_phy_344;
    reg [0:0] r_phy_622; always @(posedge lint_clk) r_phy_622 <= {1{lint_in}}; assign phy[622:622] = r_phy_622;
    reg [339:0] r_phy_624; always @(posedge lint_clk) r_phy_624 <= {340{lint_in}}; assign phy[963:624] = r_phy_624;
    reg [0:0] r_phy_966; always @(posedge lint_clk) r_phy_966 <= {1{lint_in}}; assign phy[966:966] = r_phy_966;
    reg [0:0] r_phy_1244; always @(posedge lint_clk) r_phy_1244 <= {1{lint_in}}; assign phy[1244:1244] = r_phy_1244;
    reg [339:0] r_phy_1246; always @(posedge lint_clk) r_phy_1246 <= {340{lint_in}}; assign phy[1585:1246] = r_phy_1246;
    reg [0:0] r_phy_1588; always @(posedge lint_clk) r_phy_1588 <= {1{lint_in}}; assign phy[1588:1588] = r_phy_1588;
endmodule

module hfd_svc_SW_s5 (
    input wire [0:0] ck,
    input wire [3:0] ei,
    input wire [543:0] eo,
    output wire [1098:0] l5,
    inout wire [2487:0] phy,
    inout wire [43:0] q5,
    input wire [0:0] rst,
    input wire [815:0] wi,
    input wire [5:0] wo
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^ei, ^eo, ^phy, ^q5, ^rst, ^wi, ^wo};
    reg [1098:0] r_l5_0; always @(posedge lint_clk) r_l5_0 <= {1099{lint_in}}; assign l5[1098:0] = r_l5_0;
    reg [0:0] r_phy_0; always @(posedge lint_clk) r_phy_0 <= {1{lint_in}}; assign phy[0:0] = r_phy_0;
    reg [339:0] r_phy_2; always @(posedge lint_clk) r_phy_2 <= {340{lint_in}}; assign phy[341:2] = r_phy_2;
    reg [0:0] r_phy_344; always @(posedge lint_clk) r_phy_344 <= {1{lint_in}}; assign phy[344:344] = r_phy_344;
    reg [0:0] r_phy_622; always @(posedge lint_clk) r_phy_622 <= {1{lint_in}}; assign phy[622:622] = r_phy_622;
    reg [339:0] r_phy_624; always @(posedge lint_clk) r_phy_624 <= {340{lint_in}}; assign phy[963:624] = r_phy_624;
    reg [0:0] r_phy_966; always @(posedge lint_clk) r_phy_966 <= {1{lint_in}}; assign phy[966:966] = r_phy_966;
    reg [0:0] r_phy_1244; always @(posedge lint_clk) r_phy_1244 <= {1{lint_in}}; assign phy[1244:1244] = r_phy_1244;
    reg [339:0] r_phy_1246; always @(posedge lint_clk) r_phy_1246 <= {340{lint_in}}; assign phy[1585:1246] = r_phy_1246;
    reg [0:0] r_phy_1588; always @(posedge lint_clk) r_phy_1588 <= {1{lint_in}}; assign phy[1588:1588] = r_phy_1588;
    reg [0:0] r_phy_1866; always @(posedge lint_clk) r_phy_1866 <= {1{lint_in}}; assign phy[1866:1866] = r_phy_1866;
    reg [339:0] r_phy_1868; always @(posedge lint_clk) r_phy_1868 <= {340{lint_in}}; assign phy[2207:1868] = r_phy_1868;
    reg [0:0] r_phy_2210; always @(posedge lint_clk) r_phy_2210 <= {1{lint_in}}; assign phy[2210:2210] = r_phy_2210;
    reg [0:0] r_q5_43; always @(posedge lint_clk) r_q5_43 <= {1{lint_in}}; assign q5[43:43] = r_q5_43;
endmodule

module hfd_svc_SW_s6 (
    input wire [0:0] ck,
    input wire [1:0] ei,
    input wire [271:0] eo,
    output wire [1101:0] l6,
    inout wire [2487:0] phy,
    input wire [44:0] q6,
    input wire [0:0] rst,
    input wire [543:0] wi,
    input wire [3:0] wo
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^ei, ^eo, ^phy, ^q6, ^rst, ^wi, ^wo};
    reg [1101:0] r_l6_0; always @(posedge lint_clk) r_l6_0 <= {1102{lint_in}}; assign l6[1101:0] = r_l6_0;
    reg [0:0] r_phy_0; always @(posedge lint_clk) r_phy_0 <= {1{lint_in}}; assign phy[0:0] = r_phy_0;
    reg [339:0] r_phy_2; always @(posedge lint_clk) r_phy_2 <= {340{lint_in}}; assign phy[341:2] = r_phy_2;
    reg [0:0] r_phy_344; always @(posedge lint_clk) r_phy_344 <= {1{lint_in}}; assign phy[344:344] = r_phy_344;
    reg [0:0] r_phy_622; always @(posedge lint_clk) r_phy_622 <= {1{lint_in}}; assign phy[622:622] = r_phy_622;
    reg [339:0] r_phy_624; always @(posedge lint_clk) r_phy_624 <= {340{lint_in}}; assign phy[963:624] = r_phy_624;
    reg [0:0] r_phy_966; always @(posedge lint_clk) r_phy_966 <= {1{lint_in}}; assign phy[966:966] = r_phy_966;
    reg [0:0] r_phy_1244; always @(posedge lint_clk) r_phy_1244 <= {1{lint_in}}; assign phy[1244:1244] = r_phy_1244;
    reg [339:0] r_phy_1246; always @(posedge lint_clk) r_phy_1246 <= {340{lint_in}}; assign phy[1585:1246] = r_phy_1246;
    reg [0:0] r_phy_1588; always @(posedge lint_clk) r_phy_1588 <= {1{lint_in}}; assign phy[1588:1588] = r_phy_1588;
    reg [0:0] r_phy_1866; always @(posedge lint_clk) r_phy_1866 <= {1{lint_in}}; assign phy[1866:1866] = r_phy_1866;
    reg [339:0] r_phy_1868; always @(posedge lint_clk) r_phy_1868 <= {340{lint_in}}; assign phy[2207:1868] = r_phy_1868;
    reg [0:0] r_phy_2210; always @(posedge lint_clk) r_phy_2210 <= {1{lint_in}}; assign phy[2210:2210] = r_phy_2210;
endmodule

module hfd_svc_SW_s7 (
    input wire [0:0] ck,
    output wire [1098:0] l7,
    inout wire [2487:0] phy,
    inout wire [43:0] q7,
    input wire [0:0] rst,
    input wire [271:0] wi,
    input wire [1:0] wo
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^phy, ^q7, ^rst, ^wi, ^wo};
    reg [1098:0] r_l7_0; always @(posedge lint_clk) r_l7_0 <= {1099{lint_in}}; assign l7[1098:0] = r_l7_0;
    reg [0:0] r_phy_0; always @(posedge lint_clk) r_phy_0 <= {1{lint_in}}; assign phy[0:0] = r_phy_0;
    reg [339:0] r_phy_2; always @(posedge lint_clk) r_phy_2 <= {340{lint_in}}; assign phy[341:2] = r_phy_2;
    reg [0:0] r_phy_344; always @(posedge lint_clk) r_phy_344 <= {1{lint_in}}; assign phy[344:344] = r_phy_344;
    reg [0:0] r_phy_622; always @(posedge lint_clk) r_phy_622 <= {1{lint_in}}; assign phy[622:622] = r_phy_622;
    reg [339:0] r_phy_624; always @(posedge lint_clk) r_phy_624 <= {340{lint_in}}; assign phy[963:624] = r_phy_624;
    reg [0:0] r_phy_966; always @(posedge lint_clk) r_phy_966 <= {1{lint_in}}; assign phy[966:966] = r_phy_966;
    reg [0:0] r_phy_1244; always @(posedge lint_clk) r_phy_1244 <= {1{lint_in}}; assign phy[1244:1244] = r_phy_1244;
    reg [339:0] r_phy_1246; always @(posedge lint_clk) r_phy_1246 <= {340{lint_in}}; assign phy[1585:1246] = r_phy_1246;
    reg [0:0] r_phy_1588; always @(posedge lint_clk) r_phy_1588 <= {1{lint_in}}; assign phy[1588:1588] = r_phy_1588;
    reg [0:0] r_phy_1866; always @(posedge lint_clk) r_phy_1866 <= {1{lint_in}}; assign phy[1866:1866] = r_phy_1866;
    reg [339:0] r_phy_1868; always @(posedge lint_clk) r_phy_1868 <= {340{lint_in}}; assign phy[2207:1868] = r_phy_1868;
    reg [0:0] r_phy_2210; always @(posedge lint_clk) r_phy_2210 <= {1{lint_in}}; assign phy[2210:2210] = r_phy_2210;
    reg [0:0] r_q7_43; always @(posedge lint_clk) r_q7_43 <= {1{lint_in}}; assign q7[43:43] = r_q7_43;
endmodule

module hfd_vm_ne (
    input wire [0:0] ck,
    input wire [255:0] f_s_ctl,
    input wire [2255:0] f_s_row,
    input wire [2263:0] f_s_wr,
    input wire [2047:0] f_su_NE,
    input wire [255:0] f_w_ctl,
    input wire [2255:0] f_w_row,
    input wire [2263:0] f_w_wr,
    input wire [511:0] iNE,
    output wire [581:0] qNE,
    input wire [0:0] rst,
    output wire [255:0] t_s_ctl,
    output wire [2255:0] t_s_row,
    output wire [2263:0] t_s_wr,
    output wire [2047:0] t_su_NE,
    output wire [255:0] t_w_ctl,
    output wire [2255:0] t_w_row,
    output wire [2263:0] t_w_wr,
    output wire [2067:0] xNE
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^f_s_ctl, ^f_s_row, ^f_s_wr, ^f_su_NE, ^f_w_ctl, ^f_w_row, ^f_w_wr, ^iNE, ^rst};
    reg [581:0] r_qNE_0; always @(posedge lint_clk) r_qNE_0 <= {582{lint_in}}; assign qNE[581:0] = r_qNE_0;
    reg [255:0] r_t_s_ctl_0; always @(posedge lint_clk) r_t_s_ctl_0 <= {256{lint_in}}; assign t_s_ctl[255:0] = r_t_s_ctl_0;
    reg [2255:0] r_t_s_row_0; always @(posedge lint_clk) r_t_s_row_0 <= {2256{lint_in}}; assign t_s_row[2255:0] = r_t_s_row_0;
    reg [2263:0] r_t_s_wr_0; always @(posedge lint_clk) r_t_s_wr_0 <= {2264{lint_in}}; assign t_s_wr[2263:0] = r_t_s_wr_0;
    reg [2047:0] r_t_su_NE_0; always @(posedge lint_clk) r_t_su_NE_0 <= {2048{lint_in}}; assign t_su_NE[2047:0] = r_t_su_NE_0;
    reg [255:0] r_t_w_ctl_0; always @(posedge lint_clk) r_t_w_ctl_0 <= {256{lint_in}}; assign t_w_ctl[255:0] = r_t_w_ctl_0;
    reg [2255:0] r_t_w_row_0; always @(posedge lint_clk) r_t_w_row_0 <= {2256{lint_in}}; assign t_w_row[2255:0] = r_t_w_row_0;
    reg [2263:0] r_t_w_wr_0; always @(posedge lint_clk) r_t_w_wr_0 <= {2264{lint_in}}; assign t_w_wr[2263:0] = r_t_w_wr_0;
    reg [2067:0] r_xNE_0; always @(posedge lint_clk) r_xNE_0 <= {2068{lint_in}}; assign xNE[2067:0] = r_xNE_0;
endmodule

module hfd_vm_nw (
    input wire [0:0] ck,
    input wire [255:0] f_e_ctl,
    input wire [2255:0] f_e_row,
    input wire [2263:0] f_e_wr,
    input wire [255:0] f_s_ctl,
    input wire [2255:0] f_s_row,
    input wire [2263:0] f_s_wr,
    input wire [2047:0] f_su_NW,
    input wire [511:0] iNW,
    output wire [581:0] qNW,
    input wire [0:0] rst,
    output wire [255:0] t_e_ctl,
    output wire [2255:0] t_e_row,
    output wire [2263:0] t_e_wr,
    output wire [1023:0] t_quant,
    output wire [255:0] t_s_ctl,
    output wire [2255:0] t_s_row,
    output wire [2263:0] t_s_wr,
    output wire [2047:0] t_su_NW,
    output wire [2067:0] xNW
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^f_e_ctl, ^f_e_row, ^f_e_wr, ^f_s_ctl, ^f_s_row, ^f_s_wr, ^f_su_NW, ^iNW, ^rst};
    reg [581:0] r_qNW_0; always @(posedge lint_clk) r_qNW_0 <= {582{lint_in}}; assign qNW[581:0] = r_qNW_0;
    reg [255:0] r_t_e_ctl_0; always @(posedge lint_clk) r_t_e_ctl_0 <= {256{lint_in}}; assign t_e_ctl[255:0] = r_t_e_ctl_0;
    reg [2255:0] r_t_e_row_0; always @(posedge lint_clk) r_t_e_row_0 <= {2256{lint_in}}; assign t_e_row[2255:0] = r_t_e_row_0;
    reg [2263:0] r_t_e_wr_0; always @(posedge lint_clk) r_t_e_wr_0 <= {2264{lint_in}}; assign t_e_wr[2263:0] = r_t_e_wr_0;
    reg [1023:0] r_t_quant_0; always @(posedge lint_clk) r_t_quant_0 <= {1024{lint_in}}; assign t_quant[1023:0] = r_t_quant_0;
    reg [255:0] r_t_s_ctl_0; always @(posedge lint_clk) r_t_s_ctl_0 <= {256{lint_in}}; assign t_s_ctl[255:0] = r_t_s_ctl_0;
    reg [2255:0] r_t_s_row_0; always @(posedge lint_clk) r_t_s_row_0 <= {2256{lint_in}}; assign t_s_row[2255:0] = r_t_s_row_0;
    reg [2263:0] r_t_s_wr_0; always @(posedge lint_clk) r_t_s_wr_0 <= {2264{lint_in}}; assign t_s_wr[2263:0] = r_t_s_wr_0;
    reg [2047:0] r_t_su_NW_0; always @(posedge lint_clk) r_t_su_NW_0 <= {2048{lint_in}}; assign t_su_NW[2047:0] = r_t_su_NW_0;
    reg [2067:0] r_xNW_0; always @(posedge lint_clk) r_xNW_0 <= {2068{lint_in}}; assign xNW[2067:0] = r_xNW_0;
endmodule

module hfd_vm_se (
    input wire [0:0] ck,
    input wire [255:0] f_n_ctl,
    input wire [2255:0] f_n_row,
    input wire [2263:0] f_n_wr,
    input wire [2047:0] f_su_SE,
    input wire [255:0] f_w_ctl,
    input wire [2255:0] f_w_row,
    input wire [2263:0] f_w_wr,
    input wire [511:0] iSE,
    output wire [581:0] qSE,
    input wire [0:0] rst,
    output wire [255:0] t_n_ctl,
    output wire [2255:0] t_n_row,
    output wire [2263:0] t_n_wr,
    output wire [2047:0] t_su_SE,
    output wire [255:0] t_w_ctl,
    output wire [2255:0] t_w_row,
    output wire [2263:0] t_w_wr,
    output wire [2067:0] xSE
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^f_n_ctl, ^f_n_row, ^f_n_wr, ^f_su_SE, ^f_w_ctl, ^f_w_row, ^f_w_wr, ^iSE, ^rst};
    reg [581:0] r_qSE_0; always @(posedge lint_clk) r_qSE_0 <= {582{lint_in}}; assign qSE[581:0] = r_qSE_0;
    reg [255:0] r_t_n_ctl_0; always @(posedge lint_clk) r_t_n_ctl_0 <= {256{lint_in}}; assign t_n_ctl[255:0] = r_t_n_ctl_0;
    reg [2255:0] r_t_n_row_0; always @(posedge lint_clk) r_t_n_row_0 <= {2256{lint_in}}; assign t_n_row[2255:0] = r_t_n_row_0;
    reg [2263:0] r_t_n_wr_0; always @(posedge lint_clk) r_t_n_wr_0 <= {2264{lint_in}}; assign t_n_wr[2263:0] = r_t_n_wr_0;
    reg [2047:0] r_t_su_SE_0; always @(posedge lint_clk) r_t_su_SE_0 <= {2048{lint_in}}; assign t_su_SE[2047:0] = r_t_su_SE_0;
    reg [255:0] r_t_w_ctl_0; always @(posedge lint_clk) r_t_w_ctl_0 <= {256{lint_in}}; assign t_w_ctl[255:0] = r_t_w_ctl_0;
    reg [2255:0] r_t_w_row_0; always @(posedge lint_clk) r_t_w_row_0 <= {2256{lint_in}}; assign t_w_row[2255:0] = r_t_w_row_0;
    reg [2263:0] r_t_w_wr_0; always @(posedge lint_clk) r_t_w_wr_0 <= {2264{lint_in}}; assign t_w_wr[2263:0] = r_t_w_wr_0;
    reg [2067:0] r_xSE_0; always @(posedge lint_clk) r_xSE_0 <= {2068{lint_in}}; assign xSE[2067:0] = r_xSE_0;
endmodule

module hfd_vm_sw (
    input wire [0:0] ck,
    input wire [255:0] f_e_ctl,
    input wire [2255:0] f_e_row,
    input wire [2263:0] f_e_wr,
    input wire [255:0] f_n_ctl,
    input wire [2255:0] f_n_row,
    input wire [2263:0] f_n_wr,
    input wire [2047:0] f_su_SW,
    input wire [511:0] iSW,
    output wire [581:0] qSW,
    input wire [0:0] rst,
    output wire [255:0] t_e_ctl,
    output wire [2255:0] t_e_row,
    output wire [2263:0] t_e_wr,
    output wire [255:0] t_n_ctl,
    output wire [2255:0] t_n_row,
    output wire [2263:0] t_n_wr,
    output wire [511:0] t_router,
    output wire [2047:0] t_su_SW,
    output wire [2067:0] xSW
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^f_e_ctl, ^f_e_row, ^f_e_wr, ^f_n_ctl, ^f_n_row, ^f_n_wr, ^f_su_SW, ^iSW, ^rst};
    reg [581:0] r_qSW_0; always @(posedge lint_clk) r_qSW_0 <= {582{lint_in}}; assign qSW[581:0] = r_qSW_0;
    reg [255:0] r_t_e_ctl_0; always @(posedge lint_clk) r_t_e_ctl_0 <= {256{lint_in}}; assign t_e_ctl[255:0] = r_t_e_ctl_0;
    reg [2255:0] r_t_e_row_0; always @(posedge lint_clk) r_t_e_row_0 <= {2256{lint_in}}; assign t_e_row[2255:0] = r_t_e_row_0;
    reg [2263:0] r_t_e_wr_0; always @(posedge lint_clk) r_t_e_wr_0 <= {2264{lint_in}}; assign t_e_wr[2263:0] = r_t_e_wr_0;
    reg [255:0] r_t_n_ctl_0; always @(posedge lint_clk) r_t_n_ctl_0 <= {256{lint_in}}; assign t_n_ctl[255:0] = r_t_n_ctl_0;
    reg [2255:0] r_t_n_row_0; always @(posedge lint_clk) r_t_n_row_0 <= {2256{lint_in}}; assign t_n_row[2255:0] = r_t_n_row_0;
    reg [2263:0] r_t_n_wr_0; always @(posedge lint_clk) r_t_n_wr_0 <= {2264{lint_in}}; assign t_n_wr[2263:0] = r_t_n_wr_0;
    reg [511:0] r_t_router_0; always @(posedge lint_clk) r_t_router_0 <= {512{lint_in}}; assign t_router[511:0] = r_t_router_0;
    reg [2047:0] r_t_su_SW_0; always @(posedge lint_clk) r_t_su_SW_0 <= {2048{lint_in}}; assign t_su_SW[2047:0] = r_t_su_SW_0;
    reg [2067:0] r_xSW_0; always @(posedge lint_clk) r_xSW_0 <= {2068{lint_in}}; assign xSW[2067:0] = r_xSW_0;
endmodule
