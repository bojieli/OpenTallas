// ot_v41_rom_mac (DIE-S81-56 11-04, COORD order, RE-FORM of rom_q under OWNER 11-03 conservative form): one macro half of
// ot_v41_rom_elem_qx_pq_w10 (the body of its generate block g_mac) as a module, so it can be a hard core: 2 ROMs,
// capture, 2 lanes, 2 chains, pair adder, segment tree, output registers.  Used only with MACHARD != 0, and only for the
// S81 rom_q configuration (MTP 1, NB 2, FAST 1, PP 1, QPIPE 1, QP_CAP 0, QZ 1, QZ_NS 8, QZ_NE 4, QY 1, QX 10, PQ 1, QM 5,
// QS 5, CGR 0, BF16 0, BP 0, CG 1): each branch below is the branch g_mac takes there, with the same labels.
// Zero cycles.  One difference: clock gate copy u_cg from the parent's registered enable, the form of the CGR copies
// (same enable register as the parent's gate, so an identical edge on gclk).
`timescale 1ns/1ps
module ot_v41_rom_mac
`ifndef SYNTHESIS
    #(parameter INSTANCE = "")      // simulation ROM contents only; the hard core has one view
`endif
(
    input  wire         clk,
    input  wire         rst_n_pin,
    input  wire         cg_en,        // parent cg_en_g
    input  wire         wen_t,        // parent wen_t: segment tree clock enable on the free clock (QS >= 5)
    input  wire         i1_v,
    input  wire         i1_bk,
    input  wire         i1_bf,
    input  wire [16:0]  i1_t,
    input  wire [255:0] i2x_q0,
    input  wire [9:0]   i2x_e0,
    input  wire [255:0] i2x_q1,
    input  wire [9:0]   i2x_e1,
    input  wire         issue,
    input  wire [12:0]  a_ctr,
    input  wire         pq_idle,
    input  wire [15:0]  pq_row,
    input  wire [4:0]   pq_idx,
    input  wire [4:0]   pq_n,
    output wire         pv,
    output wire [31:0]  pval,
    output wire [15:0]  prow,
    output wire [4:0]   pseg,
    output wire [4:0]   pnseg,
    output wire         perr,
    output wire [2:0]   ppos,
    output wire [3:0]   pq_tree,
    output wire [2:0]   pq_pos,
    output wire         qy_bkf
);
    localparam integer NSEG = 8, NCH = 16, LV = 5, EARLY = 1, QZ_NS = 8, QZ_NE = 4;
    localparam [8:0] CUT = 9'b1_0111_1011;
    localparam integer SW = $clog2(NSEG);
    localparam integer TRW = SW + 1;
    localparam integer HW = $clog2(NCH);
    localparam integer LAT = 1 + CUT[0] + CUT[1] + CUT[2] + CUT[3] + CUT[4] + CUT[5] + CUT[6] + CUT[7] + CUT[8];
    localparam integer TW = HW + 3 + TRW + 6;
    localparam integer TG = 3 + TRW;

    function automatic [255:0] nib(input [127:0] c);
        integer i;
        begin
            nib = 256'd0;
            for (i = 0; i < 32; i = i + 1) nib[8*i +: 4] = c[4*i +: 4];
        end
    endfunction

    wire gclk;
    (* keep *) ot_hdc_cg u_cg (.clk(clk), .en(cg_en), .gclk(gclk));
    wire gclk_ma = gclk, gclk_mb = gclk, gclk_c1 = gclk, gclk_l0 = gclk, gclk_l1 = gclk;

    wire              mi2x_v, mi2x_bk, mi2_v, mi2_bk, mi2_bf;
    wire [TW-1:0]     mi2_t;
    wire              rst_m, rst_mc, rst_mp, rst_mt;
    wire [QZ_NS-1:0]  mz_bk, mz_fp4;
    wire [QZ_NE-1:0]  mz_c0, mz_c1;
    wire [255:0]      mz_q0, mz_q1;
    wire [9:0]        mz_e0, mz_e1;
    if (1) begin : g_mz
        ot_v41_kreg #(.W(1), .AR(1), .RV(1'b0)) u_rs (.clk(clk), .arst_n(rst_n_pin), .d(1'b1), .q(rst_m));
        ot_v41_kreg #(.W(1), .AR(1), .RV(1'b0)) u_rsc (.clk(clk), .arst_n(rst_n_pin), .d(1'b1), .q(rst_mc));
        ot_v41_kreg #(.W(1), .AR(1), .RV(1'b0)) u_rsp (.clk(clk), .arst_n(rst_n_pin), .d(1'b1), .q(rst_mp));
        ot_v41_kreg #(.W(1), .AR(1), .RV(1'b0)) u_rst (.clk(clk), .arst_n(rst_n_pin), .d(1'b1), .q(rst_mt));
        ot_v41_kreg #(.W(532)) u_x (.clk(gclk_ma), .arst_n(1'b1), .d({i2x_q0, i2x_e0, i2x_q1, i2x_e1}),
                                    .q({mz_q0, mz_e0, mz_q1, mz_e1}));
    end
    if (1) begin : g_mi
        wire          z2x_bf, z2_bk;
        wire [TW-1:0] z2x_t;
        ot_v41_kreg #(.W(1), .AR(1), .RV(1'b0)) u_v2x (.clk(gclk_ma), .arst_n(rst_m), .d(i1_v), .q(mi2x_v));
        ot_v41_kreg #(.W(TW + 2)) u_c2x (.clk(gclk_ma), .arst_n(1'b1), .d({i1_bk, i1_bf, i1_t}), .q({mi2x_bk, z2x_bf, z2x_t}));
        ot_v41_kreg #(.W(1), .AR(1), .RV(1'b0)) u_v3 (.clk(gclk_ma), .arst_n(rst_m), .d(mi2x_v), .q(mi2_v));
        ot_v41_kreg #(.W(TW + 2)) u_c2 (.clk(gclk_ma), .arst_n(1'b1), .d({mi2x_bk, z2x_bf, z2x_t}), .q({z2_bk, mi2_bf, mi2_t}));
        assign mi2_bk = z2_bk;
        genvar zk;
        for (zk = 0; zk < QZ_NS; zk = zk + 1) begin : g_ns
            ot_v41_kreg #(.W(2)) u_s (.clk(gclk_ma), .arst_n(1'b1), .d({mi2x_bk, z2x_t[0]}), .q({mz_bk[zk], mz_fp4[zk]}));
        end
        for (zk = 0; zk < QZ_NE; zk = zk + 1) begin : g_ne
            ot_v41_kreg #(.W(2), .AR(1), .RV(2'b00)) u_e (.clk(gclk_ma), .arst_n(rst_m), .d({i1_v && i1_bk, i1_v && !i1_bk}),
                                                          .q({mz_c1[zk], mz_c0[zk]}));
        end
    end

    wire [273:0] cap;
    if (1) begin : g_pp
        wire [273:0] rd0, rd1;
        reg  [273:0] cap0, cap1;
        ot_rom_4096x274_m8
`ifndef SYNTHESIS
            #(.INSTANCE($sformatf("%s_0", INSTANCE)))
`endif
            u_rom0 (.clk(gclk_ma), .ce_in(issue && !a_ctr[0]), .addr_in(a_ctr[12:1]), .rd_out(rd0));
        ot_rom_4096x274_m8
`ifndef SYNTHESIS
            #(.INSTANCE($sformatf("%s_1", INSTANCE)))
`endif
            u_rom1 (.clk(gclk_c1), .ce_in(issue && a_ctr[0]), .addr_in(a_ctr[12:1]), .rd_out(rd1));
        if (1) begin : g_cz
            genvar ck;
            for (ck = 0; ck < QZ_NE; ck = ck + 1) begin : g_e
                localparam integer LO = (274 * ck) / QZ_NE, HI = (274 * (ck + 1)) / QZ_NE;
                always @(posedge gclk_ma) if (mz_c0[ck]) cap0[HI-1:LO] <= rd0[HI-1:LO];
                always @(posedge gclk_c1) if (mz_c1[ck]) cap1[HI-1:LO] <= rd1[HI-1:LO];
            end
            for (ck = 0; ck < QZ_NS; ck = ck + 1) begin : g_s
                localparam integer LO = (274 * ck) / QZ_NS, HI = (274 * (ck + 1)) / QZ_NS;
                assign cap[HI-1:LO] = mz_bk[ck] ? cap1[HI-1:LO] : cap0[HI-1:LO];
            end
        end
    end
    wire [273:0]  lcap = cap;
    wire          l_v0 = mi2_v && mi2_t[2], l_v1 = mi2_v && mi2_t[1];
    wire [TW-1:0] l_t = mi2_t;
    wire [255:0]  l_xq0 = mz_q0, l_xq1 = mz_q1;
    wire [9:0]    l_xe0 = mz_e0, l_xe1 = mz_e1;
    wire [255:0] w0q;
    wire [7:0]   w0e;
    if (1) begin : g_wz
        wire [255:0] w0n = nib(lcap[127:0]);
        genvar wk;
        for (wk = 0; wk < QZ_NS; wk = wk + 1) begin : g_s
            localparam integer LO = (256 * wk) / QZ_NS, HI = (256 * (wk + 1)) / QZ_NS;
            assign w0q[HI-1:LO] = mz_fp4[wk] ? w0n[HI-1:LO] : lcap[HI-1:LO];
        end
        assign w0e = mz_fp4[0] ? lcap[135:128] : lcap[263:256];
    end
    wire [255:0] w1q = nib(lcap[263:136]);
    wire [7:0]   w1e = lcap[271:264];
    wire signed [9:0] we0 = $signed({2'b00, w0e}) - 10'sd127;
    wire signed [9:0] we1 = $signed({2'b00, w1e}) - 10'sd127;

    wire l0_v, l1_v, l0_f, l1_f;
    wire [31:0] l0_y, l1_y;
    wire [TW-1:0] l0_t, l1_t;
    if (1) begin : g_l3
        reg              r_v0, r_v1;
        reg [TW-1:0]     r_t;
        reg [255:0]      r_xq0, r_xq1, r_w0q, r_w1q;
        reg [9:0]        r_xe0, r_xe1;
        reg signed [9:0] r_we0, r_we1;
        always @(posedge gclk_ma or negedge rst_m) if (!rst_m) begin r_v0 <= 1'b0; r_v1 <= 1'b0; end
                                                else begin r_v0 <= l_v0; r_v1 <= l_v1; end
        always @(posedge gclk_ma) begin
            r_t <= l_t; r_xq0 <= l_xq0; r_xq1 <= l_xq1; r_xe0 <= l_xe0; r_xe1 <= l_xe1;
            r_w0q <= w0q; r_w1q <= w1q; r_we0 <= we0; r_we1 <= we1;
        end
        ot_v41_bterm5_w10 #(.TW(TW), .FPC(32), .P0B(3)) u_l0 (.clk(gclk_l0), .rst_n(rst_m), .v(r_v0), .fp4(r_t[0]),
            .xq(r_xq0), .xe(r_xe0), .wq(r_w0q), .we(r_we0), .tag(r_t), .ov(l0_v), .y(l0_y), .f(l0_f), .otag(l0_t));
        ot_v41_bterm5_w10 #(.TW(TW), .FP4K(1), .P0B(3)) u_l1 (.clk(gclk_l1), .rst_n(rst_m), .v(r_v1), .fp4(1'b1),
            .xq(r_xq1), .xe(r_xe1), .wq(r_w1q), .we(r_we1), .tag(r_t), .ov(l1_v), .y(l1_y), .f(l1_f), .otag(l1_t));
    end
    wire c0_v, c1_v, c0_f, c1_f, c0_fault, c1_fault, t_fault;
    wire [31:0] c0_s, c1_s;
    wire [TG:0] c0_t, c1_t;
    wire [HW-1:0] ci_slot = l0_t[TW-1 -: HW], ci1_slot = l1_t[TW-1 -: HW];
    wire [TG:0]   ci_tag = {l0_t[TW-HW-1 -: TG], l0_t[3]}, ci1_tag = {l1_t[TW-HW-1 -: TG], l1_t[3]};
    if (1) begin : g_ch3
    ot_v41_chain4 #(.PD(1), .ND(QZ_NS / 2), .NCH(NCH), .TW(TG + 1), .CUT(CUT)) u_c0 (.clk(gclk_mb), .rst_n(rst_mc), .v(l0_v),
        .slot(ci_slot), .first(l0_t[5]), .last(l0_t[4]), .term(l0_y), .term_f(l0_f),
        .tag(ci_tag), .ov(c0_v), .osum(c0_s), .of(c0_f), .otag(c0_t), .fault(c0_fault));
    ot_v41_chain4 #(.PD(1), .ND(QZ_NS / 2), .NCH(NCH), .TW(TG + 1), .CUT(CUT)) u_c1 (.clk(gclk_mb), .rst_n(rst_mc), .v(l1_v),
        .slot(ci1_slot), .first(l1_t[5]), .last(l1_t[4]), .term(l1_y), .term_f(l1_f),
        .tag(ci1_tag), .ov(c1_v), .osum(c1_s), .of(c1_f), .otag(c1_t), .fault(c1_fault));
    end
    wire both = c0_v && c1_v;
    wire any = c0_v || c1_v;
    wire [TG:0] ct = c0_v ? c0_t : c1_t;
    wire [31:0] one = c0_v ? c0_s : c1_s;
    wire one_f = c0_v ? c0_f : c1_f;
    wire [31:0] pr_sum, pr_pass;
    wire [1:0] pr_err;
    wire pr_vo;
    if (1) begin : g_pa2
        ot_v41_fadd #(.CUT(CUT)) u_pair (.clk(gclk_mb), .rst_n(rst_mp), .valid_in(both), .a(c0_s), .b(c1_s),
            .y(pr_sum), .err(pr_err), .valid_out(pr_vo));
    end
    ot_hdc_delay #(.W(32), .D(LAT)) u_pp (.clk(gclk_mb), .rst_n(rst_mp), .d(one), .q(pr_pass));
    wire [TG+2:0] pr_t;
    ot_hdc_delay #(.W(TG + 3), .D(LAT)) u_pt (.clk(gclk_mb), .rst_n(rst_mp),
        .d({ct, both, both ? (c0_f | c1_f) : one_f}), .q(pr_t));
    reg [LAT-1:0] pr_vp;
    always @(posedge gclk_mb or negedge rst_mp)
        if (!rst_mp) pr_vp <= '0; else pr_vp <= {pr_vp[LAT-2:0], any};
    wire        b_v = pr_vp[LAT-1];
    wire [31:0] b_val = pr_t[1] ? pr_sum : pr_pass;
    wire        b_err = pr_t[0] | (pr_t[1] && pr_err != 2'd0);
    wire [TG:0] qq_t = pr_t[TG+2:2];
    wire [TG-1:0] b_tag = qq_t[TG:1];
    wire [TRW-1:0] b_tree = b_tag[TRW-1:0];
    wire [2:0]     b_pos = b_tag[TG-1 -: 3];
    wire        b_final = qq_t[0];

    wire t_v, t_err;
    wire [TRW-1:0] t_tree;
    wire [2:0]     t_pos;
    wire [31:0] t_val;
    if (1) begin : g_tr5
    ot_v41_segtree6 #(.CUT(CUT), .NT(NSEG << 1), .LV(LV), .EARLY(EARLY), .QD(8), .YF(1)) u_tree (.clk(clk), .rst_n(rst_mt), .ce(wen_t), .pclk(gclk_mb), .in_v(b_v),
        .in_tree(b_tree), .in_pos(b_pos), .in_val(b_val), .in_final(b_final), .in_err(b_err),
        .ov(t_v), .otree(t_tree), .opos(t_pos), .oval(t_val), .oerr(t_err), .fault(t_fault));
    end
    reg o_v, o_err;
    reg [31:0] o_val;
    reg [15:0] o_row;
    reg [4:0] o_seg, o_n;
    reg [2:0] o_pos;
    assign pq_tree = t_tree;
    assign pq_pos = t_pos;
    always @(posedge gclk_mb or negedge rst_mt) begin
        if (!rst_mt) o_v <= 1'b0;
        else o_v <= t_v && !pq_idle;
    end
    always @(posedge gclk_mb) begin
        o_val <= t_val; o_err <= t_err;
        o_row <= pq_row; o_seg <= pq_idx; o_n <= pq_n;
        o_pos <= t_pos;
    end
    if (1) begin : g_o2
        reg q_v, q_err; reg [31:0] q_val; reg [15:0] q_row; reg [4:0] q_seg, q_n; reg [2:0] q_pos;
        always @(posedge gclk_mb or negedge rst_mt) if (!rst_mt) q_v <= 1'b0; else q_v <= o_v;
        always @(posedge gclk_mb) begin q_err <= o_err; q_val <= o_val; q_row <= o_row; q_seg <= o_seg; q_n <= o_n; q_pos <= o_pos; end
        assign pv = q_v; assign pval = q_val; assign prow = q_row;
        assign pseg = q_seg; assign pnseg = q_n; assign perr = q_err;
        assign ppos = q_pos;
    end
    wire bk_fault = c0_fault | c1_fault | t_fault;
    if (1) begin : g_qyb
        reg bkf_r;
        always @(posedge clk or negedge rst_mt) if (!rst_mt) bkf_r <= 1'b0; else bkf_r <= bk_fault;
        assign qy_bkf = bkf_r;
    end
endmodule
