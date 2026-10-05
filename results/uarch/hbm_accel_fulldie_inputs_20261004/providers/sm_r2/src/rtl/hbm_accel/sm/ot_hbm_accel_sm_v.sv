`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hbm_accel_sm_v: the DeepSeek-V4.1 HBM accelerator's SM element at 1.2 GHz SS (0.833 ns).
//
// ENABLE = 0 (default) instantiates W13's ot_gpu_sm_v unchanged.  ENABLE = 1 is the 1.2 GHz successor: the same
// arithmetic, issue order and golden tree (every result bit identical), with
//   * the routed-closed issue and bulk copy (ot_hbm_accel_issue / ot_hbm_accel_bulk_copy ENABLE = 1; the staging
//     ring as even/odd 512x256 macro groups, RING_MACRO = 1);
//   * the issue's combinational outputs (adv, xa) registered in the SM (stage s1) before they reach the x store;
//   * a LEAF per (column c, sub-partition sp): its block-dot and BF16 column macros, its own x-store macros holding
//     exactly that pair's x slice (NXL = ceil((LBS*266 + LSB*16) / 256) macros of 128 x 256; the fragment is
//     re-laid out per leaf so x never crosses the element), the unpacked weight slice of sp, the registered
//     combine-tree input (G1);
//   * pipelined, replicated (keep_hierarchy, never merged) distribution: s1 -> DS per-sub stages -> per-sub-half
//     copy (L2, up to 4 columns) -> leaf, the x-read address on the same schedule, the x-write beat through DW
//     per-sub stages; the column gather leaf G1 -> DG stages -> tree input; every leaf at the same depth (no skew);
//   * the column combine-tree input selected by the op's registered format (the two column types never run in one
//     op, so this equals ot_gpu_sm_v's select on sub 0's block-dot valid);
//   * a registered element boundary (the W13 die budget: inputs land in a flop, outputs leave one), PIO stages each
//     way between the pins and the hub: one-way pipes for start/op, rsp, release, results, busy, arrive, released;
//     credit-based pipelined channels (sink FIFO, credit return) for the descriptor and request handshakes.
// Cycles added (latency only; one issue a cycle and the ring's run-ahead are unchanged), DS = 3, DG = 3, PIO = 2:
//   start -> issue +PIO; issue setup +1 (ot_hbm_accel_issue); x read / weight to the column macros +DS+2
//   (s1, DS stages, L2, leaf E3; ot_gpu_sm_v reads x at the issue edge); column gather +DG+2 (G1, DG, tree input);
//   results -> pins +PIO; busy / arrive / released -> pins +PIO; release_in -> issue +PIO; HBM read response +PIO,
//   request +PIO+1 (credit channel).  x writes land 2+DW+2 edges after the beat (pin, DW stages, L2, leaf); a
//   fragment's last beat must precede `start` by >= 1 cycle (the first x read is >= PIO+DS+4 edges after start).
// ---------------------------------------------------------------------------
module ot_hbm_accel_sm_v #(
    parameter integer ENABLE = 0,
    parameter integer SUB  = 4,
    parameter integer LBS  = 2,
    parameter integer LSB  = 16,
    parameter integer NC   = 8,
    parameter integer IL   = 8,
    parameter integer RMAX = 4096,
    parameter integer LEV  = 4,
    parameter integer XD   = 128,
    parameter integer MAX_OUT = 512,
    parameter integer TCK  = 1,         // ENABLE = 1: BF16 column with the bubble gate off the multiplier's first
                                        // stage (ot_hbm_accel_tc16, bit-identical, 0 cycles); 0 = ot_gpu_tc16;
                                        // likewise the block-dot column with the FP4 decode in its input register
                                        // (ot_hbm_accel_bd_col / ot_hbm_accel_bterm2); 0 = ot_gpu_bd_col
    parameter integer DS   = 3,         // per-sub distribution stages between s1 and the sub-half copy
    parameter integer DW   = 4,         // per-sub x-write stages between the pin register and the sub-half copy
    parameter integer DG   = 3,         // gather stages between a leaf's G1 and its column's tree input
    parameter integer PIO  = 2          // boundary stages between the pins and the hub, each way
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    start,
    input  wire [$clog2(RMAX):0]   op_rows,
    input  wire [15:0]             op_c,
    input  wire [7:0]              op_g,
    input  wire                    op_gs,
    input  wire [1:0]              op_fmt,
    output wire                    busy,
    input  wire                    d_valid,
    output wire                    d_ready,
    input  wire [31:0]             d_base,
    input  wire [23:0]             d_lines,
    output wire                    req_v,
    input  wire                    req_ready,
    output wire [31:0]             req_addr,
    output wire [9:0]              req_tag,
    input  wire                    rsp_v,
    input  wire [9:0]              rsp_tag,
    input  wire [1087:0]           rsp_data,
    input  wire                    xw_en,
    input  wire [$clog2(XD)-1:0]   xw_addr,
    input  wire [6:0]              xw_grp,
    input  wire [8*256-1:0]        xw_data,
    output wire                    rv,
    output wire [$clog2(RMAX)-1:0] rrow,
    output wire [NC*32-1:0]        rdata,
    output wire                    fault,
    output wire                    arrive,
    input  wire                    release_in,
    output wire                    released
);
    generate if (ENABLE == 0) begin : g_original
        ot_gpu_sm_v #(.SUB(SUB), .LBS(LBS), .LSB(LSB), .NC(NC), .IL(IL), .RMAX(RMAX), .LEV(LEV), .XD(XD),
                      .MAX_OUT(MAX_OUT)) u_original (.*);
    end else begin : g_new
    localparam integer LB    = SUB * LBS;
    localparam integer LF    = SUB * LSB;
    localparam integer XC    = LB * 266 + LF * 16;     // x bits per column (the fragment layout of ot_gpu_sm_v)
    localparam integer FRAGW = NC * XC;
    localparam integer NBEAT = (FRAGW + 2047) / 2048;   // x-write beats per fragment
    localparam integer SW    = $clog2(IL);
    localparam integer RW    = $clog2(RMAX);
    localparam integer XW    = $clog2(XD);
    localparam integer TAGW  = RW + 1 + SW;
    localparam integer SLW   = LBS * 266 + LSB * 16;   // x slice of one leaf
    localparam integer WSW   = LBS * 256 + LBS * 10 + LSB * 16;   // unpacked weight slice of one sub
    localparam integer CW    = 6 + TAGW;               // control: iv_b, iv_f, first, last, fp4, bf16-op
    localparam integer HC    = 4;                       // columns per sub half (L2 group)
    localparam integer NH    = (NC + HC - 1) / HC;
    localparam integer OPW   = (RW + 1) + 16 + 8 + 1 + 2;
    localparam integer CHD   = 2 * PIO + 3;             // channel FIFO depth (credits): one transfer a cycle

    // ---------------- boundary: pins <-> hub ----------------
    wire          h_start;
    wire [OPW-1:0] h_op;
    ot_hbm_accel_smv_chain #(.W(1), .D(PIO), .RST(1)) u_pst (.clk(clk), .rst_n(rst_n), .d(start), .q(h_start));
    ot_hbm_accel_smv_chain #(.W(OPW), .D(PIO), .RST(0)) u_pop (.clk(clk), .rst_n(rst_n),
        .d({op_rows, op_c, op_g, op_gs, op_fmt}), .q(h_op));
    wire [RW:0] h_rows = h_op[OPW-1 -: RW+1];
    wire [15:0] h_c    = h_op[11 +: 16];
    wire [7:0]  h_g    = h_op[3 +: 8];
    wire        h_gs   = h_op[2];
    wire [1:0]  h_fmt  = h_op[1:0];
    wire h_rsp_v; wire [9:0] h_rsp_tag; wire [1087:0] h_rsp_data;
    ot_hbm_accel_smv_chain #(.W(1), .D(PIO), .RST(1)) u_prv (.clk(clk), .rst_n(rst_n), .d(rsp_v), .q(h_rsp_v));
    ot_hbm_accel_smv_chain #(.W(1098), .D(PIO), .RST(0)) u_prd (.clk(clk), .rst_n(rst_n), .d({rsp_tag, rsp_data}),
        .q({h_rsp_tag, h_rsp_data}));
    wire h_release;
    ot_hbm_accel_smv_chain #(.W(1), .D(PIO), .RST(1)) u_prl (.clk(clk), .rst_n(rst_n), .d(release_in), .q(h_release));
    // descriptor and request handshakes: credit channels (inputs land in a flop, ready / valid leave one)
    wire h_d_valid, h_d_ready; wire [55:0] h_d;
    ot_hbm_accel_smv_chan #(.W(56), .P(PIO), .DEPTH(CHD)) u_dch (.clk(clk), .rst_n(rst_n),
        .s_valid(d_valid), .s_ready(d_ready), .s_data({d_base, d_lines}),
        .m_valid(h_d_valid), .m_ready(h_d_ready), .m_data(h_d));
    wire h_req_v, h_req_ready; wire [31:0] h_req_addr; wire [9:0] h_req_tag;
    ot_hbm_accel_smv_chan #(.W(42), .P(PIO), .DEPTH(CHD)) u_rch (.clk(clk), .rst_n(rst_n),
        .s_valid(h_req_v), .s_ready(h_req_ready), .s_data({h_req_addr, h_req_tag}),
        .m_valid(req_v), .m_ready(req_ready), .m_data({req_addr, req_tag}));

    // ---------------- bulk copy (routed-closed successor) ----------------
    wire          w_valid, w_ready;
    wire [1087:0] w_data;
    ot_hbm_accel_bulk_copy #(.ENABLE(1), .LINE_BITS(1088), .DEPTH(1024), .MAX_OUT(MAX_OUT), .SRAM_RING(1),
                             .RING_MACRO(1)) u_bc (
        .clk(clk), .rst_n(rst_n), .d_valid(h_d_valid), .d_ready(h_d_ready), .d_base(h_d[55:24]), .d_lines(h_d[23:0]),
        .req_v(h_req_v), .req_ready(h_req_ready), .req_addr(h_req_addr), .req_tag(h_req_tag),
        .rsp_v(h_rsp_v), .rsp_tag(h_rsp_tag), .rsp_data(h_rsp_data),
        .s_valid(w_valid), .s_ready(w_ready), .s_data(w_data), .outstanding(), .idle());

    // ---------------- issue (routed-closed successor) ----------------
    reg  [1:0]  fmt_q;
    wire        sv, h_busy, h_arrive, h_released;
    wire        adv, row_ok, i_first, i_last, i_glast;
    wire [SW-1:0] si;
    wire [RW:0] row_now;
    wire [XW-1:0] xa;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fmt_q <= 2'd0;
        else if (h_start && !h_busy) fmt_q <= h_fmt;
    ot_hbm_accel_issue #(.ENABLE(1), .IL(IL), .RMAX(RMAX), .XDEPTH(XD)) u_issue (
        .clk(clk), .rst_n(rst_n), .start(h_start), .op_rows(h_rows), .op_c(h_c), .op_g(h_g), .op_gs(h_gs),
        .w_valid(w_valid), .x_rdy(1'b1), .w_ready(w_ready), .rdone(sv), .busy(h_busy), .iss_v(adv),
        .iss_row_ok(row_ok), .iss_slot(si), .iss_row(row_now), .iss_first(i_first), .iss_last(i_last),
        .iss_glast(i_glast), .iss_rev_end(), .xa(xa), .arrive(h_arrive), .release_in(h_release),
        .released(h_released));
    ot_hbm_accel_smv_chain #(.W(3), .D(PIO), .RST(1)) u_pbz (.clk(clk), .rst_n(rst_n),
        .d({h_busy, h_arrive, h_released}), .q({busy, arrive, released}));

    // ---------------- stage s1: the issue's outputs and the line, registered ----------------
    reg              s1_v, s1_first, s1_last;
    reg [TAGW-1:0]   s1_tag;
    reg [1087:0]     s1_w;
    reg [XW-1:0]     s1_xa;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s1_v <= 1'b0; s1_first <= 1'b0; s1_last <= 1'b0; end
        else begin s1_v <= adv && row_ok; s1_first <= i_first; s1_last <= i_last; end
    end
    always @(posedge clk) begin
        s1_tag <= {row_now[RW-1:0], i_glast, si};
        s1_w <= w_data;
        s1_xa <= xa;
    end

    // ---------------- x-write beat, registered at the pins ----------------
    reg              w0_en;
    reg [XW-1:0]     w0_addr;
    reg [NBEAT-1:0]  w0_oh;                 // one-hot beat group
    reg [2047:0]     w0_data;
    integer gq;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) w0_en <= 1'b0;
        else w0_en <= xw_en;
    always @(posedge clk) begin
        w0_addr <= xw_addr; w0_data <= xw_data;
        for (gq = 0; gq < NBEAT; gq = gq + 1) w0_oh[gq] <= (xw_grp == gq);
    end

    // ---------------- per sub: unpack, DS / DW stage chains ----------------
    localparam integer XBW = 1 + XW;                     // x-read bundle: ce, address
    localparam integer WBW = 1 + XW + NBEAT + 2048;      // x-write bundle
    wire [SUB*CW-1:0]  l1_c;
    wire [SUB*WSW-1:0] l1_w;
    wire [SUB*XBW-1:0] l1_x;
    wire [SUB*WBW-1:0] l1_b;
    wire bf_op = (fmt_q == 2'd0);
    genvar sp, h, c, q, bb;
    for (sp = 0; sp < SUB; sp = sp + 1) begin : g_sub
        // the sub's unpacked weight slice: {iwf (LSB x 16), iwe (LBS x 10), iwq (LBS x 256)}, as ot_gpu_sm_v stage 2
        wire [WSW-1:0] un;
        for (q = 0; q < LBS; q = q + 1) begin : g_q
            localparam integer J = sp * LBS + q;
            wire [255:0] fp4w, fp8w;
            for (bb = 0; bb < 32; bb = bb + 1) begin : g_b
                assign fp4w[8*bb +: 8] = {4'd0, s1_w[128*J + 4*bb +: 4]};
                assign fp8w[8*bb +: 8] = (J < LB / 2) ? s1_w[256*J + 8*bb +: 8] : 8'd0;
            end
            assign un[256*q +: 256] = (fmt_q == 2'd2) ? fp4w : fp8w;
            assign un[LBS*256 + 10*q +: 10] = {2'b00, s1_w[1024 + 8*J +: 8]} - 10'sd127;
        end
        assign un[LBS*266 +: LSB*16] = s1_w[sp*LSB*16 +: LSB*16];
        wire [CW-1:0] c_in = {s1_v && !bf_op, s1_v && bf_op, s1_first, s1_last, fmt_q == 2'd2, bf_op, s1_tag};
        ot_hbm_accel_smv_chain #(.W(2), .D(DS), .RST(1)) u_cv (.clk(clk), .rst_n(rst_n), .d(c_in[CW-1 -: 2]),
            .q(l1_c[CW*sp + CW - 2 +: 2]));
        ot_hbm_accel_smv_chain #(.W(CW-2), .D(DS), .RST(0)) u_cd (.clk(clk), .rst_n(rst_n), .d(c_in[CW-3:0]),
            .q(l1_c[CW*sp +: CW-2]));
        ot_hbm_accel_smv_chain #(.W(WSW), .D(DS), .RST(0)) u_w (.clk(clk), .rst_n(rst_n), .d(un),
            .q(l1_w[WSW*sp +: WSW]));
        ot_hbm_accel_smv_chain #(.W(1), .D(DS), .RST(1)) u_xv (.clk(clk), .rst_n(rst_n), .d(s1_v), .q(l1_x[XBW*sp]));
        ot_hbm_accel_smv_chain #(.W(XW), .D(DS), .RST(0)) u_xa (.clk(clk), .rst_n(rst_n), .d(s1_xa),
            .q(l1_x[XBW*sp + 1 +: XW]));
        ot_hbm_accel_smv_chain #(.W(1), .D(DW), .RST(1)) u_bv (.clk(clk), .rst_n(rst_n), .d(w0_en), .q(l1_b[WBW*sp]));
        ot_hbm_accel_smv_chain #(.W(WBW - 1), .D(DW), .RST(0)) u_bd (.clk(clk), .rst_n(rst_n),
            .d({w0_data, w0_oh, w0_addr}), .q(l1_b[WBW*sp + 1 +: WBW - 1]));
    end

    // ---------------- per sub half: L2 copies; leaves ----------------
    wire [NC*SUB-1:0]      g_v, g_f;
    wire [NC*SUB*32-1:0]   g_y;
    wire [NC*SUB*TAGW-1:0] g_t;
    for (sp = 0; sp < SUB; sp = sp + 1) begin : g_l2s
        for (h = 0; h < NH; h = h + 1) begin : g_h
            wire [CW-1:0]  c2;
            wire [WSW-1:0] w2;
            wire [XBW-1:0] x2;
            wire [WBW-1:0] b2;
            ot_hbm_accel_bc_kreg #(.W(2)) u_cv (.clk(clk), .rst_n(rst_n), .d(l1_c[CW*sp + CW - 2 +: 2]), .q(c2[CW-1 -: 2]));
            ot_hbm_accel_smv_pipe #(.W(CW-2)) u_cd (.clk(clk), .d(l1_c[CW*sp +: CW-2]), .q(c2[CW-3:0]));
            ot_hbm_accel_smv_pipe #(.W(WSW)) u_w (.clk(clk), .d(l1_w[WSW*sp +: WSW]), .q(w2));
            ot_hbm_accel_bc_kreg #(.W(1)) u_xv (.clk(clk), .rst_n(rst_n), .d(l1_x[XBW*sp]), .q(x2[0]));
            ot_hbm_accel_smv_pipe #(.W(XW)) u_xa (.clk(clk), .d(l1_x[XBW*sp + 1 +: XW]), .q(x2[1 +: XW]));
            ot_hbm_accel_bc_kreg #(.W(1)) u_bv (.clk(clk), .rst_n(rst_n), .d(l1_b[WBW*sp]), .q(b2[0]));
            ot_hbm_accel_smv_pipe #(.W(WBW - 1)) u_bd (.clk(clk), .d(l1_b[WBW*sp + 1 +: WBW - 1]),
                                                      .q(b2[1 +: WBW - 1]));
            for (c = h * HC; c < NC && c < (h + 1) * HC; c = c + 1) begin : g_c
                wire gv1, gf1; wire [31:0] gy1; wire [TAGW-1:0] gt1;
                ot_hbm_accel_smv_leaf #(.SUB(SUB), .LBS(LBS), .LSB(LSB), .NC(NC), .IL(IL), .TAGW(TAGW), .XD(XD),
                                        .NBEAT(NBEAT), .COL(c), .SP(sp), .TCK(TCK)) u_leaf (
                    .clk(clk), .rst_n(rst_n), .c_in(c2), .w_in(w2), .x_ce(x2[0]), .x_addr(x2[1 +: XW]),
                    .b_en(b2[0]), .b_addr(b2[1 +: XW]), .b_oh(b2[1 + XW +: NBEAT]), .b_data(b2[1 + XW + NBEAT +: 2048]),
                    .gv(gv1), .gy(gy1), .gt(gt1), .gf(gf1));
                // gather toward the hub
                ot_hbm_accel_smv_chain #(.W(2), .D(DG), .RST(1)) u_gv (.clk(clk), .rst_n(rst_n), .d({gv1, gf1}),
                    .q({g_v[c*SUB + sp], g_f[c*SUB + sp]}));
                ot_hbm_accel_smv_chain #(.W(32 + TAGW), .D(DG), .RST(0)) u_gd (.clk(clk), .rst_n(rst_n),
                    .d({gy1, gt1}), .q({g_y[32*(c*SUB + sp) +: 32], g_t[TAGW*(c*SUB + sp) +: TAGW]}));
            end
        end
    end

    // ---------------- per column: tree input register, combine tree, streaming stack ----------------
    wire [NC-1:0] cv, cf;
    wire [NC*32-1:0] cy;
    wire [NC*RW-1:0] crow;
    for (c = 0; c < NC; c = c + 1) begin : g_col
        reg              tv_in;
        reg [SUB*32-1:0] td_in;
        reg [TAGW-1:0]   tt_in;
        reg              gfault;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin tv_in <= 1'b0; gfault <= 1'b0; end
            else begin tv_in <= g_v[c*SUB]; gfault <= |g_f[c*SUB +: SUB]; end
        always @(posedge clk) begin
            td_in <= g_y[32*c*SUB +: 32*SUB];
            tt_in <= g_t[TAGW*c*SUB +: TAGW];
        end
        wire tv, tf;
        wire [31:0] ty;
        wire [TAGW-1:0] tt;
        ot_gpu_tree #(.N(SUB), .TAGW(TAGW), .ALAT(7)) u_comb (.clk(clk), .rst_n(rst_n), .v(tv_in), .d(td_in),
                                                              .tag(tt_in), .ov(tv), .y(ty), .otag(tt), .fault(tf));
        wire kf;
        ot_gpu_stack #(.LEV(LEV), .IL(IL), .TAGW(RW), .ALAT(7)) u_stack (
            .clk(clk), .rst_n(rst_n), .iv(tv), .d(ty), .ilast(tt[SW]), .islot(tt[SW-1:0]),
            .itag(tt[TAGW-1:SW+1]), .ov(cv[c]), .y(cy[32*c +: 32]), .otag(crow[RW*c +: RW]), .fault(kf));
        assign cf[c] = gfault | tf | kf;
    end
    assign sv = cv[0];
    reg              rv_q, fault_q;
    reg [RW-1:0]     rrow_q;
    reg [NC*32-1:0]  rdata_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rv_q <= 1'b0; fault_q <= 1'b0; end
        else begin rv_q <= cv[0]; fault_q <= fault_q | (|cf); end
    end
    always @(posedge clk) begin rrow_q <= crow[RW-1:0]; rdata_q <= cy; end
    ot_hbm_accel_smv_chain #(.W(2), .D(PIO), .RST(1)) u_prv_o (.clk(clk), .rst_n(rst_n), .d({rv_q, fault_q}),
        .q({rv, fault}));
    ot_hbm_accel_smv_chain #(.W(RW + NC*32), .D(PIO), .RST(0)) u_prd_o (.clk(clk), .rst_n(rst_n),
        .d({rrow_q, rdata_q}), .q({rrow, rdata}));
    end endgenerate
endmodule

// A plain register copy that synthesis keeps as its own instance (never merged with an identical copy), so a
// replicated distribution hop stays replicated.
(* keep_hierarchy *)
module ot_hbm_accel_smv_pipe #(
    parameter integer W = 1
) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    always @(posedge clk) q <= d;
endmodule

// D register stages (D >= 0), each its own kept instance so placement spreads them along the wire; RST = 1 resets
// them to 0 (valids), RST = 0 has no reset (data).
module ot_hbm_accel_smv_chain #(
    parameter integer W = 1,
    parameter integer D = 1,
    parameter integer RST = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    wire [W*(D+1)-1:0] t;
    assign t[W-1:0] = d;
    genvar i;
    generate for (i = 0; i < D; i = i + 1) begin : g_s
        if (RST != 0) begin : g_r
            ot_hbm_accel_bc_kreg #(.W(W)) u (.clk(clk), .rst_n(rst_n), .d(t[W*i +: W]), .q(t[W*(i+1) +: W]));
        end else begin : g_n
            ot_hbm_accel_smv_pipe #(.W(W)) u (.clk(clk), .d(t[W*i +: W]), .q(t[W*(i+1) +: W]));
        end
    end endgenerate
    assign q = t[W*D +: W];
endmodule

// A valid/ready channel stretched over P register stages each way: the source holds DEPTH credits (s_ready = a
// credit is left), a transfer travels P stages into the sink's DEPTH-entry FIFO, every FIFO pop returns its credit
// through P stages.  DEPTH >= 2P + 3 sustains one transfer a cycle.  Order and data are unchanged; the latency is
// P + 1 (FIFO) edges.  Both ends are registered: s_ready is a decode of the credit counter, m_valid of the FIFO
// count, m_data the FIFO head selected by a registered pointer.
module ot_hbm_accel_smv_chan #(
    parameter integer W = 8,
    parameter integer P = 2,
    parameter integer DEPTH = 7
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         s_valid,
    output wire         s_ready,
    input  wire [W-1:0] s_data,
    output wire         m_valid,
    input  wire         m_ready,
    output wire [W-1:0] m_data
);
    localparam integer CW = $clog2(DEPTH + 1);
    localparam integer AW = (DEPTH <= 1) ? 1 : $clog2(DEPTH);
    reg  [CW-1:0] cred;
    wire          fire = s_valid && s_ready;
    wire          ret;
    assign s_ready = (cred != 0);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) cred <= DEPTH[CW-1:0];
        else cred <= cred - fire + ret;
    wire          f_v;
    wire [W-1:0]  f_d;
    ot_hbm_accel_smv_chain #(.W(1), .D(P), .RST(1)) u_fv (.clk(clk), .rst_n(rst_n), .d(fire), .q(f_v));
    ot_hbm_accel_smv_chain #(.W(W), .D(P), .RST(0)) u_fd (.clk(clk), .rst_n(rst_n), .d(s_data), .q(f_d));
    reg  [W-1:0]  mem [0:DEPTH-1];
    reg  [AW-1:0] wp, rp;
    reg  [CW-1:0] cnt;
    wire          pop = m_valid && m_ready;
    assign m_valid = (cnt != 0);
    assign m_data = mem[rp];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wp <= 0; rp <= 0; cnt <= 0; end
        else begin
            if (f_v) wp <= (wp == DEPTH - 1) ? {AW{1'b0}} : wp + 1'b1;
            if (pop) rp <= (rp == DEPTH - 1) ? {AW{1'b0}} : rp + 1'b1;
            cnt <= cnt + f_v - pop;
        end
    always @(posedge clk) if (f_v) mem[wp] <= f_d;
    ot_hbm_accel_smv_chain #(.W(1), .D(P), .RST(1)) u_cr (.clk(clk), .rst_n(rst_n), .d(pop), .q(ret));
endmodule

// ---------------------------------------------------------------------------
// One leaf of the successor SM: column COL, sub-partition SP.  Its x-store macros hold the pair's x slice
// (block-dot lanes then BF16 lanes, as ot_gpu_sm_v's fragment for (COL, SP)); the x-write beat is mapped onto
// it bit for bit with per-bit write masks.  Inputs arrive from the sub-half copies (L2); relative to L2's edge:
//   +1 (E3)  leaf line / control register; x-store read latched (address straight from L2)
//   +2 (E4)  x fragment, weight slice and control registers (the column macros' inputs; = ot_gpu_sm_v stage 2)
// Output G1: the column-tree input of this sub, selected by the op's format, registered.
// ---------------------------------------------------------------------------
(* keep_hierarchy *)
module ot_hbm_accel_smv_leaf #(
    parameter integer SUB = 4,
    parameter integer LBS = 2,
    parameter integer LSB = 16,
    parameter integer NC  = 8,
    parameter integer IL  = 8,
    parameter integer TAGW = 16,
    parameter integer XD  = 128,
    parameter integer NBEAT = 13,
    parameter integer COL = 0,
    parameter integer SP  = 0,
    parameter integer TCK = 1
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire [6+TAGW-1:0]        c_in,
    input  wire [LBS*266+LSB*16-1:0] w_in,
    input  wire                     x_ce,
    input  wire [$clog2(XD)-1:0]    x_addr,
    input  wire                     b_en,
    input  wire [$clog2(XD)-1:0]    b_addr,
    input  wire [NBEAT-1:0]         b_oh,
    input  wire [2047:0]            b_data,
    output reg                      gv,
    output reg  [31:0]              gy,
    output reg  [TAGW-1:0]          gt,
    output reg                      gf
);
    localparam integer LB  = SUB * LBS;
    localparam integer XC  = LB * 266 + SUB * LSB * 16;
    localparam integer SLW = LBS * 266 + LSB * 16;
    localparam integer WSW = SLW;
    localparam integer NXL = (SLW + 255) / 256;
    localparam integer XW  = $clog2(XD);
    localparam integer CW  = 6 + TAGW;
    // ---- E3: line and control ----
    reg  [1:0]     c3v;                 // iv_b, iv_f
    reg  [CW-3:0]  c3d;                 // first, last, fp4, bf16-op, tag
    reg  [WSW-1:0] w3;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) c3v <= 2'b00;
        else c3v <= c_in[CW-1:CW-2];
    always @(posedge clk) begin c3d <= c_in[CW-3:0]; w3 <= w_in; end
    // ---- x write: the beat's bits of this slice, per-bit masks from the one-hot beat group ----
    reg               we_q;
    reg [XW-1:0]      wa_q;
    reg [NBEAT-1:0]   woh_q;
    reg [SLW-1:0]     wd_q;
    wire [SLW-1:0]    wd_n;
    wire [NXL*256-1:0] wd_m, wm_m;
    genvar b, m, qq;
    generate for (b = 0; b < SLW; b = b + 1) begin : g_wb
        // fragment bit of slice bit b (ot_gpu_sm_v layout)
        localparam integer F = (b < LBS * 266) ? COL * XC + (SP * LBS + b / 266) * 266 + (b % 266)
                                                : COL * XC + LB * 266 + SP * LSB * 16 + (b - LBS * 266);
        assign wd_n[b] = b_data[F % 2048];
        assign wd_m[b] = wd_q[b];
        assign wm_m[b] = woh_q[F / 2048];
    end
    for (b = SLW; b < NXL * 256; b = b + 1) begin : g_pad
        assign wd_m[b] = 1'b0;
        assign wm_m[b] = 1'b0;
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if (!rst_n) we_q <= 1'b0;
        else we_q <= b_en;
    always @(posedge clk) begin wa_q <= b_addr; woh_q <= b_oh; wd_q <= wd_n; end
    // ---- x store: NXL macros, read from the L2 address (latched at E3) ----
    wire [NXL*256-1:0] xrd;
    generate for (m = 0; m < NXL; m = m + 1) begin : g_xm
        ot_sram_1r1w_128x256_m1_r2c2 u_x (
            .clk(clk), .r_ce_in(x_ce), .r_addr_in(x_addr), .rd_out(xrd[256*m +: 256]),
            .w_ce_in(we_q && (|(wm_m[256*m +: 256]))), .w_addr_in(wa_q), .wd_in(wd_m[256*m +: 256]),
            .w_mask_in(wm_m[256*m +: 256]),
            .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    // ---- E4: the column macros' input registers (ot_gpu_sm_v stage 2) ----
    reg              iv_b, iv_f, ifirst, ilast, ifp4, ibf;
    reg [TAGW-1:0]   itag;
    reg [WSW-1:0]    iw;
    reg [SLW-1:0]    ix;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin iv_b <= 1'b0; iv_f <= 1'b0; end
        else begin iv_b <= c3v[1]; iv_f <= c3v[0]; end
    end
    always @(posedge clk) begin
        ifirst <= c3d[CW-3]; ilast <= c3d[CW-4]; ifp4 <= c3d[CW-5]; ibf <= c3d[CW-6]; itag <= c3d[TAGW-1:0];
        iw <= w3;
        ix <= xrd[SLW-1:0];
    end
    // ---- the column macros ----
    wire bov, bfault, fov, ffault;
    wire [31:0] by, fy;
    wire [TAGW-1:0] btag, ftag;
    generate
        if (LBS == 2 && IL == 8 && TAGW == 16 && TCK != 0) begin : g_hbdk
            ot_hbm_accel_bd_col u_bd (
                .clk(clk), .rst_n(rst_n), .v(iv_b), .first(ifirst), .last(ilast), .fp4(ifp4), .tag(itag),
                .wq(iw[0 +: LBS*256]), .we(iw[LBS*256 +: LBS*10]), .xq({ix[266 +: 256], ix[0 +: 256]}),
                .xe({ix[266 + 256 +: 10], ix[256 +: 10]}),
                .ov(bov), .y(by), .otag(btag), .fault(bfault));
        end else if (LBS == 2 && IL == 8 && TAGW == 16) begin : g_hbd
            ot_gpu_bd_col u_bd (
                .clk(clk), .rst_n(rst_n), .v(iv_b), .first(ifirst), .last(ilast), .fp4(ifp4), .tag(itag),
                .wq(iw[0 +: LBS*256]), .we(iw[LBS*256 +: LBS*10]), .xq({ix[266 +: 256], ix[0 +: 256]}),
                .xe({ix[266 + 256 +: 10], ix[256 +: 10]}),
                .ov(bov), .y(by), .otag(btag), .fault(bfault));
        end else begin : g_sbd
            wire [LBS*256-1:0] xq_s;
            wire [LBS*10-1:0]  xe_s;
            for (qq = 0; qq < LBS; qq = qq + 1) begin : g_b
                assign xq_s[256*qq +: 256] = ix[qq*266 +: 256];
                assign xe_s[10*qq +: 10]   = ix[qq*266 + 256 +: 10];
            end
            if (TCK != 0) begin : g_k
                ot_hbm_accel_bd_col #(.LB(LBS), .IL(IL), .TAGW(TAGW)) u_bd (
                    .clk(clk), .rst_n(rst_n), .v(iv_b), .first(ifirst), .last(ilast), .fp4(ifp4), .tag(itag),
                    .wq(iw[0 +: LBS*256]), .we(iw[LBS*256 +: LBS*10]), .xq(xq_s), .xe(xe_s),
                    .ov(bov), .y(by), .otag(btag), .fault(bfault));
            end else begin : g_o
            ot_gpu_bd_col #(.LB(LBS), .IL(IL), .TAGW(TAGW)) u_bd (
                .clk(clk), .rst_n(rst_n), .v(iv_b), .first(ifirst), .last(ilast), .fp4(ifp4), .tag(itag),
                .wq(iw[0 +: LBS*256]), .we(iw[LBS*256 +: LBS*10]), .xq(xq_s), .xe(xe_s),
                .ov(bov), .y(by), .otag(btag), .fault(bfault));
            end
        end
        if (LSB == 16 && TAGW == 16 && IL == 8 && TCK != 0) begin : g_hardk
            ot_hbm_accel_tc16 u_tc (
                .clk(clk), .rst_n(rst_n), .v(iv_f), .first(ifirst), .last(ilast), .tag(itag),
                .w(iw[LBS*266 +: LSB*16]), .x(ix[LBS*266 +: LSB*16]),
                .ov(fov), .y(fy), .otag(ftag), .fault(ffault));
        end else if (LSB == 16 && TAGW == 16 && IL == 8) begin : g_hard
            ot_gpu_tc16 u_tc (
                .clk(clk), .rst_n(rst_n), .v(iv_f), .first(ifirst), .last(ilast), .tag(itag),
                .w(iw[LBS*266 +: LSB*16]), .x(ix[LBS*266 +: LSB*16]),
                .ov(fov), .y(fy), .otag(ftag), .fault(ffault));
        end else if (TCK != 0) begin : g_softk
            ot_hbm_accel_tc_col #(.L(LSB), .IL(IL), .TAGW(TAGW)) u_tc (
                .clk(clk), .rst_n(rst_n), .v(iv_f), .first(ifirst), .last(ilast), .tag(itag),
                .w(iw[LBS*266 +: LSB*16]), .x(ix[LBS*266 +: LSB*16]),
                .ov(fov), .y(fy), .otag(ftag), .fault(ffault));
        end else begin : g_soft
            ot_gpu_tc_col #(.L(LSB), .IL(IL), .TAGW(TAGW)) u_tc (
                .clk(clk), .rst_n(rst_n), .v(iv_f), .first(ifirst), .last(ilast), .tag(itag),
                .w(iw[LBS*266 +: LSB*16]), .x(ix[LBS*266 +: LSB*16]),
                .ov(fov), .y(fy), .otag(ftag), .fault(ffault));
        end
    endgenerate
    // ---- G1: this sub's combine-tree input, selected by the op's format (registered with the op) ----
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin gv <= 1'b0; gf <= 1'b0; end
        else begin gv <= bov | fov; gf <= bfault | ffault | (bov & fov); end
    always @(posedge clk) begin
        gy <= ibf ? fy : by;
        gt <= ibf ? ftag : btag;
    end
endmodule
