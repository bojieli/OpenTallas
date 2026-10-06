// die_top_lint: port-identical REGISTERED STUBS of every placeholder master (generated abstract ports and
// widths; directions from the DIRECTION MODEL in tools/die_top_lint.py; x = conflicting across instances
// -> inout).  Outputs come from flops on the stub clock (ck[0] when the abstract has a clock port).

module hfd_attn_tile (
    input wire [0:0] ck,
    input wire [511:0] i,
    input wire [1023:0] k,
    input wire [1023:0] kd,
    output wire [1023:0] ku,
    output wire [511:0] o
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^i, ^k, ^kd};
    reg [1023:0] r_ku_0; always @(posedge lint_clk) r_ku_0 <= {1024{lint_in}}; assign ku[1023:0] = r_ku_0;
    reg [511:0] r_o_0; always @(posedge lint_clk) r_o_0 <= {512{lint_in}}; assign o[511:0] = r_o_0;
endmodule

module hfd_barrier (
    input wire [0:0] ck,
    output wire [63:0] t_cmdproc
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck};
    reg [63:0] r_t_cmdproc_0; always @(posedge lint_clk) r_t_cmdproc_0 <= {64{lint_in}}; assign t_cmdproc[63:0] = r_t_cmdproc_0;
endmodule

module hfd_cdist_112 (
    inout wire [359:0] a,
    inout wire [179:0] b,
    inout wire [44:0] t0,
    inout wire [44:0] t1,
    inout wire [44:0] t2,
    inout wire [44:0] t3
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b, ^t0, ^t1, ^t2, ^t3};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [2:0] r_a_222; always @(posedge lint_clk) r_a_222 <= {3{lint_in}}; assign a[224:222] = r_a_222;
    reg [2:0] r_a_267; always @(posedge lint_clk) r_a_267 <= {3{lint_in}}; assign a[269:267] = r_a_267;
    reg [2:0] r_a_312; always @(posedge lint_clk) r_a_312 <= {3{lint_in}}; assign a[314:312] = r_a_312;
    reg [2:0] r_a_357; always @(posedge lint_clk) r_a_357 <= {3{lint_in}}; assign a[359:357] = r_a_357;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [41:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {42{lint_in}}; assign b[86:45] = r_b_45;
    reg [41:0] r_b_90; always @(posedge lint_clk) r_b_90 <= {42{lint_in}}; assign b[131:90] = r_b_90;
    reg [41:0] r_b_135; always @(posedge lint_clk) r_b_135 <= {42{lint_in}}; assign b[176:135] = r_b_135;
    reg [41:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {42{lint_in}}; assign t0[41:0] = r_t0_0;
    reg [41:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {42{lint_in}}; assign t1[41:0] = r_t1_0;
    reg [41:0] r_t2_0; always @(posedge lint_clk) r_t2_0 <= {42{lint_in}}; assign t2[41:0] = r_t2_0;
    reg [41:0] r_t3_0; always @(posedge lint_clk) r_t3_0 <= {42{lint_in}}; assign t3[41:0] = r_t3_0;
endmodule

module hfd_cdist_113 (
    inout wire [179:0] a,
    inout wire [44:0] t0,
    inout wire [44:0] t1,
    inout wire [44:0] t2,
    inout wire [44:0] t3
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^t0, ^t1, ^t2, ^t3};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [41:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {42{lint_in}}; assign t0[41:0] = r_t0_0;
    reg [41:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {42{lint_in}}; assign t1[41:0] = r_t1_0;
    reg [41:0] r_t2_0; always @(posedge lint_clk) r_t2_0 <= {42{lint_in}}; assign t2[41:0] = r_t2_0;
    reg [41:0] r_t3_0; always @(posedge lint_clk) r_t3_0 <= {42{lint_in}}; assign t3[41:0] = r_t3_0;
endmodule

module hfd_cdist_158 (
    inout wire [359:0] a,
    inout wire [179:0] b,
    inout wire [44:0] t0,
    inout wire [44:0] t1,
    inout wire [44:0] t2,
    inout wire [44:0] t3
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b, ^t0, ^t1, ^t2, ^t3};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [2:0] r_a_222; always @(posedge lint_clk) r_a_222 <= {3{lint_in}}; assign a[224:222] = r_a_222;
    reg [2:0] r_a_267; always @(posedge lint_clk) r_a_267 <= {3{lint_in}}; assign a[269:267] = r_a_267;
    reg [2:0] r_a_312; always @(posedge lint_clk) r_a_312 <= {3{lint_in}}; assign a[314:312] = r_a_312;
    reg [2:0] r_a_357; always @(posedge lint_clk) r_a_357 <= {3{lint_in}}; assign a[359:357] = r_a_357;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [41:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {42{lint_in}}; assign b[86:45] = r_b_45;
    reg [41:0] r_b_90; always @(posedge lint_clk) r_b_90 <= {42{lint_in}}; assign b[131:90] = r_b_90;
    reg [41:0] r_b_135; always @(posedge lint_clk) r_b_135 <= {42{lint_in}}; assign b[176:135] = r_b_135;
    reg [41:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {42{lint_in}}; assign t0[41:0] = r_t0_0;
    reg [41:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {42{lint_in}}; assign t1[41:0] = r_t1_0;
    reg [41:0] r_t2_0; always @(posedge lint_clk) r_t2_0 <= {42{lint_in}}; assign t2[41:0] = r_t2_0;
    reg [41:0] r_t3_0; always @(posedge lint_clk) r_t3_0 <= {42{lint_in}}; assign t3[41:0] = r_t3_0;
endmodule

module hfd_cdist_159 (
    inout wire [179:0] a,
    inout wire [44:0] t0,
    inout wire [44:0] t1,
    inout wire [44:0] t2,
    inout wire [44:0] t3
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^t0, ^t1, ^t2, ^t3};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [41:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {42{lint_in}}; assign t0[41:0] = r_t0_0;
    reg [41:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {42{lint_in}}; assign t1[41:0] = r_t1_0;
    reg [41:0] r_t2_0; always @(posedge lint_clk) r_t2_0 <= {42{lint_in}}; assign t2[41:0] = r_t2_0;
    reg [41:0] r_t3_0; always @(posedge lint_clk) r_t3_0 <= {42{lint_in}}; assign t3[41:0] = r_t3_0;
endmodule

module hfd_cdist_28 (
    inout wire [359:0] a,
    inout wire [179:0] b,
    inout wire [44:0] t0,
    inout wire [44:0] t1,
    inout wire [44:0] t2,
    inout wire [44:0] t3
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b, ^t0, ^t1, ^t2, ^t3};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [2:0] r_a_222; always @(posedge lint_clk) r_a_222 <= {3{lint_in}}; assign a[224:222] = r_a_222;
    reg [2:0] r_a_267; always @(posedge lint_clk) r_a_267 <= {3{lint_in}}; assign a[269:267] = r_a_267;
    reg [2:0] r_a_312; always @(posedge lint_clk) r_a_312 <= {3{lint_in}}; assign a[314:312] = r_a_312;
    reg [2:0] r_a_357; always @(posedge lint_clk) r_a_357 <= {3{lint_in}}; assign a[359:357] = r_a_357;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [41:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {42{lint_in}}; assign b[86:45] = r_b_45;
    reg [41:0] r_b_90; always @(posedge lint_clk) r_b_90 <= {42{lint_in}}; assign b[131:90] = r_b_90;
    reg [41:0] r_b_135; always @(posedge lint_clk) r_b_135 <= {42{lint_in}}; assign b[176:135] = r_b_135;
    reg [41:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {42{lint_in}}; assign t0[41:0] = r_t0_0;
    reg [41:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {42{lint_in}}; assign t1[41:0] = r_t1_0;
    reg [41:0] r_t2_0; always @(posedge lint_clk) r_t2_0 <= {42{lint_in}}; assign t2[41:0] = r_t2_0;
    reg [41:0] r_t3_0; always @(posedge lint_clk) r_t3_0 <= {42{lint_in}}; assign t3[41:0] = r_t3_0;
endmodule

module hfd_cdist_29 (
    inout wire [179:0] a,
    inout wire [44:0] t0,
    inout wire [44:0] t1,
    inout wire [44:0] t2,
    inout wire [44:0] t3
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^t0, ^t1, ^t2, ^t3};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [41:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {42{lint_in}}; assign t0[41:0] = r_t0_0;
    reg [41:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {42{lint_in}}; assign t1[41:0] = r_t1_0;
    reg [41:0] r_t2_0; always @(posedge lint_clk) r_t2_0 <= {42{lint_in}}; assign t2[41:0] = r_t2_0;
    reg [41:0] r_t3_0; always @(posedge lint_clk) r_t3_0 <= {42{lint_in}}; assign t3[41:0] = r_t3_0;
endmodule

module hfd_cdist_71 (
    inout wire [359:0] a,
    inout wire [179:0] b,
    inout wire [44:0] t0,
    inout wire [44:0] t1,
    inout wire [44:0] t2,
    inout wire [44:0] t3
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b, ^t0, ^t1, ^t2, ^t3};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [2:0] r_a_222; always @(posedge lint_clk) r_a_222 <= {3{lint_in}}; assign a[224:222] = r_a_222;
    reg [2:0] r_a_267; always @(posedge lint_clk) r_a_267 <= {3{lint_in}}; assign a[269:267] = r_a_267;
    reg [2:0] r_a_312; always @(posedge lint_clk) r_a_312 <= {3{lint_in}}; assign a[314:312] = r_a_312;
    reg [2:0] r_a_357; always @(posedge lint_clk) r_a_357 <= {3{lint_in}}; assign a[359:357] = r_a_357;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [41:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {42{lint_in}}; assign b[86:45] = r_b_45;
    reg [41:0] r_b_90; always @(posedge lint_clk) r_b_90 <= {42{lint_in}}; assign b[131:90] = r_b_90;
    reg [41:0] r_b_135; always @(posedge lint_clk) r_b_135 <= {42{lint_in}}; assign b[176:135] = r_b_135;
    reg [41:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {42{lint_in}}; assign t0[41:0] = r_t0_0;
    reg [41:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {42{lint_in}}; assign t1[41:0] = r_t1_0;
    reg [41:0] r_t2_0; always @(posedge lint_clk) r_t2_0 <= {42{lint_in}}; assign t2[41:0] = r_t2_0;
    reg [41:0] r_t3_0; always @(posedge lint_clk) r_t3_0 <= {42{lint_in}}; assign t3[41:0] = r_t3_0;
endmodule

module hfd_cdist_72 (
    inout wire [179:0] a,
    inout wire [44:0] t0,
    inout wire [44:0] t1,
    inout wire [44:0] t2,
    inout wire [44:0] t3
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^t0, ^t1, ^t2, ^t3};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [41:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {42{lint_in}}; assign t0[41:0] = r_t0_0;
    reg [41:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {42{lint_in}}; assign t1[41:0] = r_t1_0;
    reg [41:0] r_t2_0; always @(posedge lint_clk) r_t2_0 <= {42{lint_in}}; assign t2[41:0] = r_t2_0;
    reg [41:0] r_t3_0; always @(posedge lint_clk) r_t3_0 <= {42{lint_in}}; assign t3[41:0] = r_t3_0;
endmodule

module hfd_cmdproc (
    inout wire [359:0] cNE,
    inout wire [359:0] cNW,
    inout wire [359:0] cSE,
    inout wire [359:0] cSW,
    input wire [0:0] ck,
    input wire [63:0] f_barrier,
    input wire [340:0] f_loader,
    input wire [63:0] f_router,
    output wire [63:0] t_coll,
    output wire [63:0] t_su_NE,
    output wire [63:0] t_su_NW,
    output wire [63:0] t_su_SE,
    output wire [63:0] t_su_SW
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^cNE, ^cNW, ^cSE, ^cSW, ^ck, ^f_barrier, ^f_loader, ^f_router};
    reg [41:0] r_cNE_0; always @(posedge lint_clk) r_cNE_0 <= {42{lint_in}}; assign cNE[41:0] = r_cNE_0;
    reg [41:0] r_cNE_45; always @(posedge lint_clk) r_cNE_45 <= {42{lint_in}}; assign cNE[86:45] = r_cNE_45;
    reg [41:0] r_cNE_90; always @(posedge lint_clk) r_cNE_90 <= {42{lint_in}}; assign cNE[131:90] = r_cNE_90;
    reg [41:0] r_cNE_135; always @(posedge lint_clk) r_cNE_135 <= {42{lint_in}}; assign cNE[176:135] = r_cNE_135;
    reg [41:0] r_cNE_180; always @(posedge lint_clk) r_cNE_180 <= {42{lint_in}}; assign cNE[221:180] = r_cNE_180;
    reg [41:0] r_cNE_225; always @(posedge lint_clk) r_cNE_225 <= {42{lint_in}}; assign cNE[266:225] = r_cNE_225;
    reg [41:0] r_cNE_270; always @(posedge lint_clk) r_cNE_270 <= {42{lint_in}}; assign cNE[311:270] = r_cNE_270;
    reg [41:0] r_cNE_315; always @(posedge lint_clk) r_cNE_315 <= {42{lint_in}}; assign cNE[356:315] = r_cNE_315;
    reg [41:0] r_cNW_0; always @(posedge lint_clk) r_cNW_0 <= {42{lint_in}}; assign cNW[41:0] = r_cNW_0;
    reg [41:0] r_cNW_45; always @(posedge lint_clk) r_cNW_45 <= {42{lint_in}}; assign cNW[86:45] = r_cNW_45;
    reg [41:0] r_cNW_90; always @(posedge lint_clk) r_cNW_90 <= {42{lint_in}}; assign cNW[131:90] = r_cNW_90;
    reg [41:0] r_cNW_135; always @(posedge lint_clk) r_cNW_135 <= {42{lint_in}}; assign cNW[176:135] = r_cNW_135;
    reg [41:0] r_cNW_180; always @(posedge lint_clk) r_cNW_180 <= {42{lint_in}}; assign cNW[221:180] = r_cNW_180;
    reg [41:0] r_cNW_225; always @(posedge lint_clk) r_cNW_225 <= {42{lint_in}}; assign cNW[266:225] = r_cNW_225;
    reg [41:0] r_cNW_270; always @(posedge lint_clk) r_cNW_270 <= {42{lint_in}}; assign cNW[311:270] = r_cNW_270;
    reg [41:0] r_cNW_315; always @(posedge lint_clk) r_cNW_315 <= {42{lint_in}}; assign cNW[356:315] = r_cNW_315;
    reg [41:0] r_cSE_0; always @(posedge lint_clk) r_cSE_0 <= {42{lint_in}}; assign cSE[41:0] = r_cSE_0;
    reg [41:0] r_cSE_45; always @(posedge lint_clk) r_cSE_45 <= {42{lint_in}}; assign cSE[86:45] = r_cSE_45;
    reg [41:0] r_cSE_90; always @(posedge lint_clk) r_cSE_90 <= {42{lint_in}}; assign cSE[131:90] = r_cSE_90;
    reg [41:0] r_cSE_135; always @(posedge lint_clk) r_cSE_135 <= {42{lint_in}}; assign cSE[176:135] = r_cSE_135;
    reg [41:0] r_cSE_180; always @(posedge lint_clk) r_cSE_180 <= {42{lint_in}}; assign cSE[221:180] = r_cSE_180;
    reg [41:0] r_cSE_225; always @(posedge lint_clk) r_cSE_225 <= {42{lint_in}}; assign cSE[266:225] = r_cSE_225;
    reg [41:0] r_cSE_270; always @(posedge lint_clk) r_cSE_270 <= {42{lint_in}}; assign cSE[311:270] = r_cSE_270;
    reg [41:0] r_cSE_315; always @(posedge lint_clk) r_cSE_315 <= {42{lint_in}}; assign cSE[356:315] = r_cSE_315;
    reg [41:0] r_cSW_0; always @(posedge lint_clk) r_cSW_0 <= {42{lint_in}}; assign cSW[41:0] = r_cSW_0;
    reg [41:0] r_cSW_45; always @(posedge lint_clk) r_cSW_45 <= {42{lint_in}}; assign cSW[86:45] = r_cSW_45;
    reg [41:0] r_cSW_90; always @(posedge lint_clk) r_cSW_90 <= {42{lint_in}}; assign cSW[131:90] = r_cSW_90;
    reg [41:0] r_cSW_135; always @(posedge lint_clk) r_cSW_135 <= {42{lint_in}}; assign cSW[176:135] = r_cSW_135;
    reg [41:0] r_cSW_180; always @(posedge lint_clk) r_cSW_180 <= {42{lint_in}}; assign cSW[221:180] = r_cSW_180;
    reg [41:0] r_cSW_225; always @(posedge lint_clk) r_cSW_225 <= {42{lint_in}}; assign cSW[266:225] = r_cSW_225;
    reg [41:0] r_cSW_270; always @(posedge lint_clk) r_cSW_270 <= {42{lint_in}}; assign cSW[311:270] = r_cSW_270;
    reg [41:0] r_cSW_315; always @(posedge lint_clk) r_cSW_315 <= {42{lint_in}}; assign cSW[356:315] = r_cSW_315;
    reg [63:0] r_t_coll_0; always @(posedge lint_clk) r_t_coll_0 <= {64{lint_in}}; assign t_coll[63:0] = r_t_coll_0;
    reg [63:0] r_t_su_NE_0; always @(posedge lint_clk) r_t_su_NE_0 <= {64{lint_in}}; assign t_su_NE[63:0] = r_t_su_NE_0;
    reg [63:0] r_t_su_NW_0; always @(posedge lint_clk) r_t_su_NW_0 <= {64{lint_in}}; assign t_su_NW[63:0] = r_t_su_NW_0;
    reg [63:0] r_t_su_SE_0; always @(posedge lint_clk) r_t_su_SE_0 <= {64{lint_in}}; assign t_su_SE[63:0] = r_t_su_SE_0;
    reg [63:0] r_t_su_SW_0; always @(posedge lint_clk) r_t_su_SW_0 <= {64{lint_in}}; assign t_su_SW[63:0] = r_t_su_SW_0;
endmodule

module hfd_coll (
    input wire [63:0] f_cmdproc,
    input wire [1023:0] f_su_NE,
    input wire [1023:0] f_su_NW,
    input wire [1023:0] f_su_SE,
    input wire [1023:0] f_su_SW,
    input wire [511:0] f_vm,
    inout wire [973:0] llk_N0,
    inout wire [973:0] llk_N1,
    inout wire [973:0] llk_N2,
    inout wire [973:0] llk_N3,
    inout wire [973:0] llk_S0,
    inout wire [973:0] llk_S1,
    inout wire [973:0] llk_S2,
    inout wire [973:0] llk_S3,
    inout wire [973:0] llk_S4,
    output wire [0:0] pll_hbm,
    output wire [0:0] pll_serial,
    output wire [0:0] pll_stream,
    output wire [1023:0] t_su_NE,
    output wire [1023:0] t_su_NW,
    output wire [1023:0] t_su_SE,
    output wire [1023:0] t_su_SW
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^f_cmdproc, ^f_su_NE, ^f_su_NW, ^f_su_SE, ^f_su_SW, ^f_vm, ^llk_N0, ^llk_N1, ^llk_N2, ^llk_N3, ^llk_S0, ^llk_S1, ^llk_S2, ^llk_S3, ^llk_S4};
    reg [486:0] r_llk_N0_0; always @(posedge lint_clk) r_llk_N0_0 <= {487{lint_in}}; assign llk_N0[486:0] = r_llk_N0_0;
    reg [486:0] r_llk_N1_0; always @(posedge lint_clk) r_llk_N1_0 <= {487{lint_in}}; assign llk_N1[486:0] = r_llk_N1_0;
    reg [486:0] r_llk_N2_0; always @(posedge lint_clk) r_llk_N2_0 <= {487{lint_in}}; assign llk_N2[486:0] = r_llk_N2_0;
    reg [486:0] r_llk_N3_0; always @(posedge lint_clk) r_llk_N3_0 <= {487{lint_in}}; assign llk_N3[486:0] = r_llk_N3_0;
    reg [486:0] r_llk_S0_0; always @(posedge lint_clk) r_llk_S0_0 <= {487{lint_in}}; assign llk_S0[486:0] = r_llk_S0_0;
    reg [486:0] r_llk_S1_0; always @(posedge lint_clk) r_llk_S1_0 <= {487{lint_in}}; assign llk_S1[486:0] = r_llk_S1_0;
    reg [486:0] r_llk_S2_0; always @(posedge lint_clk) r_llk_S2_0 <= {487{lint_in}}; assign llk_S2[486:0] = r_llk_S2_0;
    reg [486:0] r_llk_S3_0; always @(posedge lint_clk) r_llk_S3_0 <= {487{lint_in}}; assign llk_S3[486:0] = r_llk_S3_0;
    reg [486:0] r_llk_S4_0; always @(posedge lint_clk) r_llk_S4_0 <= {487{lint_in}}; assign llk_S4[486:0] = r_llk_S4_0;
    reg [0:0] r_pll_hbm_0; always @(posedge lint_clk) r_pll_hbm_0 <= {1{lint_in}}; assign pll_hbm[0:0] = r_pll_hbm_0;
    reg [0:0] r_pll_serial_0; always @(posedge lint_clk) r_pll_serial_0 <= {1{lint_in}}; assign pll_serial[0:0] = r_pll_serial_0;
    reg [0:0] r_pll_stream_0; always @(posedge lint_clk) r_pll_stream_0 <= {1{lint_in}}; assign pll_stream[0:0] = r_pll_stream_0;
    reg [1023:0] r_t_su_NE_0; always @(posedge lint_clk) r_t_su_NE_0 <= {1024{lint_in}}; assign t_su_NE[1023:0] = r_t_su_NE_0;
    reg [1023:0] r_t_su_NW_0; always @(posedge lint_clk) r_t_su_NW_0 <= {1024{lint_in}}; assign t_su_NW[1023:0] = r_t_su_NW_0;
    reg [1023:0] r_t_su_SE_0; always @(posedge lint_clk) r_t_su_SE_0 <= {1024{lint_in}}; assign t_su_SE[1023:0] = r_t_su_SE_0;
    reg [1023:0] r_t_su_SW_0; always @(posedge lint_clk) r_t_su_SW_0 <= {1024{lint_in}}; assign t_su_SW[1023:0] = r_t_su_SW_0;
endmodule

module hfd_gath_100 (
    output wire [539:0] b,
    input wire [269:0] t0,
    input wire [269:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^t0, ^t1};
    reg [539:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {540{lint_in}}; assign b[539:0] = r_b_0;
endmodule

module hfd_gath_101 (
    input wire [539:0] a,
    output wire [1079:0] b,
    input wire [269:0] t0,
    input wire [269:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^t0, ^t1};
    reg [1079:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1080{lint_in}}; assign b[1079:0] = r_b_0;
endmodule

module hfd_gath_102 (
    input wire [539:0] a,
    input wire [1079:0] a2,
    output wire [2159:0] b,
    input wire [269:0] t0,
    input wire [269:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^a2, ^t0, ^t1};
    reg [2159:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2160{lint_in}}; assign b[2159:0] = r_b_0;
endmodule

module hfd_gath_144 (
    output wire [539:0] b,
    input wire [269:0] t0,
    input wire [269:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^t0, ^t1};
    reg [539:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {540{lint_in}}; assign b[539:0] = r_b_0;
endmodule

module hfd_gath_145 (
    output wire [539:0] b,
    input wire [269:0] t0,
    input wire [269:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^t0, ^t1};
    reg [539:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {540{lint_in}}; assign b[539:0] = r_b_0;
endmodule

module hfd_gath_146 (
    input wire [539:0] a,
    output wire [1079:0] b,
    input wire [269:0] t0,
    input wire [269:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^t0, ^t1};
    reg [1079:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1080{lint_in}}; assign b[1079:0] = r_b_0;
endmodule

module hfd_gath_147 (
    input wire [539:0] a,
    input wire [1079:0] a2,
    output wire [2159:0] b,
    input wire [269:0] t0,
    input wire [269:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^a2, ^t0, ^t1};
    reg [2159:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2160{lint_in}}; assign b[2159:0] = r_b_0;
endmodule

module hfd_gath_17 (
    output wire [539:0] b,
    input wire [269:0] t0,
    input wire [269:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^t0, ^t1};
    reg [539:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {540{lint_in}}; assign b[539:0] = r_b_0;
endmodule

module hfd_gath_18 (
    output wire [539:0] b,
    input wire [269:0] t0,
    input wire [269:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^t0, ^t1};
    reg [539:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {540{lint_in}}; assign b[539:0] = r_b_0;
endmodule

module hfd_gath_19 (
    input wire [539:0] a,
    output wire [1079:0] b,
    input wire [269:0] t0,
    input wire [269:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^t0, ^t1};
    reg [1079:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1080{lint_in}}; assign b[1079:0] = r_b_0;
endmodule

module hfd_gath_20 (
    input wire [539:0] a,
    input wire [1079:0] a2,
    output wire [2159:0] b,
    input wire [269:0] t0,
    input wire [269:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^a2, ^t0, ^t1};
    reg [2159:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2160{lint_in}}; assign b[2159:0] = r_b_0;
endmodule

module hfd_gath_59 (
    output wire [539:0] b,
    input wire [269:0] t0,
    input wire [269:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^t0, ^t1};
    reg [539:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {540{lint_in}}; assign b[539:0] = r_b_0;
endmodule

module hfd_gath_60 (
    output wire [539:0] b,
    input wire [269:0] t0,
    input wire [269:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^t0, ^t1};
    reg [539:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {540{lint_in}}; assign b[539:0] = r_b_0;
endmodule

module hfd_gath_61 (
    input wire [539:0] a,
    output wire [1079:0] b,
    input wire [269:0] t0,
    input wire [269:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^t0, ^t1};
    reg [1079:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1080{lint_in}}; assign b[1079:0] = r_b_0;
endmodule

module hfd_gath_62 (
    input wire [539:0] a,
    input wire [1079:0] a2,
    output wire [2159:0] b,
    input wire [269:0] t0,
    input wire [269:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^a2, ^t0, ^t1};
    reg [2159:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2160{lint_in}}; assign b[2159:0] = r_b_0;
endmodule

module hfd_gath_99 (
    output wire [539:0] b,
    input wire [269:0] t0,
    input wire [269:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^t0, ^t1};
    reg [539:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {540{lint_in}}; assign b[539:0] = r_b_0;
endmodule

module hfd_hc (
    input wire [0:0] ck,
    input wire [1023:0] f_sfu
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^f_sfu};
endmodule

module hfd_host_slab (

);  // NO PORTS: reservation slab, no die net
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{1'b0};
endmodule

module hfd_index_q (
    input wire [511:0] a0,
    input wire [511:0] a1,
    input wire [511:0] a2,
    input wire [511:0] a3,
    input wire [0:0] ck,
    input wire [1023:0] k,
    output wire [1023:0] t_su,
    output wire [511:0] t_vm
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^a0, ^a1, ^a2, ^a3, ^ck, ^k};
    reg [1023:0] r_t_su_0; always @(posedge lint_clk) r_t_su_0 <= {1024{lint_in}}; assign t_su[1023:0] = r_t_su_0;
    reg [511:0] r_t_vm_0; always @(posedge lint_clk) r_t_vm_0 <= {512{lint_in}}; assign t_vm[511:0] = r_t_vm_0;
endmodule

module hfd_loader (
    input wire [0:0] ck,
    inout wire [511:0] h,
    output wire [340:0] t_cmdproc
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^h};
    reg [255:0] r_h_0; always @(posedge lint_clk) r_h_0 <= {256{lint_in}}; assign h[255:0] = r_h_0;
    reg [340:0] r_t_cmdproc_0; always @(posedge lint_clk) r_t_cmdproc_0 <= {341{lint_in}}; assign t_cmdproc[340:0] = r_t_cmdproc_0;
endmodule

module hfd_mcast_13 (
    input wire [2062:0] a,
    output wire [2062:0] b,
    output wire [2062:0] t0,
    output wire [2062:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2063{lint_in}}; assign b[2062:0] = r_b_0;
    reg [2062:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {2063{lint_in}}; assign t0[2062:0] = r_t0_0;
    reg [2062:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {2063{lint_in}}; assign t1[2062:0] = r_t1_0;
endmodule

module hfd_mcast_14 (
    input wire [2062:0] a,
    output wire [2062:0] b,
    output wire [2062:0] t0,
    output wire [2062:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2063{lint_in}}; assign b[2062:0] = r_b_0;
    reg [2062:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {2063{lint_in}}; assign t0[2062:0] = r_t0_0;
    reg [2062:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {2063{lint_in}}; assign t1[2062:0] = r_t1_0;
endmodule

module hfd_mcast_140 (
    input wire [2062:0] a,
    output wire [2062:0] b,
    output wire [2062:0] t0,
    output wire [2062:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2063{lint_in}}; assign b[2062:0] = r_b_0;
    reg [2062:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {2063{lint_in}}; assign t0[2062:0] = r_t0_0;
    reg [2062:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {2063{lint_in}}; assign t1[2062:0] = r_t1_0;
endmodule

module hfd_mcast_141 (
    input wire [2062:0] a,
    output wire [2062:0] b,
    output wire [2062:0] t0,
    output wire [2062:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2063{lint_in}}; assign b[2062:0] = r_b_0;
    reg [2062:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {2063{lint_in}}; assign t0[2062:0] = r_t0_0;
    reg [2062:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {2063{lint_in}}; assign t1[2062:0] = r_t1_0;
endmodule

module hfd_mcast_142 (
    input wire [2062:0] a,
    output wire [2062:0] b,
    output wire [2062:0] t0,
    output wire [2062:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2063{lint_in}}; assign b[2062:0] = r_b_0;
    reg [2062:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {2063{lint_in}}; assign t0[2062:0] = r_t0_0;
    reg [2062:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {2063{lint_in}}; assign t1[2062:0] = r_t1_0;
endmodule

module hfd_mcast_143 (
    input wire [2062:0] a,
    output wire [2062:0] t0,
    output wire [2062:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {2063{lint_in}}; assign t0[2062:0] = r_t0_0;
    reg [2062:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {2063{lint_in}}; assign t1[2062:0] = r_t1_0;
endmodule

module hfd_mcast_15 (
    input wire [2062:0] a,
    output wire [2062:0] b,
    output wire [2062:0] t0,
    output wire [2062:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2063{lint_in}}; assign b[2062:0] = r_b_0;
    reg [2062:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {2063{lint_in}}; assign t0[2062:0] = r_t0_0;
    reg [2062:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {2063{lint_in}}; assign t1[2062:0] = r_t1_0;
endmodule

module hfd_mcast_16 (
    input wire [2062:0] a,
    output wire [2062:0] t0,
    output wire [2062:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {2063{lint_in}}; assign t0[2062:0] = r_t0_0;
    reg [2062:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {2063{lint_in}}; assign t1[2062:0] = r_t1_0;
endmodule

module hfd_mcast_55 (
    input wire [2062:0] a,
    output wire [2062:0] b,
    output wire [2062:0] t0,
    output wire [2062:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2063{lint_in}}; assign b[2062:0] = r_b_0;
    reg [2062:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {2063{lint_in}}; assign t0[2062:0] = r_t0_0;
    reg [2062:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {2063{lint_in}}; assign t1[2062:0] = r_t1_0;
endmodule

module hfd_mcast_56 (
    input wire [2062:0] a,
    output wire [2062:0] b,
    output wire [2062:0] t0,
    output wire [2062:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2063{lint_in}}; assign b[2062:0] = r_b_0;
    reg [2062:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {2063{lint_in}}; assign t0[2062:0] = r_t0_0;
    reg [2062:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {2063{lint_in}}; assign t1[2062:0] = r_t1_0;
endmodule

module hfd_mcast_57 (
    input wire [2062:0] a,
    output wire [2062:0] b,
    output wire [2062:0] t0,
    output wire [2062:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2063{lint_in}}; assign b[2062:0] = r_b_0;
    reg [2062:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {2063{lint_in}}; assign t0[2062:0] = r_t0_0;
    reg [2062:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {2063{lint_in}}; assign t1[2062:0] = r_t1_0;
endmodule

module hfd_mcast_58 (
    input wire [2062:0] a,
    output wire [2062:0] t0,
    output wire [2062:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {2063{lint_in}}; assign t0[2062:0] = r_t0_0;
    reg [2062:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {2063{lint_in}}; assign t1[2062:0] = r_t1_0;
endmodule

module hfd_mcast_95 (
    input wire [2062:0] a,
    output wire [2062:0] b,
    output wire [2062:0] t0,
    output wire [2062:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2063{lint_in}}; assign b[2062:0] = r_b_0;
    reg [2062:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {2063{lint_in}}; assign t0[2062:0] = r_t0_0;
    reg [2062:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {2063{lint_in}}; assign t1[2062:0] = r_t1_0;
endmodule

module hfd_mcast_96 (
    input wire [2062:0] a,
    output wire [2062:0] b,
    output wire [2062:0] t0,
    output wire [2062:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2063{lint_in}}; assign b[2062:0] = r_b_0;
    reg [2062:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {2063{lint_in}}; assign t0[2062:0] = r_t0_0;
    reg [2062:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {2063{lint_in}}; assign t1[2062:0] = r_t1_0;
endmodule

module hfd_mcast_97 (
    input wire [2062:0] a,
    output wire [2062:0] b,
    output wire [2062:0] t0,
    output wire [2062:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2063{lint_in}}; assign b[2062:0] = r_b_0;
    reg [2062:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {2063{lint_in}}; assign t0[2062:0] = r_t0_0;
    reg [2062:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {2063{lint_in}}; assign t1[2062:0] = r_t1_0;
endmodule

module hfd_mcast_98 (
    input wire [2062:0] a,
    output wire [2062:0] t0,
    output wire [2062:0] t1
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_t0_0; always @(posedge lint_clk) r_t0_0 <= {2063{lint_in}}; assign t0[2062:0] = r_t0_0;
    reg [2062:0] r_t1_0; always @(posedge lint_clk) r_t1_0 <= {2063{lint_in}}; assign t1[2062:0] = r_t1_0;
endmodule

module hfd_quant (
    input wire [0:0] ck,
    input wire [1023:0] f_vm,
    output wire [511:0] t_su_NE,
    output wire [511:0] t_su_NW,
    output wire [511:0] t_su_SE,
    output wire [511:0] t_su_SW
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^f_vm};
    reg [511:0] r_t_su_NE_0; always @(posedge lint_clk) r_t_su_NE_0 <= {512{lint_in}}; assign t_su_NE[511:0] = r_t_su_NE_0;
    reg [511:0] r_t_su_NW_0; always @(posedge lint_clk) r_t_su_NW_0 <= {512{lint_in}}; assign t_su_NW[511:0] = r_t_su_NW_0;
    reg [511:0] r_t_su_SE_0; always @(posedge lint_clk) r_t_su_SE_0 <= {512{lint_in}}; assign t_su_SE[511:0] = r_t_su_SE_0;
    reg [511:0] r_t_su_SW_0; always @(posedge lint_clk) r_t_su_SW_0 <= {512{lint_in}}; assign t_su_SW[511:0] = r_t_su_SW_0;
endmodule

module hfd_router (
    input wire [0:0] ck,
    output wire [127:0] eNE,
    output wire [127:0] eNW,
    output wire [127:0] eSE,
    output wire [127:0] eSW,
    input wire [255:0] f_su_NE,
    input wire [255:0] f_su_NW,
    input wire [255:0] f_su_SE,
    input wire [255:0] f_su_SW,
    input wire [511:0] f_vm,
    output wire [63:0] t_cmdproc
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^f_su_NE, ^f_su_NW, ^f_su_SE, ^f_su_SW, ^f_vm};
    reg [127:0] r_eNE_0; always @(posedge lint_clk) r_eNE_0 <= {128{lint_in}}; assign eNE[127:0] = r_eNE_0;
    reg [127:0] r_eNW_0; always @(posedge lint_clk) r_eNW_0 <= {128{lint_in}}; assign eNW[127:0] = r_eNW_0;
    reg [127:0] r_eSE_0; always @(posedge lint_clk) r_eSE_0 <= {128{lint_in}}; assign eSE[127:0] = r_eSE_0;
    reg [127:0] r_eSW_0; always @(posedge lint_clk) r_eSW_0 <= {128{lint_in}}; assign eSW[127:0] = r_eSW_0;
    reg [63:0] r_t_cmdproc_0; always @(posedge lint_clk) r_t_cmdproc_0 <= {64{lint_in}}; assign t_cmdproc[63:0] = r_t_cmdproc_0;
endmodule

module hfd_serdes_slab (

);  // NO PORTS: reservation slab, no die net
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{1'b0};
endmodule

module hfd_sfu (
    input wire [0:0] ck,
    input wire [1023:0] f_su,
    output wire [1023:0] t_hc
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^f_su};
    reg [1023:0] r_t_hc_0; always @(posedge lint_clk) r_t_hc_0 <= {1024{lint_in}}; assign t_hc[1023:0] = r_t_hc_0;
endmodule

module hfd_stn_1 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_10 (
    input wire [2062:0] a,
    output wire [2062:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2063{lint_in}}; assign b[2062:0] = r_b_0;
endmodule

module hfd_stn_103 (
    input wire [2159:0] a,
    output wire [2159:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2159:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2160{lint_in}}; assign b[2159:0] = r_b_0;
endmodule

module hfd_stn_104 (
    input wire [2159:0] a,
    output wire [2159:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2159:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2160{lint_in}}; assign b[2159:0] = r_b_0;
endmodule

module hfd_stn_105 (
    input wire [2159:0] a,
    output wire [2159:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2159:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2160{lint_in}}; assign b[2159:0] = r_b_0;
endmodule

module hfd_stn_106 (
    inout wire [359:0] a,
    inout wire [359:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [2:0] r_a_222; always @(posedge lint_clk) r_a_222 <= {3{lint_in}}; assign a[224:222] = r_a_222;
    reg [2:0] r_a_267; always @(posedge lint_clk) r_a_267 <= {3{lint_in}}; assign a[269:267] = r_a_267;
    reg [2:0] r_a_312; always @(posedge lint_clk) r_a_312 <= {3{lint_in}}; assign a[314:312] = r_a_312;
    reg [2:0] r_a_357; always @(posedge lint_clk) r_a_357 <= {3{lint_in}}; assign a[359:357] = r_a_357;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [41:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {42{lint_in}}; assign b[86:45] = r_b_45;
    reg [41:0] r_b_90; always @(posedge lint_clk) r_b_90 <= {42{lint_in}}; assign b[131:90] = r_b_90;
    reg [41:0] r_b_135; always @(posedge lint_clk) r_b_135 <= {42{lint_in}}; assign b[176:135] = r_b_135;
    reg [41:0] r_b_180; always @(posedge lint_clk) r_b_180 <= {42{lint_in}}; assign b[221:180] = r_b_180;
    reg [41:0] r_b_225; always @(posedge lint_clk) r_b_225 <= {42{lint_in}}; assign b[266:225] = r_b_225;
    reg [41:0] r_b_270; always @(posedge lint_clk) r_b_270 <= {42{lint_in}}; assign b[311:270] = r_b_270;
    reg [41:0] r_b_315; always @(posedge lint_clk) r_b_315 <= {42{lint_in}}; assign b[356:315] = r_b_315;
endmodule

module hfd_stn_107 (
    inout wire [359:0] a,
    inout wire [359:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [2:0] r_a_222; always @(posedge lint_clk) r_a_222 <= {3{lint_in}}; assign a[224:222] = r_a_222;
    reg [2:0] r_a_267; always @(posedge lint_clk) r_a_267 <= {3{lint_in}}; assign a[269:267] = r_a_267;
    reg [2:0] r_a_312; always @(posedge lint_clk) r_a_312 <= {3{lint_in}}; assign a[314:312] = r_a_312;
    reg [2:0] r_a_357; always @(posedge lint_clk) r_a_357 <= {3{lint_in}}; assign a[359:357] = r_a_357;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [41:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {42{lint_in}}; assign b[86:45] = r_b_45;
    reg [41:0] r_b_90; always @(posedge lint_clk) r_b_90 <= {42{lint_in}}; assign b[131:90] = r_b_90;
    reg [41:0] r_b_135; always @(posedge lint_clk) r_b_135 <= {42{lint_in}}; assign b[176:135] = r_b_135;
    reg [41:0] r_b_180; always @(posedge lint_clk) r_b_180 <= {42{lint_in}}; assign b[221:180] = r_b_180;
    reg [41:0] r_b_225; always @(posedge lint_clk) r_b_225 <= {42{lint_in}}; assign b[266:225] = r_b_225;
    reg [41:0] r_b_270; always @(posedge lint_clk) r_b_270 <= {42{lint_in}}; assign b[311:270] = r_b_270;
    reg [41:0] r_b_315; always @(posedge lint_clk) r_b_315 <= {42{lint_in}}; assign b[356:315] = r_b_315;
endmodule

module hfd_stn_108 (
    inout wire [359:0] a,
    inout wire [359:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [2:0] r_a_222; always @(posedge lint_clk) r_a_222 <= {3{lint_in}}; assign a[224:222] = r_a_222;
    reg [2:0] r_a_267; always @(posedge lint_clk) r_a_267 <= {3{lint_in}}; assign a[269:267] = r_a_267;
    reg [2:0] r_a_312; always @(posedge lint_clk) r_a_312 <= {3{lint_in}}; assign a[314:312] = r_a_312;
    reg [2:0] r_a_357; always @(posedge lint_clk) r_a_357 <= {3{lint_in}}; assign a[359:357] = r_a_357;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [41:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {42{lint_in}}; assign b[86:45] = r_b_45;
    reg [41:0] r_b_90; always @(posedge lint_clk) r_b_90 <= {42{lint_in}}; assign b[131:90] = r_b_90;
    reg [41:0] r_b_135; always @(posedge lint_clk) r_b_135 <= {42{lint_in}}; assign b[176:135] = r_b_135;
    reg [41:0] r_b_180; always @(posedge lint_clk) r_b_180 <= {42{lint_in}}; assign b[221:180] = r_b_180;
    reg [41:0] r_b_225; always @(posedge lint_clk) r_b_225 <= {42{lint_in}}; assign b[266:225] = r_b_225;
    reg [41:0] r_b_270; always @(posedge lint_clk) r_b_270 <= {42{lint_in}}; assign b[311:270] = r_b_270;
    reg [41:0] r_b_315; always @(posedge lint_clk) r_b_315 <= {42{lint_in}}; assign b[356:315] = r_b_315;
endmodule

module hfd_stn_109 (
    inout wire [359:0] a,
    inout wire [359:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [2:0] r_a_222; always @(posedge lint_clk) r_a_222 <= {3{lint_in}}; assign a[224:222] = r_a_222;
    reg [2:0] r_a_267; always @(posedge lint_clk) r_a_267 <= {3{lint_in}}; assign a[269:267] = r_a_267;
    reg [2:0] r_a_312; always @(posedge lint_clk) r_a_312 <= {3{lint_in}}; assign a[314:312] = r_a_312;
    reg [2:0] r_a_357; always @(posedge lint_clk) r_a_357 <= {3{lint_in}}; assign a[359:357] = r_a_357;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [41:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {42{lint_in}}; assign b[86:45] = r_b_45;
    reg [41:0] r_b_90; always @(posedge lint_clk) r_b_90 <= {42{lint_in}}; assign b[131:90] = r_b_90;
    reg [41:0] r_b_135; always @(posedge lint_clk) r_b_135 <= {42{lint_in}}; assign b[176:135] = r_b_135;
    reg [41:0] r_b_180; always @(posedge lint_clk) r_b_180 <= {42{lint_in}}; assign b[221:180] = r_b_180;
    reg [41:0] r_b_225; always @(posedge lint_clk) r_b_225 <= {42{lint_in}}; assign b[266:225] = r_b_225;
    reg [41:0] r_b_270; always @(posedge lint_clk) r_b_270 <= {42{lint_in}}; assign b[311:270] = r_b_270;
    reg [41:0] r_b_315; always @(posedge lint_clk) r_b_315 <= {42{lint_in}}; assign b[356:315] = r_b_315;
endmodule

module hfd_stn_11 (
    input wire [2062:0] a,
    output wire [2062:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2063{lint_in}}; assign b[2062:0] = r_b_0;
endmodule

module hfd_stn_110 (
    inout wire [359:0] a,
    inout wire [359:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [2:0] r_a_222; always @(posedge lint_clk) r_a_222 <= {3{lint_in}}; assign a[224:222] = r_a_222;
    reg [2:0] r_a_267; always @(posedge lint_clk) r_a_267 <= {3{lint_in}}; assign a[269:267] = r_a_267;
    reg [2:0] r_a_312; always @(posedge lint_clk) r_a_312 <= {3{lint_in}}; assign a[314:312] = r_a_312;
    reg [2:0] r_a_357; always @(posedge lint_clk) r_a_357 <= {3{lint_in}}; assign a[359:357] = r_a_357;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [41:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {42{lint_in}}; assign b[86:45] = r_b_45;
    reg [41:0] r_b_90; always @(posedge lint_clk) r_b_90 <= {42{lint_in}}; assign b[131:90] = r_b_90;
    reg [41:0] r_b_135; always @(posedge lint_clk) r_b_135 <= {42{lint_in}}; assign b[176:135] = r_b_135;
    reg [41:0] r_b_180; always @(posedge lint_clk) r_b_180 <= {42{lint_in}}; assign b[221:180] = r_b_180;
    reg [41:0] r_b_225; always @(posedge lint_clk) r_b_225 <= {42{lint_in}}; assign b[266:225] = r_b_225;
    reg [41:0] r_b_270; always @(posedge lint_clk) r_b_270 <= {42{lint_in}}; assign b[311:270] = r_b_270;
    reg [41:0] r_b_315; always @(posedge lint_clk) r_b_315 <= {42{lint_in}}; assign b[356:315] = r_b_315;
endmodule

module hfd_stn_111 (
    inout wire [359:0] a,
    inout wire [359:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [2:0] r_a_222; always @(posedge lint_clk) r_a_222 <= {3{lint_in}}; assign a[224:222] = r_a_222;
    reg [2:0] r_a_267; always @(posedge lint_clk) r_a_267 <= {3{lint_in}}; assign a[269:267] = r_a_267;
    reg [2:0] r_a_312; always @(posedge lint_clk) r_a_312 <= {3{lint_in}}; assign a[314:312] = r_a_312;
    reg [2:0] r_a_357; always @(posedge lint_clk) r_a_357 <= {3{lint_in}}; assign a[359:357] = r_a_357;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [41:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {42{lint_in}}; assign b[86:45] = r_b_45;
    reg [41:0] r_b_90; always @(posedge lint_clk) r_b_90 <= {42{lint_in}}; assign b[131:90] = r_b_90;
    reg [41:0] r_b_135; always @(posedge lint_clk) r_b_135 <= {42{lint_in}}; assign b[176:135] = r_b_135;
    reg [41:0] r_b_180; always @(posedge lint_clk) r_b_180 <= {42{lint_in}}; assign b[221:180] = r_b_180;
    reg [41:0] r_b_225; always @(posedge lint_clk) r_b_225 <= {42{lint_in}}; assign b[266:225] = r_b_225;
    reg [41:0] r_b_270; always @(posedge lint_clk) r_b_270 <= {42{lint_in}}; assign b[311:270] = r_b_270;
    reg [41:0] r_b_315; always @(posedge lint_clk) r_b_315 <= {42{lint_in}}; assign b[356:315] = r_b_315;
endmodule

module hfd_stn_114 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_115 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_116 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_117 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_118 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_119 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_12 (
    input wire [2062:0] a,
    output wire [2062:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2063{lint_in}}; assign b[2062:0] = r_b_0;
endmodule

module hfd_stn_120 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_121 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_122 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_123 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_124 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_125 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_126 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_127 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_128 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_129 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_130 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_131 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_132 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_133 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_134 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_135 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_136 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_137 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_138 (
    input wire [2062:0] a,
    output wire [2062:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2063{lint_in}}; assign b[2062:0] = r_b_0;
endmodule

module hfd_stn_139 (
    input wire [2062:0] a,
    output wire [2062:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2063{lint_in}}; assign b[2062:0] = r_b_0;
endmodule

module hfd_stn_148 (
    input wire [2159:0] a,
    output wire [2159:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2159:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2160{lint_in}}; assign b[2159:0] = r_b_0;
endmodule

module hfd_stn_149 (
    input wire [2159:0] a,
    output wire [2159:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2159:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2160{lint_in}}; assign b[2159:0] = r_b_0;
endmodule

module hfd_stn_150 (
    input wire [2159:0] a,
    output wire [2159:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2159:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2160{lint_in}}; assign b[2159:0] = r_b_0;
endmodule

module hfd_stn_151 (
    input wire [2159:0] a,
    output wire [2159:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2159:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2160{lint_in}}; assign b[2159:0] = r_b_0;
endmodule

module hfd_stn_152 (
    inout wire [359:0] a,
    inout wire [359:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [2:0] r_a_222; always @(posedge lint_clk) r_a_222 <= {3{lint_in}}; assign a[224:222] = r_a_222;
    reg [2:0] r_a_267; always @(posedge lint_clk) r_a_267 <= {3{lint_in}}; assign a[269:267] = r_a_267;
    reg [2:0] r_a_312; always @(posedge lint_clk) r_a_312 <= {3{lint_in}}; assign a[314:312] = r_a_312;
    reg [2:0] r_a_357; always @(posedge lint_clk) r_a_357 <= {3{lint_in}}; assign a[359:357] = r_a_357;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [41:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {42{lint_in}}; assign b[86:45] = r_b_45;
    reg [41:0] r_b_90; always @(posedge lint_clk) r_b_90 <= {42{lint_in}}; assign b[131:90] = r_b_90;
    reg [41:0] r_b_135; always @(posedge lint_clk) r_b_135 <= {42{lint_in}}; assign b[176:135] = r_b_135;
    reg [41:0] r_b_180; always @(posedge lint_clk) r_b_180 <= {42{lint_in}}; assign b[221:180] = r_b_180;
    reg [41:0] r_b_225; always @(posedge lint_clk) r_b_225 <= {42{lint_in}}; assign b[266:225] = r_b_225;
    reg [41:0] r_b_270; always @(posedge lint_clk) r_b_270 <= {42{lint_in}}; assign b[311:270] = r_b_270;
    reg [41:0] r_b_315; always @(posedge lint_clk) r_b_315 <= {42{lint_in}}; assign b[356:315] = r_b_315;
endmodule

module hfd_stn_153 (
    inout wire [359:0] a,
    inout wire [359:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [2:0] r_a_222; always @(posedge lint_clk) r_a_222 <= {3{lint_in}}; assign a[224:222] = r_a_222;
    reg [2:0] r_a_267; always @(posedge lint_clk) r_a_267 <= {3{lint_in}}; assign a[269:267] = r_a_267;
    reg [2:0] r_a_312; always @(posedge lint_clk) r_a_312 <= {3{lint_in}}; assign a[314:312] = r_a_312;
    reg [2:0] r_a_357; always @(posedge lint_clk) r_a_357 <= {3{lint_in}}; assign a[359:357] = r_a_357;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [41:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {42{lint_in}}; assign b[86:45] = r_b_45;
    reg [41:0] r_b_90; always @(posedge lint_clk) r_b_90 <= {42{lint_in}}; assign b[131:90] = r_b_90;
    reg [41:0] r_b_135; always @(posedge lint_clk) r_b_135 <= {42{lint_in}}; assign b[176:135] = r_b_135;
    reg [41:0] r_b_180; always @(posedge lint_clk) r_b_180 <= {42{lint_in}}; assign b[221:180] = r_b_180;
    reg [41:0] r_b_225; always @(posedge lint_clk) r_b_225 <= {42{lint_in}}; assign b[266:225] = r_b_225;
    reg [41:0] r_b_270; always @(posedge lint_clk) r_b_270 <= {42{lint_in}}; assign b[311:270] = r_b_270;
    reg [41:0] r_b_315; always @(posedge lint_clk) r_b_315 <= {42{lint_in}}; assign b[356:315] = r_b_315;
endmodule

module hfd_stn_154 (
    inout wire [359:0] a,
    inout wire [359:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [2:0] r_a_222; always @(posedge lint_clk) r_a_222 <= {3{lint_in}}; assign a[224:222] = r_a_222;
    reg [2:0] r_a_267; always @(posedge lint_clk) r_a_267 <= {3{lint_in}}; assign a[269:267] = r_a_267;
    reg [2:0] r_a_312; always @(posedge lint_clk) r_a_312 <= {3{lint_in}}; assign a[314:312] = r_a_312;
    reg [2:0] r_a_357; always @(posedge lint_clk) r_a_357 <= {3{lint_in}}; assign a[359:357] = r_a_357;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [41:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {42{lint_in}}; assign b[86:45] = r_b_45;
    reg [41:0] r_b_90; always @(posedge lint_clk) r_b_90 <= {42{lint_in}}; assign b[131:90] = r_b_90;
    reg [41:0] r_b_135; always @(posedge lint_clk) r_b_135 <= {42{lint_in}}; assign b[176:135] = r_b_135;
    reg [41:0] r_b_180; always @(posedge lint_clk) r_b_180 <= {42{lint_in}}; assign b[221:180] = r_b_180;
    reg [41:0] r_b_225; always @(posedge lint_clk) r_b_225 <= {42{lint_in}}; assign b[266:225] = r_b_225;
    reg [41:0] r_b_270; always @(posedge lint_clk) r_b_270 <= {42{lint_in}}; assign b[311:270] = r_b_270;
    reg [41:0] r_b_315; always @(posedge lint_clk) r_b_315 <= {42{lint_in}}; assign b[356:315] = r_b_315;
endmodule

module hfd_stn_155 (
    inout wire [359:0] a,
    inout wire [359:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [2:0] r_a_222; always @(posedge lint_clk) r_a_222 <= {3{lint_in}}; assign a[224:222] = r_a_222;
    reg [2:0] r_a_267; always @(posedge lint_clk) r_a_267 <= {3{lint_in}}; assign a[269:267] = r_a_267;
    reg [2:0] r_a_312; always @(posedge lint_clk) r_a_312 <= {3{lint_in}}; assign a[314:312] = r_a_312;
    reg [2:0] r_a_357; always @(posedge lint_clk) r_a_357 <= {3{lint_in}}; assign a[359:357] = r_a_357;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [41:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {42{lint_in}}; assign b[86:45] = r_b_45;
    reg [41:0] r_b_90; always @(posedge lint_clk) r_b_90 <= {42{lint_in}}; assign b[131:90] = r_b_90;
    reg [41:0] r_b_135; always @(posedge lint_clk) r_b_135 <= {42{lint_in}}; assign b[176:135] = r_b_135;
    reg [41:0] r_b_180; always @(posedge lint_clk) r_b_180 <= {42{lint_in}}; assign b[221:180] = r_b_180;
    reg [41:0] r_b_225; always @(posedge lint_clk) r_b_225 <= {42{lint_in}}; assign b[266:225] = r_b_225;
    reg [41:0] r_b_270; always @(posedge lint_clk) r_b_270 <= {42{lint_in}}; assign b[311:270] = r_b_270;
    reg [41:0] r_b_315; always @(posedge lint_clk) r_b_315 <= {42{lint_in}}; assign b[356:315] = r_b_315;
endmodule

module hfd_stn_156 (
    inout wire [359:0] a,
    inout wire [359:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [2:0] r_a_222; always @(posedge lint_clk) r_a_222 <= {3{lint_in}}; assign a[224:222] = r_a_222;
    reg [2:0] r_a_267; always @(posedge lint_clk) r_a_267 <= {3{lint_in}}; assign a[269:267] = r_a_267;
    reg [2:0] r_a_312; always @(posedge lint_clk) r_a_312 <= {3{lint_in}}; assign a[314:312] = r_a_312;
    reg [2:0] r_a_357; always @(posedge lint_clk) r_a_357 <= {3{lint_in}}; assign a[359:357] = r_a_357;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [41:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {42{lint_in}}; assign b[86:45] = r_b_45;
    reg [41:0] r_b_90; always @(posedge lint_clk) r_b_90 <= {42{lint_in}}; assign b[131:90] = r_b_90;
    reg [41:0] r_b_135; always @(posedge lint_clk) r_b_135 <= {42{lint_in}}; assign b[176:135] = r_b_135;
    reg [41:0] r_b_180; always @(posedge lint_clk) r_b_180 <= {42{lint_in}}; assign b[221:180] = r_b_180;
    reg [41:0] r_b_225; always @(posedge lint_clk) r_b_225 <= {42{lint_in}}; assign b[266:225] = r_b_225;
    reg [41:0] r_b_270; always @(posedge lint_clk) r_b_270 <= {42{lint_in}}; assign b[311:270] = r_b_270;
    reg [41:0] r_b_315; always @(posedge lint_clk) r_b_315 <= {42{lint_in}}; assign b[356:315] = r_b_315;
endmodule

module hfd_stn_157 (
    inout wire [359:0] a,
    inout wire [359:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [2:0] r_a_222; always @(posedge lint_clk) r_a_222 <= {3{lint_in}}; assign a[224:222] = r_a_222;
    reg [2:0] r_a_267; always @(posedge lint_clk) r_a_267 <= {3{lint_in}}; assign a[269:267] = r_a_267;
    reg [2:0] r_a_312; always @(posedge lint_clk) r_a_312 <= {3{lint_in}}; assign a[314:312] = r_a_312;
    reg [2:0] r_a_357; always @(posedge lint_clk) r_a_357 <= {3{lint_in}}; assign a[359:357] = r_a_357;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [41:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {42{lint_in}}; assign b[86:45] = r_b_45;
    reg [41:0] r_b_90; always @(posedge lint_clk) r_b_90 <= {42{lint_in}}; assign b[131:90] = r_b_90;
    reg [41:0] r_b_135; always @(posedge lint_clk) r_b_135 <= {42{lint_in}}; assign b[176:135] = r_b_135;
    reg [41:0] r_b_180; always @(posedge lint_clk) r_b_180 <= {42{lint_in}}; assign b[221:180] = r_b_180;
    reg [41:0] r_b_225; always @(posedge lint_clk) r_b_225 <= {42{lint_in}}; assign b[266:225] = r_b_225;
    reg [41:0] r_b_270; always @(posedge lint_clk) r_b_270 <= {42{lint_in}}; assign b[311:270] = r_b_270;
    reg [41:0] r_b_315; always @(posedge lint_clk) r_b_315 <= {42{lint_in}}; assign b[356:315] = r_b_315;
endmodule

module hfd_stn_160 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_161 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_162 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_163 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_164 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_165 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_166 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_167 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_168 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_169 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_170 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_171 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_172 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_173 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_174 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_175 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_176 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_177 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_178 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_179 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_180 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_181 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_182 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_183 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_184 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_185 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_186 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_187 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_188 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_189 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_190 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_191 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_192 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_193 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_194 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_195 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_196 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_197 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_198 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_199 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_2 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_200 (
    inout wire [973:0] a,
    inout wire [973:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [486:0] r_a_487; always @(posedge lint_clk) r_a_487 <= {487{lint_in}}; assign a[973:487] = r_a_487;
    reg [486:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {487{lint_in}}; assign b[486:0] = r_b_0;
endmodule

module hfd_stn_201 (
    inout wire [511:0] a,
    inout wire [511:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [255:0] r_a_256; always @(posedge lint_clk) r_a_256 <= {256{lint_in}}; assign a[511:256] = r_a_256;
    reg [255:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {256{lint_in}}; assign b[255:0] = r_b_0;
endmodule

module hfd_stn_202 (
    inout wire [511:0] a,
    inout wire [511:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [255:0] r_a_256; always @(posedge lint_clk) r_a_256 <= {256{lint_in}}; assign a[511:256] = r_a_256;
    reg [255:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {256{lint_in}}; assign b[255:0] = r_b_0;
endmodule

module hfd_stn_203 (
    inout wire [511:0] a,
    inout wire [511:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [255:0] r_a_256; always @(posedge lint_clk) r_a_256 <= {256{lint_in}}; assign a[511:256] = r_a_256;
    reg [255:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {256{lint_in}}; assign b[255:0] = r_b_0;
endmodule

module hfd_stn_204 (
    inout wire [511:0] a,
    inout wire [511:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [255:0] r_a_256; always @(posedge lint_clk) r_a_256 <= {256{lint_in}}; assign a[511:256] = r_a_256;
    reg [255:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {256{lint_in}}; assign b[255:0] = r_b_0;
endmodule

module hfd_stn_205 (
    inout wire [511:0] a,
    inout wire [511:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [255:0] r_a_256; always @(posedge lint_clk) r_a_256 <= {256{lint_in}}; assign a[511:256] = r_a_256;
    reg [255:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {256{lint_in}}; assign b[255:0] = r_b_0;
endmodule

module hfd_stn_206 (
    inout wire [511:0] a,
    inout wire [511:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [255:0] r_a_256; always @(posedge lint_clk) r_a_256 <= {256{lint_in}}; assign a[511:256] = r_a_256;
    reg [255:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {256{lint_in}}; assign b[255:0] = r_b_0;
endmodule

module hfd_stn_207 (
    inout wire [511:0] a,
    inout wire [511:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [255:0] r_a_256; always @(posedge lint_clk) r_a_256 <= {256{lint_in}}; assign a[511:256] = r_a_256;
    reg [255:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {256{lint_in}}; assign b[255:0] = r_b_0;
endmodule

module hfd_stn_208 (
    inout wire [511:0] a,
    inout wire [511:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [255:0] r_a_256; always @(posedge lint_clk) r_a_256 <= {256{lint_in}}; assign a[511:256] = r_a_256;
    reg [255:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {256{lint_in}}; assign b[255:0] = r_b_0;
endmodule

module hfd_stn_21 (
    input wire [2159:0] a,
    output wire [2159:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2159:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2160{lint_in}}; assign b[2159:0] = r_b_0;
endmodule

module hfd_stn_22 (
    input wire [2159:0] a,
    output wire [2159:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2159:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2160{lint_in}}; assign b[2159:0] = r_b_0;
endmodule

module hfd_stn_23 (
    input wire [2159:0] a,
    output wire [2159:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2159:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2160{lint_in}}; assign b[2159:0] = r_b_0;
endmodule

module hfd_stn_24 (
    inout wire [359:0] a,
    inout wire [359:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [2:0] r_a_222; always @(posedge lint_clk) r_a_222 <= {3{lint_in}}; assign a[224:222] = r_a_222;
    reg [2:0] r_a_267; always @(posedge lint_clk) r_a_267 <= {3{lint_in}}; assign a[269:267] = r_a_267;
    reg [2:0] r_a_312; always @(posedge lint_clk) r_a_312 <= {3{lint_in}}; assign a[314:312] = r_a_312;
    reg [2:0] r_a_357; always @(posedge lint_clk) r_a_357 <= {3{lint_in}}; assign a[359:357] = r_a_357;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [41:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {42{lint_in}}; assign b[86:45] = r_b_45;
    reg [41:0] r_b_90; always @(posedge lint_clk) r_b_90 <= {42{lint_in}}; assign b[131:90] = r_b_90;
    reg [41:0] r_b_135; always @(posedge lint_clk) r_b_135 <= {42{lint_in}}; assign b[176:135] = r_b_135;
    reg [41:0] r_b_180; always @(posedge lint_clk) r_b_180 <= {42{lint_in}}; assign b[221:180] = r_b_180;
    reg [41:0] r_b_225; always @(posedge lint_clk) r_b_225 <= {42{lint_in}}; assign b[266:225] = r_b_225;
    reg [41:0] r_b_270; always @(posedge lint_clk) r_b_270 <= {42{lint_in}}; assign b[311:270] = r_b_270;
    reg [41:0] r_b_315; always @(posedge lint_clk) r_b_315 <= {42{lint_in}}; assign b[356:315] = r_b_315;
endmodule

module hfd_stn_25 (
    inout wire [359:0] a,
    inout wire [359:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [2:0] r_a_222; always @(posedge lint_clk) r_a_222 <= {3{lint_in}}; assign a[224:222] = r_a_222;
    reg [2:0] r_a_267; always @(posedge lint_clk) r_a_267 <= {3{lint_in}}; assign a[269:267] = r_a_267;
    reg [2:0] r_a_312; always @(posedge lint_clk) r_a_312 <= {3{lint_in}}; assign a[314:312] = r_a_312;
    reg [2:0] r_a_357; always @(posedge lint_clk) r_a_357 <= {3{lint_in}}; assign a[359:357] = r_a_357;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [41:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {42{lint_in}}; assign b[86:45] = r_b_45;
    reg [41:0] r_b_90; always @(posedge lint_clk) r_b_90 <= {42{lint_in}}; assign b[131:90] = r_b_90;
    reg [41:0] r_b_135; always @(posedge lint_clk) r_b_135 <= {42{lint_in}}; assign b[176:135] = r_b_135;
    reg [41:0] r_b_180; always @(posedge lint_clk) r_b_180 <= {42{lint_in}}; assign b[221:180] = r_b_180;
    reg [41:0] r_b_225; always @(posedge lint_clk) r_b_225 <= {42{lint_in}}; assign b[266:225] = r_b_225;
    reg [41:0] r_b_270; always @(posedge lint_clk) r_b_270 <= {42{lint_in}}; assign b[311:270] = r_b_270;
    reg [41:0] r_b_315; always @(posedge lint_clk) r_b_315 <= {42{lint_in}}; assign b[356:315] = r_b_315;
endmodule

module hfd_stn_26 (
    inout wire [359:0] a,
    inout wire [359:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [2:0] r_a_222; always @(posedge lint_clk) r_a_222 <= {3{lint_in}}; assign a[224:222] = r_a_222;
    reg [2:0] r_a_267; always @(posedge lint_clk) r_a_267 <= {3{lint_in}}; assign a[269:267] = r_a_267;
    reg [2:0] r_a_312; always @(posedge lint_clk) r_a_312 <= {3{lint_in}}; assign a[314:312] = r_a_312;
    reg [2:0] r_a_357; always @(posedge lint_clk) r_a_357 <= {3{lint_in}}; assign a[359:357] = r_a_357;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [41:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {42{lint_in}}; assign b[86:45] = r_b_45;
    reg [41:0] r_b_90; always @(posedge lint_clk) r_b_90 <= {42{lint_in}}; assign b[131:90] = r_b_90;
    reg [41:0] r_b_135; always @(posedge lint_clk) r_b_135 <= {42{lint_in}}; assign b[176:135] = r_b_135;
    reg [41:0] r_b_180; always @(posedge lint_clk) r_b_180 <= {42{lint_in}}; assign b[221:180] = r_b_180;
    reg [41:0] r_b_225; always @(posedge lint_clk) r_b_225 <= {42{lint_in}}; assign b[266:225] = r_b_225;
    reg [41:0] r_b_270; always @(posedge lint_clk) r_b_270 <= {42{lint_in}}; assign b[311:270] = r_b_270;
    reg [41:0] r_b_315; always @(posedge lint_clk) r_b_315 <= {42{lint_in}}; assign b[356:315] = r_b_315;
endmodule

module hfd_stn_27 (
    inout wire [359:0] a,
    inout wire [359:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [2:0] r_a_222; always @(posedge lint_clk) r_a_222 <= {3{lint_in}}; assign a[224:222] = r_a_222;
    reg [2:0] r_a_267; always @(posedge lint_clk) r_a_267 <= {3{lint_in}}; assign a[269:267] = r_a_267;
    reg [2:0] r_a_312; always @(posedge lint_clk) r_a_312 <= {3{lint_in}}; assign a[314:312] = r_a_312;
    reg [2:0] r_a_357; always @(posedge lint_clk) r_a_357 <= {3{lint_in}}; assign a[359:357] = r_a_357;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [41:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {42{lint_in}}; assign b[86:45] = r_b_45;
    reg [41:0] r_b_90; always @(posedge lint_clk) r_b_90 <= {42{lint_in}}; assign b[131:90] = r_b_90;
    reg [41:0] r_b_135; always @(posedge lint_clk) r_b_135 <= {42{lint_in}}; assign b[176:135] = r_b_135;
    reg [41:0] r_b_180; always @(posedge lint_clk) r_b_180 <= {42{lint_in}}; assign b[221:180] = r_b_180;
    reg [41:0] r_b_225; always @(posedge lint_clk) r_b_225 <= {42{lint_in}}; assign b[266:225] = r_b_225;
    reg [41:0] r_b_270; always @(posedge lint_clk) r_b_270 <= {42{lint_in}}; assign b[311:270] = r_b_270;
    reg [41:0] r_b_315; always @(posedge lint_clk) r_b_315 <= {42{lint_in}}; assign b[356:315] = r_b_315;
endmodule

module hfd_stn_3 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_30 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_31 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_32 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_33 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_34 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_35 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_36 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_37 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_38 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_39 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_4 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_40 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_41 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_42 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_43 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_44 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_45 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_46 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_47 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_48 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_49 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_5 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_50 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_51 (
    input wire [2062:0] a,
    output wire [2062:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2063{lint_in}}; assign b[2062:0] = r_b_0;
endmodule

module hfd_stn_52 (
    input wire [2062:0] a,
    output wire [2062:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2063{lint_in}}; assign b[2062:0] = r_b_0;
endmodule

module hfd_stn_53 (
    input wire [2062:0] a,
    output wire [2062:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2063{lint_in}}; assign b[2062:0] = r_b_0;
endmodule

module hfd_stn_54 (
    input wire [2062:0] a,
    output wire [2062:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2063{lint_in}}; assign b[2062:0] = r_b_0;
endmodule

module hfd_stn_6 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_63 (
    input wire [2159:0] a,
    output wire [2159:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2159:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2160{lint_in}}; assign b[2159:0] = r_b_0;
endmodule

module hfd_stn_64 (
    input wire [2159:0] a,
    output wire [2159:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2159:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2160{lint_in}}; assign b[2159:0] = r_b_0;
endmodule

module hfd_stn_65 (
    input wire [2159:0] a,
    output wire [2159:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2159:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2160{lint_in}}; assign b[2159:0] = r_b_0;
endmodule

module hfd_stn_66 (
    input wire [2159:0] a,
    output wire [2159:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2159:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2160{lint_in}}; assign b[2159:0] = r_b_0;
endmodule

module hfd_stn_67 (
    inout wire [359:0] a,
    inout wire [359:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [2:0] r_a_222; always @(posedge lint_clk) r_a_222 <= {3{lint_in}}; assign a[224:222] = r_a_222;
    reg [2:0] r_a_267; always @(posedge lint_clk) r_a_267 <= {3{lint_in}}; assign a[269:267] = r_a_267;
    reg [2:0] r_a_312; always @(posedge lint_clk) r_a_312 <= {3{lint_in}}; assign a[314:312] = r_a_312;
    reg [2:0] r_a_357; always @(posedge lint_clk) r_a_357 <= {3{lint_in}}; assign a[359:357] = r_a_357;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [41:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {42{lint_in}}; assign b[86:45] = r_b_45;
    reg [41:0] r_b_90; always @(posedge lint_clk) r_b_90 <= {42{lint_in}}; assign b[131:90] = r_b_90;
    reg [41:0] r_b_135; always @(posedge lint_clk) r_b_135 <= {42{lint_in}}; assign b[176:135] = r_b_135;
    reg [41:0] r_b_180; always @(posedge lint_clk) r_b_180 <= {42{lint_in}}; assign b[221:180] = r_b_180;
    reg [41:0] r_b_225; always @(posedge lint_clk) r_b_225 <= {42{lint_in}}; assign b[266:225] = r_b_225;
    reg [41:0] r_b_270; always @(posedge lint_clk) r_b_270 <= {42{lint_in}}; assign b[311:270] = r_b_270;
    reg [41:0] r_b_315; always @(posedge lint_clk) r_b_315 <= {42{lint_in}}; assign b[356:315] = r_b_315;
endmodule

module hfd_stn_68 (
    inout wire [359:0] a,
    inout wire [359:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [2:0] r_a_222; always @(posedge lint_clk) r_a_222 <= {3{lint_in}}; assign a[224:222] = r_a_222;
    reg [2:0] r_a_267; always @(posedge lint_clk) r_a_267 <= {3{lint_in}}; assign a[269:267] = r_a_267;
    reg [2:0] r_a_312; always @(posedge lint_clk) r_a_312 <= {3{lint_in}}; assign a[314:312] = r_a_312;
    reg [2:0] r_a_357; always @(posedge lint_clk) r_a_357 <= {3{lint_in}}; assign a[359:357] = r_a_357;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [41:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {42{lint_in}}; assign b[86:45] = r_b_45;
    reg [41:0] r_b_90; always @(posedge lint_clk) r_b_90 <= {42{lint_in}}; assign b[131:90] = r_b_90;
    reg [41:0] r_b_135; always @(posedge lint_clk) r_b_135 <= {42{lint_in}}; assign b[176:135] = r_b_135;
    reg [41:0] r_b_180; always @(posedge lint_clk) r_b_180 <= {42{lint_in}}; assign b[221:180] = r_b_180;
    reg [41:0] r_b_225; always @(posedge lint_clk) r_b_225 <= {42{lint_in}}; assign b[266:225] = r_b_225;
    reg [41:0] r_b_270; always @(posedge lint_clk) r_b_270 <= {42{lint_in}}; assign b[311:270] = r_b_270;
    reg [41:0] r_b_315; always @(posedge lint_clk) r_b_315 <= {42{lint_in}}; assign b[356:315] = r_b_315;
endmodule

module hfd_stn_69 (
    inout wire [359:0] a,
    inout wire [359:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [2:0] r_a_222; always @(posedge lint_clk) r_a_222 <= {3{lint_in}}; assign a[224:222] = r_a_222;
    reg [2:0] r_a_267; always @(posedge lint_clk) r_a_267 <= {3{lint_in}}; assign a[269:267] = r_a_267;
    reg [2:0] r_a_312; always @(posedge lint_clk) r_a_312 <= {3{lint_in}}; assign a[314:312] = r_a_312;
    reg [2:0] r_a_357; always @(posedge lint_clk) r_a_357 <= {3{lint_in}}; assign a[359:357] = r_a_357;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [41:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {42{lint_in}}; assign b[86:45] = r_b_45;
    reg [41:0] r_b_90; always @(posedge lint_clk) r_b_90 <= {42{lint_in}}; assign b[131:90] = r_b_90;
    reg [41:0] r_b_135; always @(posedge lint_clk) r_b_135 <= {42{lint_in}}; assign b[176:135] = r_b_135;
    reg [41:0] r_b_180; always @(posedge lint_clk) r_b_180 <= {42{lint_in}}; assign b[221:180] = r_b_180;
    reg [41:0] r_b_225; always @(posedge lint_clk) r_b_225 <= {42{lint_in}}; assign b[266:225] = r_b_225;
    reg [41:0] r_b_270; always @(posedge lint_clk) r_b_270 <= {42{lint_in}}; assign b[311:270] = r_b_270;
    reg [41:0] r_b_315; always @(posedge lint_clk) r_b_315 <= {42{lint_in}}; assign b[356:315] = r_b_315;
endmodule

module hfd_stn_7 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_70 (
    inout wire [359:0] a,
    inout wire [359:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a, ^b};
    reg [2:0] r_a_42; always @(posedge lint_clk) r_a_42 <= {3{lint_in}}; assign a[44:42] = r_a_42;
    reg [2:0] r_a_87; always @(posedge lint_clk) r_a_87 <= {3{lint_in}}; assign a[89:87] = r_a_87;
    reg [2:0] r_a_132; always @(posedge lint_clk) r_a_132 <= {3{lint_in}}; assign a[134:132] = r_a_132;
    reg [2:0] r_a_177; always @(posedge lint_clk) r_a_177 <= {3{lint_in}}; assign a[179:177] = r_a_177;
    reg [2:0] r_a_222; always @(posedge lint_clk) r_a_222 <= {3{lint_in}}; assign a[224:222] = r_a_222;
    reg [2:0] r_a_267; always @(posedge lint_clk) r_a_267 <= {3{lint_in}}; assign a[269:267] = r_a_267;
    reg [2:0] r_a_312; always @(posedge lint_clk) r_a_312 <= {3{lint_in}}; assign a[314:312] = r_a_312;
    reg [2:0] r_a_357; always @(posedge lint_clk) r_a_357 <= {3{lint_in}}; assign a[359:357] = r_a_357;
    reg [41:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {42{lint_in}}; assign b[41:0] = r_b_0;
    reg [41:0] r_b_45; always @(posedge lint_clk) r_b_45 <= {42{lint_in}}; assign b[86:45] = r_b_45;
    reg [41:0] r_b_90; always @(posedge lint_clk) r_b_90 <= {42{lint_in}}; assign b[131:90] = r_b_90;
    reg [41:0] r_b_135; always @(posedge lint_clk) r_b_135 <= {42{lint_in}}; assign b[176:135] = r_b_135;
    reg [41:0] r_b_180; always @(posedge lint_clk) r_b_180 <= {42{lint_in}}; assign b[221:180] = r_b_180;
    reg [41:0] r_b_225; always @(posedge lint_clk) r_b_225 <= {42{lint_in}}; assign b[266:225] = r_b_225;
    reg [41:0] r_b_270; always @(posedge lint_clk) r_b_270 <= {42{lint_in}}; assign b[311:270] = r_b_270;
    reg [41:0] r_b_315; always @(posedge lint_clk) r_b_315 <= {42{lint_in}}; assign b[356:315] = r_b_315;
endmodule

module hfd_stn_73 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_74 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_75 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_76 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_77 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_78 (
    input wire [127:0] a,
    output wire [127:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [127:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {128{lint_in}}; assign b[127:0] = r_b_0;
endmodule

module hfd_stn_79 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_8 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_80 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_81 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_82 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_83 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_84 (
    input wire [1023:0] a,
    output wire [1023:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1023:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1024{lint_in}}; assign b[1023:0] = r_b_0;
endmodule

module hfd_stn_85 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_86 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_87 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_88 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_89 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_9 (
    input wire [2062:0] a,
    output wire [2062:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2063{lint_in}}; assign b[2062:0] = r_b_0;
endmodule

module hfd_stn_90 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_91 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_92 (
    input wire [1098:0] a,
    output wire [1098:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [1098:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {1099{lint_in}}; assign b[1098:0] = r_b_0;
endmodule

module hfd_stn_93 (
    input wire [2062:0] a,
    output wire [2062:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2063{lint_in}}; assign b[2062:0] = r_b_0;
endmodule

module hfd_stn_94 (
    input wire [2062:0] a,
    output wire [2062:0] b
);
    wire lint_clk = 1'b0;  // NO CLOCK PORT ON THIS ABSTRACT
    wire lint_in = ^{^a};
    reg [2062:0] r_b_0; always @(posedge lint_clk) r_b_0 <= {2063{lint_in}}; assign b[2062:0] = r_b_0;
endmodule

module hfd_su (
    input wire [1023:0] a,
    input wire [0:0] ck,
    input wire [63:0] f_cmdproc,
    input wire [1023:0] f_coll,
    input wire [511:0] f_quant,
    input wire [1023:0] f_su_ew,
    input wire [1023:0] f_su_ns,
    input wire [2047:0] f_vm,
    input wire [2159:0] r,
    output wire [1023:0] t_coll,
    output wire [255:0] t_router,
    output wire [1023:0] t_sfu,
    output wire [1023:0] t_su_ew,
    output wire [1023:0] t_su_ns,
    output wire [2047:0] t_vm
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^a, ^ck, ^f_cmdproc, ^f_coll, ^f_quant, ^f_su_ew, ^f_su_ns, ^f_vm, ^r};
    reg [1023:0] r_t_coll_0; always @(posedge lint_clk) r_t_coll_0 <= {1024{lint_in}}; assign t_coll[1023:0] = r_t_coll_0;
    reg [255:0] r_t_router_0; always @(posedge lint_clk) r_t_router_0 <= {256{lint_in}}; assign t_router[255:0] = r_t_router_0;
    reg [1023:0] r_t_sfu_0; always @(posedge lint_clk) r_t_sfu_0 <= {1024{lint_in}}; assign t_sfu[1023:0] = r_t_sfu_0;
    reg [1023:0] r_t_su_ew_0; always @(posedge lint_clk) r_t_su_ew_0 <= {1024{lint_in}}; assign t_su_ew[1023:0] = r_t_su_ew_0;
    reg [1023:0] r_t_su_ns_0; always @(posedge lint_clk) r_t_su_ns_0 <= {1024{lint_in}}; assign t_su_ns[1023:0] = r_t_su_ns_0;
    reg [2047:0] r_t_vm_0; always @(posedge lint_clk) r_t_vm_0 <= {2048{lint_in}}; assign t_vm[2047:0] = r_t_vm_0;
endmodule

module hfd_svc_NE (
    input wire [0:0] ck,
    input wire [127:0] e,
    output wire [1023:0] ik,
    output wire [1023:0] kv,
    output wire [1098:0] lsm24,
    output wire [1098:0] lsm25,
    output wire [1098:0] lsm26,
    output wire [1098:0] lsm27,
    output wire [1098:0] lsm28,
    output wire [1098:0] lsm29,
    output wire [1098:0] lsm30,
    output wire [1098:0] lsm31,
    inout wire [22237:0] phy,
    inout wire [43:0] qsm24,
    inout wire [43:0] qsm25,
    inout wire [43:0] qsm26,
    inout wire [43:0] qsm27,
    inout wire [43:0] qsm28,
    inout wire [43:0] qsm29,
    inout wire [43:0] qsm30,
    inout wire [43:0] qsm31
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^e, ^phy, ^qsm24, ^qsm25, ^qsm26, ^qsm27, ^qsm28, ^qsm29, ^qsm30, ^qsm31};
    reg [1023:0] r_ik_0; always @(posedge lint_clk) r_ik_0 <= {1024{lint_in}}; assign ik[1023:0] = r_ik_0;
    reg [1023:0] r_kv_0; always @(posedge lint_clk) r_kv_0 <= {1024{lint_in}}; assign kv[1023:0] = r_kv_0;
    reg [1098:0] r_lsm24_0; always @(posedge lint_clk) r_lsm24_0 <= {1099{lint_in}}; assign lsm24[1098:0] = r_lsm24_0;
    reg [1098:0] r_lsm25_0; always @(posedge lint_clk) r_lsm25_0 <= {1099{lint_in}}; assign lsm25[1098:0] = r_lsm25_0;
    reg [1098:0] r_lsm26_0; always @(posedge lint_clk) r_lsm26_0 <= {1099{lint_in}}; assign lsm26[1098:0] = r_lsm26_0;
    reg [1098:0] r_lsm27_0; always @(posedge lint_clk) r_lsm27_0 <= {1099{lint_in}}; assign lsm27[1098:0] = r_lsm27_0;
    reg [1098:0] r_lsm28_0; always @(posedge lint_clk) r_lsm28_0 <= {1099{lint_in}}; assign lsm28[1098:0] = r_lsm28_0;
    reg [1098:0] r_lsm29_0; always @(posedge lint_clk) r_lsm29_0 <= {1099{lint_in}}; assign lsm29[1098:0] = r_lsm29_0;
    reg [1098:0] r_lsm30_0; always @(posedge lint_clk) r_lsm30_0 <= {1099{lint_in}}; assign lsm30[1098:0] = r_lsm30_0;
    reg [1098:0] r_lsm31_0; always @(posedge lint_clk) r_lsm31_0 <= {1099{lint_in}}; assign lsm31[1098:0] = r_lsm31_0;
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
    reg [0:0] r_phy_3626; always @(posedge lint_clk) r_phy_3626 <= {1{lint_in}}; assign phy[3626:3626] = r_phy_3626;
    reg [339:0] r_phy_3628; always @(posedge lint_clk) r_phy_3628 <= {340{lint_in}}; assign phy[3967:3628] = r_phy_3628;
    reg [0:0] r_phy_3970; always @(posedge lint_clk) r_phy_3970 <= {1{lint_in}}; assign phy[3970:3970] = r_phy_3970;
    reg [0:0] r_phy_4250; always @(posedge lint_clk) r_phy_4250 <= {1{lint_in}}; assign phy[4250:4250] = r_phy_4250;
    reg [0:0] r_phy_4522; always @(posedge lint_clk) r_phy_4522 <= {1{lint_in}}; assign phy[4522:4522] = r_phy_4522;
    reg [339:0] r_phy_4524; always @(posedge lint_clk) r_phy_4524 <= {340{lint_in}}; assign phy[4863:4524] = r_phy_4524;
    reg [0:0] r_phy_4866; always @(posedge lint_clk) r_phy_4866 <= {1{lint_in}}; assign phy[4866:4866] = r_phy_4866;
    reg [0:0] r_phy_5146; always @(posedge lint_clk) r_phy_5146 <= {1{lint_in}}; assign phy[5146:5146] = r_phy_5146;
    reg [0:0] r_phy_5418; always @(posedge lint_clk) r_phy_5418 <= {1{lint_in}}; assign phy[5418:5418] = r_phy_5418;
    reg [339:0] r_phy_5420; always @(posedge lint_clk) r_phy_5420 <= {340{lint_in}}; assign phy[5759:5420] = r_phy_5420;
    reg [0:0] r_phy_5762; always @(posedge lint_clk) r_phy_5762 <= {1{lint_in}}; assign phy[5762:5762] = r_phy_5762;
    reg [0:0] r_phy_6042; always @(posedge lint_clk) r_phy_6042 <= {1{lint_in}}; assign phy[6042:6042] = r_phy_6042;
    reg [0:0] r_phy_6314; always @(posedge lint_clk) r_phy_6314 <= {1{lint_in}}; assign phy[6314:6314] = r_phy_6314;
    reg [339:0] r_phy_6316; always @(posedge lint_clk) r_phy_6316 <= {340{lint_in}}; assign phy[6655:6316] = r_phy_6316;
    reg [0:0] r_phy_6658; always @(posedge lint_clk) r_phy_6658 <= {1{lint_in}}; assign phy[6658:6658] = r_phy_6658;
    reg [0:0] r_phy_6938; always @(posedge lint_clk) r_phy_6938 <= {1{lint_in}}; assign phy[6938:6938] = r_phy_6938;
    reg [0:0] r_phy_7210; always @(posedge lint_clk) r_phy_7210 <= {1{lint_in}}; assign phy[7210:7210] = r_phy_7210;
    reg [339:0] r_phy_7212; always @(posedge lint_clk) r_phy_7212 <= {340{lint_in}}; assign phy[7551:7212] = r_phy_7212;
    reg [0:0] r_phy_7554; always @(posedge lint_clk) r_phy_7554 <= {1{lint_in}}; assign phy[7554:7554] = r_phy_7554;
    reg [0:0] r_phy_7832; always @(posedge lint_clk) r_phy_7832 <= {1{lint_in}}; assign phy[7832:7832] = r_phy_7832;
    reg [339:0] r_phy_7834; always @(posedge lint_clk) r_phy_7834 <= {340{lint_in}}; assign phy[8173:7834] = r_phy_7834;
    reg [0:0] r_phy_8176; always @(posedge lint_clk) r_phy_8176 <= {1{lint_in}}; assign phy[8176:8176] = r_phy_8176;
    reg [0:0] r_phy_8454; always @(posedge lint_clk) r_phy_8454 <= {1{lint_in}}; assign phy[8454:8454] = r_phy_8454;
    reg [339:0] r_phy_8456; always @(posedge lint_clk) r_phy_8456 <= {340{lint_in}}; assign phy[8795:8456] = r_phy_8456;
    reg [0:0] r_phy_8798; always @(posedge lint_clk) r_phy_8798 <= {1{lint_in}}; assign phy[8798:8798] = r_phy_8798;
    reg [0:0] r_phy_9076; always @(posedge lint_clk) r_phy_9076 <= {1{lint_in}}; assign phy[9076:9076] = r_phy_9076;
    reg [339:0] r_phy_9078; always @(posedge lint_clk) r_phy_9078 <= {340{lint_in}}; assign phy[9417:9078] = r_phy_9078;
    reg [0:0] r_phy_9420; always @(posedge lint_clk) r_phy_9420 <= {1{lint_in}}; assign phy[9420:9420] = r_phy_9420;
    reg [0:0] r_phy_9698; always @(posedge lint_clk) r_phy_9698 <= {1{lint_in}}; assign phy[9698:9698] = r_phy_9698;
    reg [339:0] r_phy_9700; always @(posedge lint_clk) r_phy_9700 <= {340{lint_in}}; assign phy[10039:9700] = r_phy_9700;
    reg [0:0] r_phy_10042; always @(posedge lint_clk) r_phy_10042 <= {1{lint_in}}; assign phy[10042:10042] = r_phy_10042;
    reg [0:0] r_phy_10320; always @(posedge lint_clk) r_phy_10320 <= {1{lint_in}}; assign phy[10320:10320] = r_phy_10320;
    reg [339:0] r_phy_10322; always @(posedge lint_clk) r_phy_10322 <= {340{lint_in}}; assign phy[10661:10322] = r_phy_10322;
    reg [0:0] r_phy_10664; always @(posedge lint_clk) r_phy_10664 <= {1{lint_in}}; assign phy[10664:10664] = r_phy_10664;
    reg [0:0] r_phy_10942; always @(posedge lint_clk) r_phy_10942 <= {1{lint_in}}; assign phy[10942:10942] = r_phy_10942;
    reg [339:0] r_phy_10944; always @(posedge lint_clk) r_phy_10944 <= {340{lint_in}}; assign phy[11283:10944] = r_phy_10944;
    reg [0:0] r_phy_11286; always @(posedge lint_clk) r_phy_11286 <= {1{lint_in}}; assign phy[11286:11286] = r_phy_11286;
    reg [0:0] r_phy_11564; always @(posedge lint_clk) r_phy_11564 <= {1{lint_in}}; assign phy[11564:11564] = r_phy_11564;
    reg [339:0] r_phy_11566; always @(posedge lint_clk) r_phy_11566 <= {340{lint_in}}; assign phy[11905:11566] = r_phy_11566;
    reg [0:0] r_phy_11908; always @(posedge lint_clk) r_phy_11908 <= {1{lint_in}}; assign phy[11908:11908] = r_phy_11908;
    reg [0:0] r_phy_12186; always @(posedge lint_clk) r_phy_12186 <= {1{lint_in}}; assign phy[12186:12186] = r_phy_12186;
    reg [339:0] r_phy_12188; always @(posedge lint_clk) r_phy_12188 <= {340{lint_in}}; assign phy[12527:12188] = r_phy_12188;
    reg [0:0] r_phy_12530; always @(posedge lint_clk) r_phy_12530 <= {1{lint_in}}; assign phy[12530:12530] = r_phy_12530;
    reg [1:0] r_phy_12808; always @(posedge lint_clk) r_phy_12808 <= {2{lint_in}}; assign phy[12809:12808] = r_phy_12808;
    reg [0:0] r_phy_12908; always @(posedge lint_clk) r_phy_12908 <= {1{lint_in}}; assign phy[12908:12908] = r_phy_12908;
    reg [339:0] r_phy_12910; always @(posedge lint_clk) r_phy_12910 <= {340{lint_in}}; assign phy[13249:12910] = r_phy_12910;
    reg [0:0] r_phy_13252; always @(posedge lint_clk) r_phy_13252 <= {1{lint_in}}; assign phy[13252:13252] = r_phy_13252;
    reg [0:0] r_phy_13530; always @(posedge lint_clk) r_phy_13530 <= {1{lint_in}}; assign phy[13530:13530] = r_phy_13530;
    reg [339:0] r_phy_13532; always @(posedge lint_clk) r_phy_13532 <= {340{lint_in}}; assign phy[13871:13532] = r_phy_13532;
    reg [0:0] r_phy_13874; always @(posedge lint_clk) r_phy_13874 <= {1{lint_in}}; assign phy[13874:13874] = r_phy_13874;
    reg [0:0] r_phy_14152; always @(posedge lint_clk) r_phy_14152 <= {1{lint_in}}; assign phy[14152:14152] = r_phy_14152;
    reg [339:0] r_phy_14154; always @(posedge lint_clk) r_phy_14154 <= {340{lint_in}}; assign phy[14493:14154] = r_phy_14154;
    reg [0:0] r_phy_14496; always @(posedge lint_clk) r_phy_14496 <= {1{lint_in}}; assign phy[14496:14496] = r_phy_14496;
    reg [0:0] r_phy_14774; always @(posedge lint_clk) r_phy_14774 <= {1{lint_in}}; assign phy[14774:14774] = r_phy_14774;
    reg [339:0] r_phy_14776; always @(posedge lint_clk) r_phy_14776 <= {340{lint_in}}; assign phy[15115:14776] = r_phy_14776;
    reg [0:0] r_phy_15118; always @(posedge lint_clk) r_phy_15118 <= {1{lint_in}}; assign phy[15118:15118] = r_phy_15118;
    reg [0:0] r_phy_15396; always @(posedge lint_clk) r_phy_15396 <= {1{lint_in}}; assign phy[15396:15396] = r_phy_15396;
    reg [339:0] r_phy_15398; always @(posedge lint_clk) r_phy_15398 <= {340{lint_in}}; assign phy[15737:15398] = r_phy_15398;
    reg [0:0] r_phy_15740; always @(posedge lint_clk) r_phy_15740 <= {1{lint_in}}; assign phy[15740:15740] = r_phy_15740;
    reg [0:0] r_phy_16018; always @(posedge lint_clk) r_phy_16018 <= {1{lint_in}}; assign phy[16018:16018] = r_phy_16018;
    reg [339:0] r_phy_16020; always @(posedge lint_clk) r_phy_16020 <= {340{lint_in}}; assign phy[16359:16020] = r_phy_16020;
    reg [0:0] r_phy_16362; always @(posedge lint_clk) r_phy_16362 <= {1{lint_in}}; assign phy[16362:16362] = r_phy_16362;
    reg [0:0] r_phy_16640; always @(posedge lint_clk) r_phy_16640 <= {1{lint_in}}; assign phy[16640:16640] = r_phy_16640;
    reg [339:0] r_phy_16642; always @(posedge lint_clk) r_phy_16642 <= {340{lint_in}}; assign phy[16981:16642] = r_phy_16642;
    reg [0:0] r_phy_16984; always @(posedge lint_clk) r_phy_16984 <= {1{lint_in}}; assign phy[16984:16984] = r_phy_16984;
    reg [0:0] r_phy_17262; always @(posedge lint_clk) r_phy_17262 <= {1{lint_in}}; assign phy[17262:17262] = r_phy_17262;
    reg [339:0] r_phy_17264; always @(posedge lint_clk) r_phy_17264 <= {340{lint_in}}; assign phy[17603:17264] = r_phy_17264;
    reg [0:0] r_phy_17606; always @(posedge lint_clk) r_phy_17606 <= {1{lint_in}}; assign phy[17606:17606] = r_phy_17606;
    reg [0:0] r_phy_17884; always @(posedge lint_clk) r_phy_17884 <= {1{lint_in}}; assign phy[17884:17884] = r_phy_17884;
    reg [339:0] r_phy_17886; always @(posedge lint_clk) r_phy_17886 <= {340{lint_in}}; assign phy[18225:17886] = r_phy_17886;
    reg [0:0] r_phy_18228; always @(posedge lint_clk) r_phy_18228 <= {1{lint_in}}; assign phy[18228:18228] = r_phy_18228;
    reg [0:0] r_phy_18506; always @(posedge lint_clk) r_phy_18506 <= {1{lint_in}}; assign phy[18506:18506] = r_phy_18506;
    reg [339:0] r_phy_18508; always @(posedge lint_clk) r_phy_18508 <= {340{lint_in}}; assign phy[18847:18508] = r_phy_18508;
    reg [0:0] r_phy_18850; always @(posedge lint_clk) r_phy_18850 <= {1{lint_in}}; assign phy[18850:18850] = r_phy_18850;
    reg [0:0] r_phy_19128; always @(posedge lint_clk) r_phy_19128 <= {1{lint_in}}; assign phy[19128:19128] = r_phy_19128;
    reg [339:0] r_phy_19130; always @(posedge lint_clk) r_phy_19130 <= {340{lint_in}}; assign phy[19469:19130] = r_phy_19130;
    reg [0:0] r_phy_19472; always @(posedge lint_clk) r_phy_19472 <= {1{lint_in}}; assign phy[19472:19472] = r_phy_19472;
    reg [0:0] r_phy_19750; always @(posedge lint_clk) r_phy_19750 <= {1{lint_in}}; assign phy[19750:19750] = r_phy_19750;
    reg [339:0] r_phy_19752; always @(posedge lint_clk) r_phy_19752 <= {340{lint_in}}; assign phy[20091:19752] = r_phy_19752;
    reg [0:0] r_phy_20094; always @(posedge lint_clk) r_phy_20094 <= {1{lint_in}}; assign phy[20094:20094] = r_phy_20094;
    reg [0:0] r_phy_20372; always @(posedge lint_clk) r_phy_20372 <= {1{lint_in}}; assign phy[20372:20372] = r_phy_20372;
    reg [339:0] r_phy_20374; always @(posedge lint_clk) r_phy_20374 <= {340{lint_in}}; assign phy[20713:20374] = r_phy_20374;
    reg [0:0] r_phy_20716; always @(posedge lint_clk) r_phy_20716 <= {1{lint_in}}; assign phy[20716:20716] = r_phy_20716;
    reg [0:0] r_phy_20994; always @(posedge lint_clk) r_phy_20994 <= {1{lint_in}}; assign phy[20994:20994] = r_phy_20994;
    reg [339:0] r_phy_20996; always @(posedge lint_clk) r_phy_20996 <= {340{lint_in}}; assign phy[21335:20996] = r_phy_20996;
    reg [0:0] r_phy_21338; always @(posedge lint_clk) r_phy_21338 <= {1{lint_in}}; assign phy[21338:21338] = r_phy_21338;
    reg [0:0] r_phy_21616; always @(posedge lint_clk) r_phy_21616 <= {1{lint_in}}; assign phy[21616:21616] = r_phy_21616;
    reg [339:0] r_phy_21618; always @(posedge lint_clk) r_phy_21618 <= {340{lint_in}}; assign phy[21957:21618] = r_phy_21618;
    reg [0:0] r_phy_21960; always @(posedge lint_clk) r_phy_21960 <= {1{lint_in}}; assign phy[21960:21960] = r_phy_21960;
    reg [0:0] r_qsm24_43; always @(posedge lint_clk) r_qsm24_43 <= {1{lint_in}}; assign qsm24[43:43] = r_qsm24_43;
    reg [0:0] r_qsm25_43; always @(posedge lint_clk) r_qsm25_43 <= {1{lint_in}}; assign qsm25[43:43] = r_qsm25_43;
    reg [0:0] r_qsm26_43; always @(posedge lint_clk) r_qsm26_43 <= {1{lint_in}}; assign qsm26[43:43] = r_qsm26_43;
    reg [0:0] r_qsm27_43; always @(posedge lint_clk) r_qsm27_43 <= {1{lint_in}}; assign qsm27[43:43] = r_qsm27_43;
    reg [0:0] r_qsm28_43; always @(posedge lint_clk) r_qsm28_43 <= {1{lint_in}}; assign qsm28[43:43] = r_qsm28_43;
    reg [0:0] r_qsm29_43; always @(posedge lint_clk) r_qsm29_43 <= {1{lint_in}}; assign qsm29[43:43] = r_qsm29_43;
    reg [0:0] r_qsm30_43; always @(posedge lint_clk) r_qsm30_43 <= {1{lint_in}}; assign qsm30[43:43] = r_qsm30_43;
    reg [0:0] r_qsm31_43; always @(posedge lint_clk) r_qsm31_43 <= {1{lint_in}}; assign qsm31[43:43] = r_qsm31_43;
endmodule

module hfd_svc_NW (
    input wire [0:0] ck,
    input wire [127:0] e,
    output wire [1023:0] ik,
    output wire [1023:0] kv,
    output wire [1098:0] lsm16,
    output wire [1098:0] lsm17,
    output wire [1098:0] lsm18,
    output wire [1098:0] lsm19,
    output wire [1098:0] lsm20,
    output wire [1098:0] lsm21,
    output wire [1098:0] lsm22,
    output wire [1098:0] lsm23,
    inout wire [22237:0] phy,
    inout wire [43:0] qsm16,
    inout wire [43:0] qsm17,
    inout wire [43:0] qsm18,
    inout wire [43:0] qsm19,
    inout wire [43:0] qsm20,
    inout wire [43:0] qsm21,
    inout wire [43:0] qsm22,
    inout wire [43:0] qsm23
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^e, ^phy, ^qsm16, ^qsm17, ^qsm18, ^qsm19, ^qsm20, ^qsm21, ^qsm22, ^qsm23};
    reg [1023:0] r_ik_0; always @(posedge lint_clk) r_ik_0 <= {1024{lint_in}}; assign ik[1023:0] = r_ik_0;
    reg [1023:0] r_kv_0; always @(posedge lint_clk) r_kv_0 <= {1024{lint_in}}; assign kv[1023:0] = r_kv_0;
    reg [1098:0] r_lsm16_0; always @(posedge lint_clk) r_lsm16_0 <= {1099{lint_in}}; assign lsm16[1098:0] = r_lsm16_0;
    reg [1098:0] r_lsm17_0; always @(posedge lint_clk) r_lsm17_0 <= {1099{lint_in}}; assign lsm17[1098:0] = r_lsm17_0;
    reg [1098:0] r_lsm18_0; always @(posedge lint_clk) r_lsm18_0 <= {1099{lint_in}}; assign lsm18[1098:0] = r_lsm18_0;
    reg [1098:0] r_lsm19_0; always @(posedge lint_clk) r_lsm19_0 <= {1099{lint_in}}; assign lsm19[1098:0] = r_lsm19_0;
    reg [1098:0] r_lsm20_0; always @(posedge lint_clk) r_lsm20_0 <= {1099{lint_in}}; assign lsm20[1098:0] = r_lsm20_0;
    reg [1098:0] r_lsm21_0; always @(posedge lint_clk) r_lsm21_0 <= {1099{lint_in}}; assign lsm21[1098:0] = r_lsm21_0;
    reg [1098:0] r_lsm22_0; always @(posedge lint_clk) r_lsm22_0 <= {1099{lint_in}}; assign lsm22[1098:0] = r_lsm22_0;
    reg [1098:0] r_lsm23_0; always @(posedge lint_clk) r_lsm23_0 <= {1099{lint_in}}; assign lsm23[1098:0] = r_lsm23_0;
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
    reg [0:0] r_phy_3626; always @(posedge lint_clk) r_phy_3626 <= {1{lint_in}}; assign phy[3626:3626] = r_phy_3626;
    reg [339:0] r_phy_3628; always @(posedge lint_clk) r_phy_3628 <= {340{lint_in}}; assign phy[3967:3628] = r_phy_3628;
    reg [0:0] r_phy_3970; always @(posedge lint_clk) r_phy_3970 <= {1{lint_in}}; assign phy[3970:3970] = r_phy_3970;
    reg [0:0] r_phy_4250; always @(posedge lint_clk) r_phy_4250 <= {1{lint_in}}; assign phy[4250:4250] = r_phy_4250;
    reg [0:0] r_phy_4522; always @(posedge lint_clk) r_phy_4522 <= {1{lint_in}}; assign phy[4522:4522] = r_phy_4522;
    reg [339:0] r_phy_4524; always @(posedge lint_clk) r_phy_4524 <= {340{lint_in}}; assign phy[4863:4524] = r_phy_4524;
    reg [0:0] r_phy_4866; always @(posedge lint_clk) r_phy_4866 <= {1{lint_in}}; assign phy[4866:4866] = r_phy_4866;
    reg [0:0] r_phy_5146; always @(posedge lint_clk) r_phy_5146 <= {1{lint_in}}; assign phy[5146:5146] = r_phy_5146;
    reg [0:0] r_phy_5418; always @(posedge lint_clk) r_phy_5418 <= {1{lint_in}}; assign phy[5418:5418] = r_phy_5418;
    reg [339:0] r_phy_5420; always @(posedge lint_clk) r_phy_5420 <= {340{lint_in}}; assign phy[5759:5420] = r_phy_5420;
    reg [0:0] r_phy_5762; always @(posedge lint_clk) r_phy_5762 <= {1{lint_in}}; assign phy[5762:5762] = r_phy_5762;
    reg [0:0] r_phy_6042; always @(posedge lint_clk) r_phy_6042 <= {1{lint_in}}; assign phy[6042:6042] = r_phy_6042;
    reg [0:0] r_phy_6314; always @(posedge lint_clk) r_phy_6314 <= {1{lint_in}}; assign phy[6314:6314] = r_phy_6314;
    reg [339:0] r_phy_6316; always @(posedge lint_clk) r_phy_6316 <= {340{lint_in}}; assign phy[6655:6316] = r_phy_6316;
    reg [0:0] r_phy_6658; always @(posedge lint_clk) r_phy_6658 <= {1{lint_in}}; assign phy[6658:6658] = r_phy_6658;
    reg [0:0] r_phy_6938; always @(posedge lint_clk) r_phy_6938 <= {1{lint_in}}; assign phy[6938:6938] = r_phy_6938;
    reg [0:0] r_phy_7210; always @(posedge lint_clk) r_phy_7210 <= {1{lint_in}}; assign phy[7210:7210] = r_phy_7210;
    reg [339:0] r_phy_7212; always @(posedge lint_clk) r_phy_7212 <= {340{lint_in}}; assign phy[7551:7212] = r_phy_7212;
    reg [0:0] r_phy_7554; always @(posedge lint_clk) r_phy_7554 <= {1{lint_in}}; assign phy[7554:7554] = r_phy_7554;
    reg [0:0] r_phy_7832; always @(posedge lint_clk) r_phy_7832 <= {1{lint_in}}; assign phy[7832:7832] = r_phy_7832;
    reg [339:0] r_phy_7834; always @(posedge lint_clk) r_phy_7834 <= {340{lint_in}}; assign phy[8173:7834] = r_phy_7834;
    reg [0:0] r_phy_8176; always @(posedge lint_clk) r_phy_8176 <= {1{lint_in}}; assign phy[8176:8176] = r_phy_8176;
    reg [0:0] r_phy_8454; always @(posedge lint_clk) r_phy_8454 <= {1{lint_in}}; assign phy[8454:8454] = r_phy_8454;
    reg [339:0] r_phy_8456; always @(posedge lint_clk) r_phy_8456 <= {340{lint_in}}; assign phy[8795:8456] = r_phy_8456;
    reg [0:0] r_phy_8798; always @(posedge lint_clk) r_phy_8798 <= {1{lint_in}}; assign phy[8798:8798] = r_phy_8798;
    reg [0:0] r_phy_9076; always @(posedge lint_clk) r_phy_9076 <= {1{lint_in}}; assign phy[9076:9076] = r_phy_9076;
    reg [339:0] r_phy_9078; always @(posedge lint_clk) r_phy_9078 <= {340{lint_in}}; assign phy[9417:9078] = r_phy_9078;
    reg [0:0] r_phy_9420; always @(posedge lint_clk) r_phy_9420 <= {1{lint_in}}; assign phy[9420:9420] = r_phy_9420;
    reg [0:0] r_phy_9698; always @(posedge lint_clk) r_phy_9698 <= {1{lint_in}}; assign phy[9698:9698] = r_phy_9698;
    reg [339:0] r_phy_9700; always @(posedge lint_clk) r_phy_9700 <= {340{lint_in}}; assign phy[10039:9700] = r_phy_9700;
    reg [0:0] r_phy_10042; always @(posedge lint_clk) r_phy_10042 <= {1{lint_in}}; assign phy[10042:10042] = r_phy_10042;
    reg [0:0] r_phy_10320; always @(posedge lint_clk) r_phy_10320 <= {1{lint_in}}; assign phy[10320:10320] = r_phy_10320;
    reg [339:0] r_phy_10322; always @(posedge lint_clk) r_phy_10322 <= {340{lint_in}}; assign phy[10661:10322] = r_phy_10322;
    reg [0:0] r_phy_10664; always @(posedge lint_clk) r_phy_10664 <= {1{lint_in}}; assign phy[10664:10664] = r_phy_10664;
    reg [0:0] r_phy_10942; always @(posedge lint_clk) r_phy_10942 <= {1{lint_in}}; assign phy[10942:10942] = r_phy_10942;
    reg [339:0] r_phy_10944; always @(posedge lint_clk) r_phy_10944 <= {340{lint_in}}; assign phy[11283:10944] = r_phy_10944;
    reg [0:0] r_phy_11286; always @(posedge lint_clk) r_phy_11286 <= {1{lint_in}}; assign phy[11286:11286] = r_phy_11286;
    reg [0:0] r_phy_11564; always @(posedge lint_clk) r_phy_11564 <= {1{lint_in}}; assign phy[11564:11564] = r_phy_11564;
    reg [339:0] r_phy_11566; always @(posedge lint_clk) r_phy_11566 <= {340{lint_in}}; assign phy[11905:11566] = r_phy_11566;
    reg [0:0] r_phy_11908; always @(posedge lint_clk) r_phy_11908 <= {1{lint_in}}; assign phy[11908:11908] = r_phy_11908;
    reg [0:0] r_phy_12186; always @(posedge lint_clk) r_phy_12186 <= {1{lint_in}}; assign phy[12186:12186] = r_phy_12186;
    reg [339:0] r_phy_12188; always @(posedge lint_clk) r_phy_12188 <= {340{lint_in}}; assign phy[12527:12188] = r_phy_12188;
    reg [0:0] r_phy_12530; always @(posedge lint_clk) r_phy_12530 <= {1{lint_in}}; assign phy[12530:12530] = r_phy_12530;
    reg [1:0] r_phy_12808; always @(posedge lint_clk) r_phy_12808 <= {2{lint_in}}; assign phy[12809:12808] = r_phy_12808;
    reg [0:0] r_phy_12908; always @(posedge lint_clk) r_phy_12908 <= {1{lint_in}}; assign phy[12908:12908] = r_phy_12908;
    reg [339:0] r_phy_12910; always @(posedge lint_clk) r_phy_12910 <= {340{lint_in}}; assign phy[13249:12910] = r_phy_12910;
    reg [0:0] r_phy_13252; always @(posedge lint_clk) r_phy_13252 <= {1{lint_in}}; assign phy[13252:13252] = r_phy_13252;
    reg [0:0] r_phy_13530; always @(posedge lint_clk) r_phy_13530 <= {1{lint_in}}; assign phy[13530:13530] = r_phy_13530;
    reg [339:0] r_phy_13532; always @(posedge lint_clk) r_phy_13532 <= {340{lint_in}}; assign phy[13871:13532] = r_phy_13532;
    reg [0:0] r_phy_13874; always @(posedge lint_clk) r_phy_13874 <= {1{lint_in}}; assign phy[13874:13874] = r_phy_13874;
    reg [0:0] r_phy_14152; always @(posedge lint_clk) r_phy_14152 <= {1{lint_in}}; assign phy[14152:14152] = r_phy_14152;
    reg [339:0] r_phy_14154; always @(posedge lint_clk) r_phy_14154 <= {340{lint_in}}; assign phy[14493:14154] = r_phy_14154;
    reg [0:0] r_phy_14496; always @(posedge lint_clk) r_phy_14496 <= {1{lint_in}}; assign phy[14496:14496] = r_phy_14496;
    reg [0:0] r_phy_14774; always @(posedge lint_clk) r_phy_14774 <= {1{lint_in}}; assign phy[14774:14774] = r_phy_14774;
    reg [339:0] r_phy_14776; always @(posedge lint_clk) r_phy_14776 <= {340{lint_in}}; assign phy[15115:14776] = r_phy_14776;
    reg [0:0] r_phy_15118; always @(posedge lint_clk) r_phy_15118 <= {1{lint_in}}; assign phy[15118:15118] = r_phy_15118;
    reg [0:0] r_phy_15396; always @(posedge lint_clk) r_phy_15396 <= {1{lint_in}}; assign phy[15396:15396] = r_phy_15396;
    reg [339:0] r_phy_15398; always @(posedge lint_clk) r_phy_15398 <= {340{lint_in}}; assign phy[15737:15398] = r_phy_15398;
    reg [0:0] r_phy_15740; always @(posedge lint_clk) r_phy_15740 <= {1{lint_in}}; assign phy[15740:15740] = r_phy_15740;
    reg [0:0] r_phy_16018; always @(posedge lint_clk) r_phy_16018 <= {1{lint_in}}; assign phy[16018:16018] = r_phy_16018;
    reg [339:0] r_phy_16020; always @(posedge lint_clk) r_phy_16020 <= {340{lint_in}}; assign phy[16359:16020] = r_phy_16020;
    reg [0:0] r_phy_16362; always @(posedge lint_clk) r_phy_16362 <= {1{lint_in}}; assign phy[16362:16362] = r_phy_16362;
    reg [0:0] r_phy_16640; always @(posedge lint_clk) r_phy_16640 <= {1{lint_in}}; assign phy[16640:16640] = r_phy_16640;
    reg [339:0] r_phy_16642; always @(posedge lint_clk) r_phy_16642 <= {340{lint_in}}; assign phy[16981:16642] = r_phy_16642;
    reg [0:0] r_phy_16984; always @(posedge lint_clk) r_phy_16984 <= {1{lint_in}}; assign phy[16984:16984] = r_phy_16984;
    reg [0:0] r_phy_17262; always @(posedge lint_clk) r_phy_17262 <= {1{lint_in}}; assign phy[17262:17262] = r_phy_17262;
    reg [339:0] r_phy_17264; always @(posedge lint_clk) r_phy_17264 <= {340{lint_in}}; assign phy[17603:17264] = r_phy_17264;
    reg [0:0] r_phy_17606; always @(posedge lint_clk) r_phy_17606 <= {1{lint_in}}; assign phy[17606:17606] = r_phy_17606;
    reg [0:0] r_phy_17884; always @(posedge lint_clk) r_phy_17884 <= {1{lint_in}}; assign phy[17884:17884] = r_phy_17884;
    reg [339:0] r_phy_17886; always @(posedge lint_clk) r_phy_17886 <= {340{lint_in}}; assign phy[18225:17886] = r_phy_17886;
    reg [0:0] r_phy_18228; always @(posedge lint_clk) r_phy_18228 <= {1{lint_in}}; assign phy[18228:18228] = r_phy_18228;
    reg [0:0] r_phy_18506; always @(posedge lint_clk) r_phy_18506 <= {1{lint_in}}; assign phy[18506:18506] = r_phy_18506;
    reg [339:0] r_phy_18508; always @(posedge lint_clk) r_phy_18508 <= {340{lint_in}}; assign phy[18847:18508] = r_phy_18508;
    reg [0:0] r_phy_18850; always @(posedge lint_clk) r_phy_18850 <= {1{lint_in}}; assign phy[18850:18850] = r_phy_18850;
    reg [0:0] r_phy_19128; always @(posedge lint_clk) r_phy_19128 <= {1{lint_in}}; assign phy[19128:19128] = r_phy_19128;
    reg [339:0] r_phy_19130; always @(posedge lint_clk) r_phy_19130 <= {340{lint_in}}; assign phy[19469:19130] = r_phy_19130;
    reg [0:0] r_phy_19472; always @(posedge lint_clk) r_phy_19472 <= {1{lint_in}}; assign phy[19472:19472] = r_phy_19472;
    reg [0:0] r_phy_19750; always @(posedge lint_clk) r_phy_19750 <= {1{lint_in}}; assign phy[19750:19750] = r_phy_19750;
    reg [339:0] r_phy_19752; always @(posedge lint_clk) r_phy_19752 <= {340{lint_in}}; assign phy[20091:19752] = r_phy_19752;
    reg [0:0] r_phy_20094; always @(posedge lint_clk) r_phy_20094 <= {1{lint_in}}; assign phy[20094:20094] = r_phy_20094;
    reg [0:0] r_phy_20372; always @(posedge lint_clk) r_phy_20372 <= {1{lint_in}}; assign phy[20372:20372] = r_phy_20372;
    reg [339:0] r_phy_20374; always @(posedge lint_clk) r_phy_20374 <= {340{lint_in}}; assign phy[20713:20374] = r_phy_20374;
    reg [0:0] r_phy_20716; always @(posedge lint_clk) r_phy_20716 <= {1{lint_in}}; assign phy[20716:20716] = r_phy_20716;
    reg [0:0] r_phy_20994; always @(posedge lint_clk) r_phy_20994 <= {1{lint_in}}; assign phy[20994:20994] = r_phy_20994;
    reg [339:0] r_phy_20996; always @(posedge lint_clk) r_phy_20996 <= {340{lint_in}}; assign phy[21335:20996] = r_phy_20996;
    reg [0:0] r_phy_21338; always @(posedge lint_clk) r_phy_21338 <= {1{lint_in}}; assign phy[21338:21338] = r_phy_21338;
    reg [0:0] r_phy_21616; always @(posedge lint_clk) r_phy_21616 <= {1{lint_in}}; assign phy[21616:21616] = r_phy_21616;
    reg [339:0] r_phy_21618; always @(posedge lint_clk) r_phy_21618 <= {340{lint_in}}; assign phy[21957:21618] = r_phy_21618;
    reg [0:0] r_phy_21960; always @(posedge lint_clk) r_phy_21960 <= {1{lint_in}}; assign phy[21960:21960] = r_phy_21960;
    reg [0:0] r_qsm16_43; always @(posedge lint_clk) r_qsm16_43 <= {1{lint_in}}; assign qsm16[43:43] = r_qsm16_43;
    reg [0:0] r_qsm17_43; always @(posedge lint_clk) r_qsm17_43 <= {1{lint_in}}; assign qsm17[43:43] = r_qsm17_43;
    reg [0:0] r_qsm18_43; always @(posedge lint_clk) r_qsm18_43 <= {1{lint_in}}; assign qsm18[43:43] = r_qsm18_43;
    reg [0:0] r_qsm19_43; always @(posedge lint_clk) r_qsm19_43 <= {1{lint_in}}; assign qsm19[43:43] = r_qsm19_43;
    reg [0:0] r_qsm20_43; always @(posedge lint_clk) r_qsm20_43 <= {1{lint_in}}; assign qsm20[43:43] = r_qsm20_43;
    reg [0:0] r_qsm21_43; always @(posedge lint_clk) r_qsm21_43 <= {1{lint_in}}; assign qsm21[43:43] = r_qsm21_43;
    reg [0:0] r_qsm22_43; always @(posedge lint_clk) r_qsm22_43 <= {1{lint_in}}; assign qsm22[43:43] = r_qsm22_43;
    reg [0:0] r_qsm23_43; always @(posedge lint_clk) r_qsm23_43 <= {1{lint_in}}; assign qsm23[43:43] = r_qsm23_43;
endmodule

module hfd_svc_SE (
    input wire [0:0] ck,
    input wire [127:0] e,
    output wire [1023:0] ik,
    output wire [1023:0] kv,
    output wire [1098:0] lsm10,
    output wire [1098:0] lsm11,
    output wire [1098:0] lsm12,
    output wire [1098:0] lsm13,
    output wire [1098:0] lsm14,
    output wire [1098:0] lsm15,
    output wire [1098:0] lsm8,
    output wire [1098:0] lsm9,
    inout wire [22237:0] phy,
    inout wire [43:0] qsm10,
    inout wire [43:0] qsm11,
    inout wire [43:0] qsm12,
    inout wire [43:0] qsm13,
    inout wire [43:0] qsm14,
    inout wire [43:0] qsm15,
    inout wire [43:0] qsm8,
    inout wire [43:0] qsm9
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^e, ^phy, ^qsm10, ^qsm11, ^qsm12, ^qsm13, ^qsm14, ^qsm15, ^qsm8, ^qsm9};
    reg [1023:0] r_ik_0; always @(posedge lint_clk) r_ik_0 <= {1024{lint_in}}; assign ik[1023:0] = r_ik_0;
    reg [1023:0] r_kv_0; always @(posedge lint_clk) r_kv_0 <= {1024{lint_in}}; assign kv[1023:0] = r_kv_0;
    reg [1098:0] r_lsm10_0; always @(posedge lint_clk) r_lsm10_0 <= {1099{lint_in}}; assign lsm10[1098:0] = r_lsm10_0;
    reg [1098:0] r_lsm11_0; always @(posedge lint_clk) r_lsm11_0 <= {1099{lint_in}}; assign lsm11[1098:0] = r_lsm11_0;
    reg [1098:0] r_lsm12_0; always @(posedge lint_clk) r_lsm12_0 <= {1099{lint_in}}; assign lsm12[1098:0] = r_lsm12_0;
    reg [1098:0] r_lsm13_0; always @(posedge lint_clk) r_lsm13_0 <= {1099{lint_in}}; assign lsm13[1098:0] = r_lsm13_0;
    reg [1098:0] r_lsm14_0; always @(posedge lint_clk) r_lsm14_0 <= {1099{lint_in}}; assign lsm14[1098:0] = r_lsm14_0;
    reg [1098:0] r_lsm15_0; always @(posedge lint_clk) r_lsm15_0 <= {1099{lint_in}}; assign lsm15[1098:0] = r_lsm15_0;
    reg [1098:0] r_lsm8_0; always @(posedge lint_clk) r_lsm8_0 <= {1099{lint_in}}; assign lsm8[1098:0] = r_lsm8_0;
    reg [1098:0] r_lsm9_0; always @(posedge lint_clk) r_lsm9_0 <= {1099{lint_in}}; assign lsm9[1098:0] = r_lsm9_0;
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
    reg [0:0] r_phy_3626; always @(posedge lint_clk) r_phy_3626 <= {1{lint_in}}; assign phy[3626:3626] = r_phy_3626;
    reg [339:0] r_phy_3628; always @(posedge lint_clk) r_phy_3628 <= {340{lint_in}}; assign phy[3967:3628] = r_phy_3628;
    reg [0:0] r_phy_3970; always @(posedge lint_clk) r_phy_3970 <= {1{lint_in}}; assign phy[3970:3970] = r_phy_3970;
    reg [0:0] r_phy_4250; always @(posedge lint_clk) r_phy_4250 <= {1{lint_in}}; assign phy[4250:4250] = r_phy_4250;
    reg [0:0] r_phy_4522; always @(posedge lint_clk) r_phy_4522 <= {1{lint_in}}; assign phy[4522:4522] = r_phy_4522;
    reg [339:0] r_phy_4524; always @(posedge lint_clk) r_phy_4524 <= {340{lint_in}}; assign phy[4863:4524] = r_phy_4524;
    reg [0:0] r_phy_4866; always @(posedge lint_clk) r_phy_4866 <= {1{lint_in}}; assign phy[4866:4866] = r_phy_4866;
    reg [0:0] r_phy_5146; always @(posedge lint_clk) r_phy_5146 <= {1{lint_in}}; assign phy[5146:5146] = r_phy_5146;
    reg [0:0] r_phy_5418; always @(posedge lint_clk) r_phy_5418 <= {1{lint_in}}; assign phy[5418:5418] = r_phy_5418;
    reg [339:0] r_phy_5420; always @(posedge lint_clk) r_phy_5420 <= {340{lint_in}}; assign phy[5759:5420] = r_phy_5420;
    reg [0:0] r_phy_5762; always @(posedge lint_clk) r_phy_5762 <= {1{lint_in}}; assign phy[5762:5762] = r_phy_5762;
    reg [0:0] r_phy_6042; always @(posedge lint_clk) r_phy_6042 <= {1{lint_in}}; assign phy[6042:6042] = r_phy_6042;
    reg [0:0] r_phy_6314; always @(posedge lint_clk) r_phy_6314 <= {1{lint_in}}; assign phy[6314:6314] = r_phy_6314;
    reg [339:0] r_phy_6316; always @(posedge lint_clk) r_phy_6316 <= {340{lint_in}}; assign phy[6655:6316] = r_phy_6316;
    reg [0:0] r_phy_6658; always @(posedge lint_clk) r_phy_6658 <= {1{lint_in}}; assign phy[6658:6658] = r_phy_6658;
    reg [0:0] r_phy_6938; always @(posedge lint_clk) r_phy_6938 <= {1{lint_in}}; assign phy[6938:6938] = r_phy_6938;
    reg [0:0] r_phy_7210; always @(posedge lint_clk) r_phy_7210 <= {1{lint_in}}; assign phy[7210:7210] = r_phy_7210;
    reg [339:0] r_phy_7212; always @(posedge lint_clk) r_phy_7212 <= {340{lint_in}}; assign phy[7551:7212] = r_phy_7212;
    reg [0:0] r_phy_7554; always @(posedge lint_clk) r_phy_7554 <= {1{lint_in}}; assign phy[7554:7554] = r_phy_7554;
    reg [0:0] r_phy_7832; always @(posedge lint_clk) r_phy_7832 <= {1{lint_in}}; assign phy[7832:7832] = r_phy_7832;
    reg [339:0] r_phy_7834; always @(posedge lint_clk) r_phy_7834 <= {340{lint_in}}; assign phy[8173:7834] = r_phy_7834;
    reg [0:0] r_phy_8176; always @(posedge lint_clk) r_phy_8176 <= {1{lint_in}}; assign phy[8176:8176] = r_phy_8176;
    reg [0:0] r_phy_8454; always @(posedge lint_clk) r_phy_8454 <= {1{lint_in}}; assign phy[8454:8454] = r_phy_8454;
    reg [339:0] r_phy_8456; always @(posedge lint_clk) r_phy_8456 <= {340{lint_in}}; assign phy[8795:8456] = r_phy_8456;
    reg [0:0] r_phy_8798; always @(posedge lint_clk) r_phy_8798 <= {1{lint_in}}; assign phy[8798:8798] = r_phy_8798;
    reg [0:0] r_phy_9076; always @(posedge lint_clk) r_phy_9076 <= {1{lint_in}}; assign phy[9076:9076] = r_phy_9076;
    reg [339:0] r_phy_9078; always @(posedge lint_clk) r_phy_9078 <= {340{lint_in}}; assign phy[9417:9078] = r_phy_9078;
    reg [0:0] r_phy_9420; always @(posedge lint_clk) r_phy_9420 <= {1{lint_in}}; assign phy[9420:9420] = r_phy_9420;
    reg [0:0] r_phy_9698; always @(posedge lint_clk) r_phy_9698 <= {1{lint_in}}; assign phy[9698:9698] = r_phy_9698;
    reg [339:0] r_phy_9700; always @(posedge lint_clk) r_phy_9700 <= {340{lint_in}}; assign phy[10039:9700] = r_phy_9700;
    reg [0:0] r_phy_10042; always @(posedge lint_clk) r_phy_10042 <= {1{lint_in}}; assign phy[10042:10042] = r_phy_10042;
    reg [0:0] r_phy_10320; always @(posedge lint_clk) r_phy_10320 <= {1{lint_in}}; assign phy[10320:10320] = r_phy_10320;
    reg [339:0] r_phy_10322; always @(posedge lint_clk) r_phy_10322 <= {340{lint_in}}; assign phy[10661:10322] = r_phy_10322;
    reg [0:0] r_phy_10664; always @(posedge lint_clk) r_phy_10664 <= {1{lint_in}}; assign phy[10664:10664] = r_phy_10664;
    reg [0:0] r_phy_10942; always @(posedge lint_clk) r_phy_10942 <= {1{lint_in}}; assign phy[10942:10942] = r_phy_10942;
    reg [339:0] r_phy_10944; always @(posedge lint_clk) r_phy_10944 <= {340{lint_in}}; assign phy[11283:10944] = r_phy_10944;
    reg [0:0] r_phy_11286; always @(posedge lint_clk) r_phy_11286 <= {1{lint_in}}; assign phy[11286:11286] = r_phy_11286;
    reg [0:0] r_phy_11564; always @(posedge lint_clk) r_phy_11564 <= {1{lint_in}}; assign phy[11564:11564] = r_phy_11564;
    reg [339:0] r_phy_11566; always @(posedge lint_clk) r_phy_11566 <= {340{lint_in}}; assign phy[11905:11566] = r_phy_11566;
    reg [0:0] r_phy_11908; always @(posedge lint_clk) r_phy_11908 <= {1{lint_in}}; assign phy[11908:11908] = r_phy_11908;
    reg [0:0] r_phy_12186; always @(posedge lint_clk) r_phy_12186 <= {1{lint_in}}; assign phy[12186:12186] = r_phy_12186;
    reg [339:0] r_phy_12188; always @(posedge lint_clk) r_phy_12188 <= {340{lint_in}}; assign phy[12527:12188] = r_phy_12188;
    reg [0:0] r_phy_12530; always @(posedge lint_clk) r_phy_12530 <= {1{lint_in}}; assign phy[12530:12530] = r_phy_12530;
    reg [1:0] r_phy_12808; always @(posedge lint_clk) r_phy_12808 <= {2{lint_in}}; assign phy[12809:12808] = r_phy_12808;
    reg [0:0] r_phy_12908; always @(posedge lint_clk) r_phy_12908 <= {1{lint_in}}; assign phy[12908:12908] = r_phy_12908;
    reg [339:0] r_phy_12910; always @(posedge lint_clk) r_phy_12910 <= {340{lint_in}}; assign phy[13249:12910] = r_phy_12910;
    reg [0:0] r_phy_13252; always @(posedge lint_clk) r_phy_13252 <= {1{lint_in}}; assign phy[13252:13252] = r_phy_13252;
    reg [0:0] r_phy_13530; always @(posedge lint_clk) r_phy_13530 <= {1{lint_in}}; assign phy[13530:13530] = r_phy_13530;
    reg [339:0] r_phy_13532; always @(posedge lint_clk) r_phy_13532 <= {340{lint_in}}; assign phy[13871:13532] = r_phy_13532;
    reg [0:0] r_phy_13874; always @(posedge lint_clk) r_phy_13874 <= {1{lint_in}}; assign phy[13874:13874] = r_phy_13874;
    reg [0:0] r_phy_14152; always @(posedge lint_clk) r_phy_14152 <= {1{lint_in}}; assign phy[14152:14152] = r_phy_14152;
    reg [339:0] r_phy_14154; always @(posedge lint_clk) r_phy_14154 <= {340{lint_in}}; assign phy[14493:14154] = r_phy_14154;
    reg [0:0] r_phy_14496; always @(posedge lint_clk) r_phy_14496 <= {1{lint_in}}; assign phy[14496:14496] = r_phy_14496;
    reg [0:0] r_phy_14774; always @(posedge lint_clk) r_phy_14774 <= {1{lint_in}}; assign phy[14774:14774] = r_phy_14774;
    reg [339:0] r_phy_14776; always @(posedge lint_clk) r_phy_14776 <= {340{lint_in}}; assign phy[15115:14776] = r_phy_14776;
    reg [0:0] r_phy_15118; always @(posedge lint_clk) r_phy_15118 <= {1{lint_in}}; assign phy[15118:15118] = r_phy_15118;
    reg [0:0] r_phy_15396; always @(posedge lint_clk) r_phy_15396 <= {1{lint_in}}; assign phy[15396:15396] = r_phy_15396;
    reg [339:0] r_phy_15398; always @(posedge lint_clk) r_phy_15398 <= {340{lint_in}}; assign phy[15737:15398] = r_phy_15398;
    reg [0:0] r_phy_15740; always @(posedge lint_clk) r_phy_15740 <= {1{lint_in}}; assign phy[15740:15740] = r_phy_15740;
    reg [0:0] r_phy_16018; always @(posedge lint_clk) r_phy_16018 <= {1{lint_in}}; assign phy[16018:16018] = r_phy_16018;
    reg [339:0] r_phy_16020; always @(posedge lint_clk) r_phy_16020 <= {340{lint_in}}; assign phy[16359:16020] = r_phy_16020;
    reg [0:0] r_phy_16362; always @(posedge lint_clk) r_phy_16362 <= {1{lint_in}}; assign phy[16362:16362] = r_phy_16362;
    reg [0:0] r_phy_16640; always @(posedge lint_clk) r_phy_16640 <= {1{lint_in}}; assign phy[16640:16640] = r_phy_16640;
    reg [339:0] r_phy_16642; always @(posedge lint_clk) r_phy_16642 <= {340{lint_in}}; assign phy[16981:16642] = r_phy_16642;
    reg [0:0] r_phy_16984; always @(posedge lint_clk) r_phy_16984 <= {1{lint_in}}; assign phy[16984:16984] = r_phy_16984;
    reg [0:0] r_phy_17262; always @(posedge lint_clk) r_phy_17262 <= {1{lint_in}}; assign phy[17262:17262] = r_phy_17262;
    reg [339:0] r_phy_17264; always @(posedge lint_clk) r_phy_17264 <= {340{lint_in}}; assign phy[17603:17264] = r_phy_17264;
    reg [0:0] r_phy_17606; always @(posedge lint_clk) r_phy_17606 <= {1{lint_in}}; assign phy[17606:17606] = r_phy_17606;
    reg [0:0] r_phy_17884; always @(posedge lint_clk) r_phy_17884 <= {1{lint_in}}; assign phy[17884:17884] = r_phy_17884;
    reg [339:0] r_phy_17886; always @(posedge lint_clk) r_phy_17886 <= {340{lint_in}}; assign phy[18225:17886] = r_phy_17886;
    reg [0:0] r_phy_18228; always @(posedge lint_clk) r_phy_18228 <= {1{lint_in}}; assign phy[18228:18228] = r_phy_18228;
    reg [0:0] r_phy_18506; always @(posedge lint_clk) r_phy_18506 <= {1{lint_in}}; assign phy[18506:18506] = r_phy_18506;
    reg [339:0] r_phy_18508; always @(posedge lint_clk) r_phy_18508 <= {340{lint_in}}; assign phy[18847:18508] = r_phy_18508;
    reg [0:0] r_phy_18850; always @(posedge lint_clk) r_phy_18850 <= {1{lint_in}}; assign phy[18850:18850] = r_phy_18850;
    reg [0:0] r_phy_19128; always @(posedge lint_clk) r_phy_19128 <= {1{lint_in}}; assign phy[19128:19128] = r_phy_19128;
    reg [339:0] r_phy_19130; always @(posedge lint_clk) r_phy_19130 <= {340{lint_in}}; assign phy[19469:19130] = r_phy_19130;
    reg [0:0] r_phy_19472; always @(posedge lint_clk) r_phy_19472 <= {1{lint_in}}; assign phy[19472:19472] = r_phy_19472;
    reg [0:0] r_phy_19750; always @(posedge lint_clk) r_phy_19750 <= {1{lint_in}}; assign phy[19750:19750] = r_phy_19750;
    reg [339:0] r_phy_19752; always @(posedge lint_clk) r_phy_19752 <= {340{lint_in}}; assign phy[20091:19752] = r_phy_19752;
    reg [0:0] r_phy_20094; always @(posedge lint_clk) r_phy_20094 <= {1{lint_in}}; assign phy[20094:20094] = r_phy_20094;
    reg [0:0] r_phy_20372; always @(posedge lint_clk) r_phy_20372 <= {1{lint_in}}; assign phy[20372:20372] = r_phy_20372;
    reg [339:0] r_phy_20374; always @(posedge lint_clk) r_phy_20374 <= {340{lint_in}}; assign phy[20713:20374] = r_phy_20374;
    reg [0:0] r_phy_20716; always @(posedge lint_clk) r_phy_20716 <= {1{lint_in}}; assign phy[20716:20716] = r_phy_20716;
    reg [0:0] r_phy_20994; always @(posedge lint_clk) r_phy_20994 <= {1{lint_in}}; assign phy[20994:20994] = r_phy_20994;
    reg [339:0] r_phy_20996; always @(posedge lint_clk) r_phy_20996 <= {340{lint_in}}; assign phy[21335:20996] = r_phy_20996;
    reg [0:0] r_phy_21338; always @(posedge lint_clk) r_phy_21338 <= {1{lint_in}}; assign phy[21338:21338] = r_phy_21338;
    reg [0:0] r_phy_21616; always @(posedge lint_clk) r_phy_21616 <= {1{lint_in}}; assign phy[21616:21616] = r_phy_21616;
    reg [339:0] r_phy_21618; always @(posedge lint_clk) r_phy_21618 <= {340{lint_in}}; assign phy[21957:21618] = r_phy_21618;
    reg [0:0] r_phy_21960; always @(posedge lint_clk) r_phy_21960 <= {1{lint_in}}; assign phy[21960:21960] = r_phy_21960;
    reg [0:0] r_qsm10_43; always @(posedge lint_clk) r_qsm10_43 <= {1{lint_in}}; assign qsm10[43:43] = r_qsm10_43;
    reg [0:0] r_qsm11_43; always @(posedge lint_clk) r_qsm11_43 <= {1{lint_in}}; assign qsm11[43:43] = r_qsm11_43;
    reg [0:0] r_qsm12_43; always @(posedge lint_clk) r_qsm12_43 <= {1{lint_in}}; assign qsm12[43:43] = r_qsm12_43;
    reg [0:0] r_qsm13_43; always @(posedge lint_clk) r_qsm13_43 <= {1{lint_in}}; assign qsm13[43:43] = r_qsm13_43;
    reg [0:0] r_qsm14_43; always @(posedge lint_clk) r_qsm14_43 <= {1{lint_in}}; assign qsm14[43:43] = r_qsm14_43;
    reg [0:0] r_qsm15_43; always @(posedge lint_clk) r_qsm15_43 <= {1{lint_in}}; assign qsm15[43:43] = r_qsm15_43;
    reg [0:0] r_qsm8_43; always @(posedge lint_clk) r_qsm8_43 <= {1{lint_in}}; assign qsm8[43:43] = r_qsm8_43;
    reg [0:0] r_qsm9_43; always @(posedge lint_clk) r_qsm9_43 <= {1{lint_in}}; assign qsm9[43:43] = r_qsm9_43;
endmodule

module hfd_svc_SW (
    input wire [0:0] ck,
    input wire [127:0] e,
    output wire [1023:0] ik,
    output wire [1023:0] kv,
    output wire [1098:0] lsm0,
    output wire [1098:0] lsm1,
    output wire [1098:0] lsm2,
    output wire [1098:0] lsm3,
    output wire [1098:0] lsm4,
    output wire [1098:0] lsm5,
    output wire [1098:0] lsm6,
    output wire [1098:0] lsm7,
    inout wire [22237:0] phy,
    inout wire [43:0] qsm0,
    inout wire [43:0] qsm1,
    inout wire [43:0] qsm2,
    inout wire [43:0] qsm3,
    inout wire [43:0] qsm4,
    inout wire [43:0] qsm5,
    inout wire [43:0] qsm6,
    inout wire [43:0] qsm7
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^e, ^phy, ^qsm0, ^qsm1, ^qsm2, ^qsm3, ^qsm4, ^qsm5, ^qsm6, ^qsm7};
    reg [1023:0] r_ik_0; always @(posedge lint_clk) r_ik_0 <= {1024{lint_in}}; assign ik[1023:0] = r_ik_0;
    reg [1023:0] r_kv_0; always @(posedge lint_clk) r_kv_0 <= {1024{lint_in}}; assign kv[1023:0] = r_kv_0;
    reg [1098:0] r_lsm0_0; always @(posedge lint_clk) r_lsm0_0 <= {1099{lint_in}}; assign lsm0[1098:0] = r_lsm0_0;
    reg [1098:0] r_lsm1_0; always @(posedge lint_clk) r_lsm1_0 <= {1099{lint_in}}; assign lsm1[1098:0] = r_lsm1_0;
    reg [1098:0] r_lsm2_0; always @(posedge lint_clk) r_lsm2_0 <= {1099{lint_in}}; assign lsm2[1098:0] = r_lsm2_0;
    reg [1098:0] r_lsm3_0; always @(posedge lint_clk) r_lsm3_0 <= {1099{lint_in}}; assign lsm3[1098:0] = r_lsm3_0;
    reg [1098:0] r_lsm4_0; always @(posedge lint_clk) r_lsm4_0 <= {1099{lint_in}}; assign lsm4[1098:0] = r_lsm4_0;
    reg [1098:0] r_lsm5_0; always @(posedge lint_clk) r_lsm5_0 <= {1099{lint_in}}; assign lsm5[1098:0] = r_lsm5_0;
    reg [1098:0] r_lsm6_0; always @(posedge lint_clk) r_lsm6_0 <= {1099{lint_in}}; assign lsm6[1098:0] = r_lsm6_0;
    reg [1098:0] r_lsm7_0; always @(posedge lint_clk) r_lsm7_0 <= {1099{lint_in}}; assign lsm7[1098:0] = r_lsm7_0;
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
    reg [0:0] r_phy_3626; always @(posedge lint_clk) r_phy_3626 <= {1{lint_in}}; assign phy[3626:3626] = r_phy_3626;
    reg [339:0] r_phy_3628; always @(posedge lint_clk) r_phy_3628 <= {340{lint_in}}; assign phy[3967:3628] = r_phy_3628;
    reg [0:0] r_phy_3970; always @(posedge lint_clk) r_phy_3970 <= {1{lint_in}}; assign phy[3970:3970] = r_phy_3970;
    reg [0:0] r_phy_4250; always @(posedge lint_clk) r_phy_4250 <= {1{lint_in}}; assign phy[4250:4250] = r_phy_4250;
    reg [0:0] r_phy_4522; always @(posedge lint_clk) r_phy_4522 <= {1{lint_in}}; assign phy[4522:4522] = r_phy_4522;
    reg [339:0] r_phy_4524; always @(posedge lint_clk) r_phy_4524 <= {340{lint_in}}; assign phy[4863:4524] = r_phy_4524;
    reg [0:0] r_phy_4866; always @(posedge lint_clk) r_phy_4866 <= {1{lint_in}}; assign phy[4866:4866] = r_phy_4866;
    reg [0:0] r_phy_5146; always @(posedge lint_clk) r_phy_5146 <= {1{lint_in}}; assign phy[5146:5146] = r_phy_5146;
    reg [0:0] r_phy_5418; always @(posedge lint_clk) r_phy_5418 <= {1{lint_in}}; assign phy[5418:5418] = r_phy_5418;
    reg [339:0] r_phy_5420; always @(posedge lint_clk) r_phy_5420 <= {340{lint_in}}; assign phy[5759:5420] = r_phy_5420;
    reg [0:0] r_phy_5762; always @(posedge lint_clk) r_phy_5762 <= {1{lint_in}}; assign phy[5762:5762] = r_phy_5762;
    reg [0:0] r_phy_6042; always @(posedge lint_clk) r_phy_6042 <= {1{lint_in}}; assign phy[6042:6042] = r_phy_6042;
    reg [0:0] r_phy_6314; always @(posedge lint_clk) r_phy_6314 <= {1{lint_in}}; assign phy[6314:6314] = r_phy_6314;
    reg [339:0] r_phy_6316; always @(posedge lint_clk) r_phy_6316 <= {340{lint_in}}; assign phy[6655:6316] = r_phy_6316;
    reg [0:0] r_phy_6658; always @(posedge lint_clk) r_phy_6658 <= {1{lint_in}}; assign phy[6658:6658] = r_phy_6658;
    reg [0:0] r_phy_6938; always @(posedge lint_clk) r_phy_6938 <= {1{lint_in}}; assign phy[6938:6938] = r_phy_6938;
    reg [0:0] r_phy_7210; always @(posedge lint_clk) r_phy_7210 <= {1{lint_in}}; assign phy[7210:7210] = r_phy_7210;
    reg [339:0] r_phy_7212; always @(posedge lint_clk) r_phy_7212 <= {340{lint_in}}; assign phy[7551:7212] = r_phy_7212;
    reg [0:0] r_phy_7554; always @(posedge lint_clk) r_phy_7554 <= {1{lint_in}}; assign phy[7554:7554] = r_phy_7554;
    reg [0:0] r_phy_7832; always @(posedge lint_clk) r_phy_7832 <= {1{lint_in}}; assign phy[7832:7832] = r_phy_7832;
    reg [339:0] r_phy_7834; always @(posedge lint_clk) r_phy_7834 <= {340{lint_in}}; assign phy[8173:7834] = r_phy_7834;
    reg [0:0] r_phy_8176; always @(posedge lint_clk) r_phy_8176 <= {1{lint_in}}; assign phy[8176:8176] = r_phy_8176;
    reg [0:0] r_phy_8454; always @(posedge lint_clk) r_phy_8454 <= {1{lint_in}}; assign phy[8454:8454] = r_phy_8454;
    reg [339:0] r_phy_8456; always @(posedge lint_clk) r_phy_8456 <= {340{lint_in}}; assign phy[8795:8456] = r_phy_8456;
    reg [0:0] r_phy_8798; always @(posedge lint_clk) r_phy_8798 <= {1{lint_in}}; assign phy[8798:8798] = r_phy_8798;
    reg [0:0] r_phy_9076; always @(posedge lint_clk) r_phy_9076 <= {1{lint_in}}; assign phy[9076:9076] = r_phy_9076;
    reg [339:0] r_phy_9078; always @(posedge lint_clk) r_phy_9078 <= {340{lint_in}}; assign phy[9417:9078] = r_phy_9078;
    reg [0:0] r_phy_9420; always @(posedge lint_clk) r_phy_9420 <= {1{lint_in}}; assign phy[9420:9420] = r_phy_9420;
    reg [0:0] r_phy_9698; always @(posedge lint_clk) r_phy_9698 <= {1{lint_in}}; assign phy[9698:9698] = r_phy_9698;
    reg [339:0] r_phy_9700; always @(posedge lint_clk) r_phy_9700 <= {340{lint_in}}; assign phy[10039:9700] = r_phy_9700;
    reg [0:0] r_phy_10042; always @(posedge lint_clk) r_phy_10042 <= {1{lint_in}}; assign phy[10042:10042] = r_phy_10042;
    reg [0:0] r_phy_10320; always @(posedge lint_clk) r_phy_10320 <= {1{lint_in}}; assign phy[10320:10320] = r_phy_10320;
    reg [339:0] r_phy_10322; always @(posedge lint_clk) r_phy_10322 <= {340{lint_in}}; assign phy[10661:10322] = r_phy_10322;
    reg [0:0] r_phy_10664; always @(posedge lint_clk) r_phy_10664 <= {1{lint_in}}; assign phy[10664:10664] = r_phy_10664;
    reg [0:0] r_phy_10942; always @(posedge lint_clk) r_phy_10942 <= {1{lint_in}}; assign phy[10942:10942] = r_phy_10942;
    reg [339:0] r_phy_10944; always @(posedge lint_clk) r_phy_10944 <= {340{lint_in}}; assign phy[11283:10944] = r_phy_10944;
    reg [0:0] r_phy_11286; always @(posedge lint_clk) r_phy_11286 <= {1{lint_in}}; assign phy[11286:11286] = r_phy_11286;
    reg [0:0] r_phy_11564; always @(posedge lint_clk) r_phy_11564 <= {1{lint_in}}; assign phy[11564:11564] = r_phy_11564;
    reg [339:0] r_phy_11566; always @(posedge lint_clk) r_phy_11566 <= {340{lint_in}}; assign phy[11905:11566] = r_phy_11566;
    reg [0:0] r_phy_11908; always @(posedge lint_clk) r_phy_11908 <= {1{lint_in}}; assign phy[11908:11908] = r_phy_11908;
    reg [0:0] r_phy_12186; always @(posedge lint_clk) r_phy_12186 <= {1{lint_in}}; assign phy[12186:12186] = r_phy_12186;
    reg [339:0] r_phy_12188; always @(posedge lint_clk) r_phy_12188 <= {340{lint_in}}; assign phy[12527:12188] = r_phy_12188;
    reg [0:0] r_phy_12530; always @(posedge lint_clk) r_phy_12530 <= {1{lint_in}}; assign phy[12530:12530] = r_phy_12530;
    reg [1:0] r_phy_12808; always @(posedge lint_clk) r_phy_12808 <= {2{lint_in}}; assign phy[12809:12808] = r_phy_12808;
    reg [0:0] r_phy_12908; always @(posedge lint_clk) r_phy_12908 <= {1{lint_in}}; assign phy[12908:12908] = r_phy_12908;
    reg [339:0] r_phy_12910; always @(posedge lint_clk) r_phy_12910 <= {340{lint_in}}; assign phy[13249:12910] = r_phy_12910;
    reg [0:0] r_phy_13252; always @(posedge lint_clk) r_phy_13252 <= {1{lint_in}}; assign phy[13252:13252] = r_phy_13252;
    reg [0:0] r_phy_13530; always @(posedge lint_clk) r_phy_13530 <= {1{lint_in}}; assign phy[13530:13530] = r_phy_13530;
    reg [339:0] r_phy_13532; always @(posedge lint_clk) r_phy_13532 <= {340{lint_in}}; assign phy[13871:13532] = r_phy_13532;
    reg [0:0] r_phy_13874; always @(posedge lint_clk) r_phy_13874 <= {1{lint_in}}; assign phy[13874:13874] = r_phy_13874;
    reg [0:0] r_phy_14152; always @(posedge lint_clk) r_phy_14152 <= {1{lint_in}}; assign phy[14152:14152] = r_phy_14152;
    reg [339:0] r_phy_14154; always @(posedge lint_clk) r_phy_14154 <= {340{lint_in}}; assign phy[14493:14154] = r_phy_14154;
    reg [0:0] r_phy_14496; always @(posedge lint_clk) r_phy_14496 <= {1{lint_in}}; assign phy[14496:14496] = r_phy_14496;
    reg [0:0] r_phy_14774; always @(posedge lint_clk) r_phy_14774 <= {1{lint_in}}; assign phy[14774:14774] = r_phy_14774;
    reg [339:0] r_phy_14776; always @(posedge lint_clk) r_phy_14776 <= {340{lint_in}}; assign phy[15115:14776] = r_phy_14776;
    reg [0:0] r_phy_15118; always @(posedge lint_clk) r_phy_15118 <= {1{lint_in}}; assign phy[15118:15118] = r_phy_15118;
    reg [0:0] r_phy_15396; always @(posedge lint_clk) r_phy_15396 <= {1{lint_in}}; assign phy[15396:15396] = r_phy_15396;
    reg [339:0] r_phy_15398; always @(posedge lint_clk) r_phy_15398 <= {340{lint_in}}; assign phy[15737:15398] = r_phy_15398;
    reg [0:0] r_phy_15740; always @(posedge lint_clk) r_phy_15740 <= {1{lint_in}}; assign phy[15740:15740] = r_phy_15740;
    reg [0:0] r_phy_16018; always @(posedge lint_clk) r_phy_16018 <= {1{lint_in}}; assign phy[16018:16018] = r_phy_16018;
    reg [339:0] r_phy_16020; always @(posedge lint_clk) r_phy_16020 <= {340{lint_in}}; assign phy[16359:16020] = r_phy_16020;
    reg [0:0] r_phy_16362; always @(posedge lint_clk) r_phy_16362 <= {1{lint_in}}; assign phy[16362:16362] = r_phy_16362;
    reg [0:0] r_phy_16640; always @(posedge lint_clk) r_phy_16640 <= {1{lint_in}}; assign phy[16640:16640] = r_phy_16640;
    reg [339:0] r_phy_16642; always @(posedge lint_clk) r_phy_16642 <= {340{lint_in}}; assign phy[16981:16642] = r_phy_16642;
    reg [0:0] r_phy_16984; always @(posedge lint_clk) r_phy_16984 <= {1{lint_in}}; assign phy[16984:16984] = r_phy_16984;
    reg [0:0] r_phy_17262; always @(posedge lint_clk) r_phy_17262 <= {1{lint_in}}; assign phy[17262:17262] = r_phy_17262;
    reg [339:0] r_phy_17264; always @(posedge lint_clk) r_phy_17264 <= {340{lint_in}}; assign phy[17603:17264] = r_phy_17264;
    reg [0:0] r_phy_17606; always @(posedge lint_clk) r_phy_17606 <= {1{lint_in}}; assign phy[17606:17606] = r_phy_17606;
    reg [0:0] r_phy_17884; always @(posedge lint_clk) r_phy_17884 <= {1{lint_in}}; assign phy[17884:17884] = r_phy_17884;
    reg [339:0] r_phy_17886; always @(posedge lint_clk) r_phy_17886 <= {340{lint_in}}; assign phy[18225:17886] = r_phy_17886;
    reg [0:0] r_phy_18228; always @(posedge lint_clk) r_phy_18228 <= {1{lint_in}}; assign phy[18228:18228] = r_phy_18228;
    reg [0:0] r_phy_18506; always @(posedge lint_clk) r_phy_18506 <= {1{lint_in}}; assign phy[18506:18506] = r_phy_18506;
    reg [339:0] r_phy_18508; always @(posedge lint_clk) r_phy_18508 <= {340{lint_in}}; assign phy[18847:18508] = r_phy_18508;
    reg [0:0] r_phy_18850; always @(posedge lint_clk) r_phy_18850 <= {1{lint_in}}; assign phy[18850:18850] = r_phy_18850;
    reg [0:0] r_phy_19128; always @(posedge lint_clk) r_phy_19128 <= {1{lint_in}}; assign phy[19128:19128] = r_phy_19128;
    reg [339:0] r_phy_19130; always @(posedge lint_clk) r_phy_19130 <= {340{lint_in}}; assign phy[19469:19130] = r_phy_19130;
    reg [0:0] r_phy_19472; always @(posedge lint_clk) r_phy_19472 <= {1{lint_in}}; assign phy[19472:19472] = r_phy_19472;
    reg [0:0] r_phy_19750; always @(posedge lint_clk) r_phy_19750 <= {1{lint_in}}; assign phy[19750:19750] = r_phy_19750;
    reg [339:0] r_phy_19752; always @(posedge lint_clk) r_phy_19752 <= {340{lint_in}}; assign phy[20091:19752] = r_phy_19752;
    reg [0:0] r_phy_20094; always @(posedge lint_clk) r_phy_20094 <= {1{lint_in}}; assign phy[20094:20094] = r_phy_20094;
    reg [0:0] r_phy_20372; always @(posedge lint_clk) r_phy_20372 <= {1{lint_in}}; assign phy[20372:20372] = r_phy_20372;
    reg [339:0] r_phy_20374; always @(posedge lint_clk) r_phy_20374 <= {340{lint_in}}; assign phy[20713:20374] = r_phy_20374;
    reg [0:0] r_phy_20716; always @(posedge lint_clk) r_phy_20716 <= {1{lint_in}}; assign phy[20716:20716] = r_phy_20716;
    reg [0:0] r_phy_20994; always @(posedge lint_clk) r_phy_20994 <= {1{lint_in}}; assign phy[20994:20994] = r_phy_20994;
    reg [339:0] r_phy_20996; always @(posedge lint_clk) r_phy_20996 <= {340{lint_in}}; assign phy[21335:20996] = r_phy_20996;
    reg [0:0] r_phy_21338; always @(posedge lint_clk) r_phy_21338 <= {1{lint_in}}; assign phy[21338:21338] = r_phy_21338;
    reg [0:0] r_phy_21616; always @(posedge lint_clk) r_phy_21616 <= {1{lint_in}}; assign phy[21616:21616] = r_phy_21616;
    reg [339:0] r_phy_21618; always @(posedge lint_clk) r_phy_21618 <= {340{lint_in}}; assign phy[21957:21618] = r_phy_21618;
    reg [0:0] r_phy_21960; always @(posedge lint_clk) r_phy_21960 <= {1{lint_in}}; assign phy[21960:21960] = r_phy_21960;
    reg [0:0] r_qsm0_43; always @(posedge lint_clk) r_qsm0_43 <= {1{lint_in}}; assign qsm0[43:43] = r_qsm0_43;
    reg [0:0] r_qsm1_43; always @(posedge lint_clk) r_qsm1_43 <= {1{lint_in}}; assign qsm1[43:43] = r_qsm1_43;
    reg [0:0] r_qsm2_43; always @(posedge lint_clk) r_qsm2_43 <= {1{lint_in}}; assign qsm2[43:43] = r_qsm2_43;
    reg [0:0] r_qsm3_43; always @(posedge lint_clk) r_qsm3_43 <= {1{lint_in}}; assign qsm3[43:43] = r_qsm3_43;
    reg [0:0] r_qsm4_43; always @(posedge lint_clk) r_qsm4_43 <= {1{lint_in}}; assign qsm4[43:43] = r_qsm4_43;
    reg [0:0] r_qsm5_43; always @(posedge lint_clk) r_qsm5_43 <= {1{lint_in}}; assign qsm5[43:43] = r_qsm5_43;
    reg [0:0] r_qsm6_43; always @(posedge lint_clk) r_qsm6_43 <= {1{lint_in}}; assign qsm6[43:43] = r_qsm6_43;
    reg [0:0] r_qsm7_43; always @(posedge lint_clk) r_qsm7_43 <= {1{lint_in}}; assign qsm7[43:43] = r_qsm7_43;
endmodule

module hfd_vm (
    input wire [0:0] ck,
    input wire [2047:0] f_su_NE,
    input wire [2047:0] f_su_NW,
    input wire [2047:0] f_su_SE,
    input wire [2047:0] f_su_SW,
    input wire [511:0] iNE,
    input wire [511:0] iNW,
    input wire [511:0] iSE,
    input wire [511:0] iSW,
    output wire [511:0] t_coll,
    output wire [1023:0] t_quant,
    output wire [511:0] t_router,
    output wire [2047:0] t_su_NE,
    output wire [2047:0] t_su_NW,
    output wire [2047:0] t_su_SE,
    output wire [2047:0] t_su_SW,
    output wire [2062:0] xNE,
    output wire [2062:0] xNW,
    output wire [2062:0] xSE,
    output wire [2062:0] xSW
);
    wire lint_clk = ck[0];  // stub clock = abstract ck port
    wire lint_in = ^{^ck, ^f_su_NE, ^f_su_NW, ^f_su_SE, ^f_su_SW, ^iNE, ^iNW, ^iSE, ^iSW};
    reg [511:0] r_t_coll_0; always @(posedge lint_clk) r_t_coll_0 <= {512{lint_in}}; assign t_coll[511:0] = r_t_coll_0;
    reg [1023:0] r_t_quant_0; always @(posedge lint_clk) r_t_quant_0 <= {1024{lint_in}}; assign t_quant[1023:0] = r_t_quant_0;
    reg [511:0] r_t_router_0; always @(posedge lint_clk) r_t_router_0 <= {512{lint_in}}; assign t_router[511:0] = r_t_router_0;
    reg [2047:0] r_t_su_NE_0; always @(posedge lint_clk) r_t_su_NE_0 <= {2048{lint_in}}; assign t_su_NE[2047:0] = r_t_su_NE_0;
    reg [2047:0] r_t_su_NW_0; always @(posedge lint_clk) r_t_su_NW_0 <= {2048{lint_in}}; assign t_su_NW[2047:0] = r_t_su_NW_0;
    reg [2047:0] r_t_su_SE_0; always @(posedge lint_clk) r_t_su_SE_0 <= {2048{lint_in}}; assign t_su_SE[2047:0] = r_t_su_SE_0;
    reg [2047:0] r_t_su_SW_0; always @(posedge lint_clk) r_t_su_SW_0 <= {2048{lint_in}}; assign t_su_SW[2047:0] = r_t_su_SW_0;
    reg [2062:0] r_xNE_0; always @(posedge lint_clk) r_xNE_0 <= {2063{lint_in}}; assign xNE[2062:0] = r_xNE_0;
    reg [2062:0] r_xNW_0; always @(posedge lint_clk) r_xNW_0 <= {2063{lint_in}}; assign xNW[2062:0] = r_xNW_0;
    reg [2062:0] r_xSE_0; always @(posedge lint_clk) r_xSE_0 <= {2063{lint_in}}; assign xSE[2062:0] = r_xSE_0;
    reg [2062:0] r_xSW_0; always @(posedge lint_clk) r_xSW_0 <= {2063{lint_in}}; assign xSW[2062:0] = r_xSW_0;
endmodule
