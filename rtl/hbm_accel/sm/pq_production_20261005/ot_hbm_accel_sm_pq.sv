`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hbm_accel_sm_pq: the DS HBM SM element ot_hbm_accel_sm_v ENABLE = 1 (main e1bf44f09) with PIPELINED ISSUE (PQ):
// op N+1 is accepted and launched while op N drains (ot_hbm_accel_issue_pq), the HBM counterpart of the ROM
// field-phase overlap.  Arithmetic, golden tree, per-op line order and x addressing relative to the op's x base are
// unchanged, so every result bit is identical.  Everything not marked PQ is ot_hbm_accel_sm_v's g_new body verbatim
// (the chains and channel modules are ot_hbm_accel_sm_v.sv's; compile both files).
//   * the leaf (ot_hbm_accel_smpq_leaf) selects its G1 output by the producing column's valid, not by the format of the
//     line entering it (the as-built select is only correct while one op is in the leaf);
// PQ changes against ot_hbm_accel_sm_v ENABLE = 1:
//   * start / op become a credit channel (ot_hbm_accel_smv_chan, like the descriptor port): `start` is a valid,
//     `start_ready` a registered credit decode; up to 2*PIO+3 ops may be posted ahead (in order);
//   * new op field `op_xb`: the op's x-store base.  The x read address is (op_xb + xa) mod XD, folded into the issue cursors, never added in s1
//     register (7-bit add).  The caller loads op N+1's x into a range disjoint from every op still issuing, so the
//     load overlaps op N (x-store ring, WAR-safe by allocation); op_xb = 0 for every op gives sm_v's addressing;
//   * the format and x base are latched at LAUNCH (the issue's pop), which is >= 1 edge after the previous op's last
//     line entered s1, so that line's unpack and format flags still see its own format (s1 -> DS chain capture);
//   * `busy` = an op is in setup, issuing or outstanding (as before for a single op); `arrive` toggles once per
//     completed op in op order; results leave in op order (the issue's retire-order hazard check guarantees it).
// Latency at the pins: start -> issue +PIO+1 (channel FIFO) as the descriptor channel; everything else unchanged.
// ---------------------------------------------------------------------------
module ot_hbm_accel_sm_pq #(
    parameter integer ENABLE = 0, PQ_ENABLE = 0,
    parameter integer PACK_W2 = 0,       // Erdos finite FP4 pair address hook
    parameter integer XMAP = 0,         // Pauli static layout; original leaf remains selected by default
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
    parameter integer PIO  = 2,         // boundary stages between the pins and the hub, each way
    parameter integer HAZ  = 1,         // PQ: retire-order hazard check (0 = negative test only)
    parameter integer NOUT = 4,         // PQ: outstanding ops in the issue
    parameter integer G1ASB = 0         // PQ negative test only: 1 = the as-built leaf G1 select (by entering format)
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    start,
    output wire                    start_ready,   // PQ
    input  wire [$clog2(RMAX):0]   op_rows,
    input  wire [15:0]             op_c,
    input  wire [7:0]              op_g,
    input  wire                    op_gs,
    input  wire [1:0]              op_fmt,
    input  wire                    op_pack_w2,    // same posted op tuple, not source ownership
    input  wire [6:0]              op_pack_delta_x,
    input  wire [$clog2(XD)-1:0]   op_xb,         // PQ: x-store base of the op
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
    generate if (!ENABLE || !PQ_ENABLE) begin : g_legacy
        // No posted handshake in the unchanged legacy pulse-start protocol.
        assign start_ready = 1'b0;
        ot_hbm_accel_sm_v #(.ENABLE(ENABLE),.SUB(SUB),.LBS(LBS),.LSB(LSB),.NC(NC),.IL(IL),.RMAX(RMAX),.LEV(LEV),.XD(XD),.MAX_OUT(MAX_OUT),.TCK(TCK),.DS(DS),.DW(DW),.DG(DG),.PIO(PIO)) u_legacy (.*);
    end else begin : g_pq
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
    // PQ: start / op as a credit channel (in-order op queue at the hub side)
    localparam integer OPX = OPW + XW;
    localparam integer OPQW = OPX + ((PACK_W2 != 0) ? 8 : 0);
    wire          h_start, h_pop;
    wire [OPQW-1:0] op_payload, h_payload;
    wire [OPX-1:0] h_opx = h_payload[OPX-1:0];
    wire [7:0] h_pack;
    if (PACK_W2 != 0) begin : g_pack_payload
        assign op_payload = {op_pack_w2, op_pack_delta_x, op_rows, op_c, op_g, op_gs, op_fmt, op_xb};
        assign h_pack = h_payload[OPX +: 8];
    end else begin : g_plain_payload
        assign op_payload = {op_rows, op_c, op_g, op_gs, op_fmt, op_xb};
        assign h_pack = 8'b0;
    end
    ot_hbm_accel_smv_chan #(.W(OPQW), .P(PIO), .DEPTH(CHD)) u_sch (.clk(clk), .rst_n(rst_n),
        .s_valid(start), .s_ready(start_ready), .s_data(op_payload),
        .m_valid(h_start), .m_ready(h_pop), .m_data(h_payload));
    wire [OPW-1:0] h_op = h_opx[XW +: OPW];
    wire [XW-1:0]  h_xb = h_opx[XW-1:0];
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
        if (!rst_n) begin fmt_q <= 2'd0; end
        else if (h_pop) begin fmt_q <= h_fmt; end
    ot_hbm_accel_issue_pq #(.ENABLE(1), .PQ_ENABLE(1), .IL(IL), .RMAX(RMAX), .XDEPTH(XD), .NOUT(NOUT), .HAZ(HAZ)) u_issue (
        .clk(clk), .rst_n(rst_n), .start_v(h_start), .launch(h_pop), .op_rows(h_rows), .op_c(h_c), .op_g(h_g),
        .op_gs(h_gs), .op_xb(h_xb), .op_bf(h_fmt == 2'd0),
        .w_valid(w_valid), .x_rdy(1'b1), .w_ready(w_ready), .rdone(sv), .busy(h_busy), .iss_v(adv),
        .iss_row_ok(row_ok), .iss_slot(si), .iss_row(row_now), .iss_first(i_first), .iss_last(i_last),
        .iss_glast(i_glast), .iss_rev_end(), .xa(xa), .arrive(h_arrive), .release_in(h_release),
        .released(h_released), .hz_wait());
    ot_hbm_accel_smv_chain #(.W(3), .D(PIO), .RST(1)) u_pbz (.clk(clk), .rst_n(rst_n),
        .d({h_busy, h_arrive, h_released}), .q({busy, arrive, released}));

    // Capture pair metadata at actual issue launch; later queue heads cannot change it.
    // Active proves the finite instruction shape only, never input-span ownership.
    wire [XW-1:0] selected_xa;
    wire pack_bad_head, pack_xa_fault;
    if (PACK_W2 != 0) begin : g_pack_address
        if (XD != 128 || IL != 8) begin : g_bad_shape
            initial $fatal(1, "PACK_W2 requires XD128/IL8");
        end
        wire head_shape = h_rows == 4 && h_c == 8 && h_g == 2 && h_fmt == 2'd2 && h_gs;
        reg pair_active;
        reg [6:0] pair_delta;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) pair_active <= 1'b0;
            else if (h_pop) pair_active <= h_pack[7] && head_shape;
        always @(posedge clk) if (h_pop) pair_delta <= h_pack[6:0];
        assign pack_bad_head = h_pop && h_pack[7] && !head_shape;
        ot_hbm_accel_w2_address_hook #(.ENABLE(PACK_W2), .RW(RW)) u_address (
            .pair_active(pair_active), .pair_shape_bound(pair_active), .pair_delta(pair_delta),
            .issue_v(adv), .issue_row_ok(row_ok), .virtual_row(row_now),
            .absolute_xa(xa), .selected_xa(selected_xa), .fault(pack_xa_fault));
    end else begin : g_plain_address
        assign selected_xa = xa;
        assign pack_bad_head = 1'b0;
        assign pack_xa_fault = 1'b0;
    end

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
        s1_xa <= selected_xa; // absolute issue address; optional pair delta before existing s1 capture
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
                if (XMAP != 0) begin : g_xmap
                ot_hbm_accel_smpq_xmap_leaf #(.SUB(SUB), .LBS(LBS), .LSB(LSB), .NC(NC), .IL(IL), .TAGW(TAGW), .XD(XD),
                                        .NBEAT(NBEAT), .COL(c), .SP(sp), .TCK(TCK), .XMAP(XMAP), .G1ASB(G1ASB)) u_leaf (
                    .clk(clk), .rst_n(rst_n), .c_in(c2), .w_in(w2), .x_ce(x2[0]), .x_addr(x2[1 +: XW]),
                    .b_en(b2[0]), .b_addr(b2[1 +: XW]), .b_oh(b2[1 + XW +: NBEAT]), .b_data(b2[1 + XW + NBEAT +: 2048]),
                    .gv(gv1), .gy(gy1), .gt(gt1), .gf(gf1));
                end else begin : g_original_layout
                ot_hbm_accel_smpq_leaf #(.SUB(SUB), .LBS(LBS), .LSB(LSB), .NC(NC), .IL(IL), .TAGW(TAGW), .XD(XD),
                                        .NBEAT(NBEAT), .COL(c), .SP(sp), .TCK(TCK), .G1ASB(G1ASB)) u_leaf (
                    .clk(clk), .rst_n(rst_n), .c_in(c2), .w_in(w2), .x_ce(x2[0]), .x_addr(x2[1 +: XW]),
                    .b_en(b2[0]), .b_addr(b2[1 +: XW]), .b_oh(b2[1 + XW +: NBEAT]), .b_data(b2[1 + XW + NBEAT +: 2048]),
                    .gv(gv1), .gy(gy1), .gt(gt1), .gf(gf1));
                end
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
        else begin rv_q <= cv[0]; fault_q <= fault_q | (|cf) | pack_bad_head | pack_xa_fault; end
    end
    always @(posedge clk) begin rrow_q <= crow[RW-1:0]; rdata_q <= cy; end
    ot_hbm_accel_smv_chain #(.W(2), .D(PIO), .RST(1)) u_prv_o (.clk(clk), .rst_n(rst_n), .d({rv_q, fault_q}),
        .q({rv, fault}));
    ot_hbm_accel_smv_chain #(.W(RW + NC*32), .D(PIO), .RST(0)) u_prd_o (.clk(clk), .rst_n(rst_n),
        .d({rrow_q, rdata_q}), .q({rrow, rdata}));
    end endgenerate
endmodule

// ---------------------------------------------------------------------------
// ot_hbm_accel_smpq_leaf: ot_hbm_accel_smv_leaf (ot_hbm_accel_sm_v.sv) verbatim except the G1 select (marked PQ).
// One leaf of the successor SM: column COL, sub-partition SP.  Its x-store macros hold the pair's x slice
// (block-dot lanes then BF16 lanes, as ot_gpu_sm_v's fragment for (COL, SP)); the x-write beat is mapped onto
// it bit for bit with per-bit write masks.  Inputs arrive from the sub-half copies (L2); relative to L2's edge:
//   +1 (E3)  leaf line / control register; x-store read latched (address straight from L2)
//   +2 (E4)  x fragment, weight slice and control registers (the column macros' inputs; = ot_gpu_sm_v stage 2)
// Output G1: the column-tree input of this sub, selected by the op's format, registered.
// ---------------------------------------------------------------------------
(* keep_hierarchy *)
module ot_hbm_accel_smpq_leaf #(
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
    parameter integer TCK = 1,
    parameter integer G1ASB = 0
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
    // PQ: select by the column that produced the result (ot_gpu_sm_v's select on the block-dot valid), not by the
    // format of the line now entering the column: under pipelined issue the next op's format reaches E4 while the
    // previous op's results are still leaving the column macros.
    always @(posedge clk) begin
        gy <= (G1ASB != 0) ? (ibf ? fy : by) : (bov ? by : fy);
        gt <= (G1ASB != 0) ? (ibf ? ftag : btag) : (bov ? btag : ftag);
    end
endmodule
