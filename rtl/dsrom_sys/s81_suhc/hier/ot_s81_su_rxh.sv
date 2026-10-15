`timescale 1ns/1ps
// ot_s81_su_rxh v2 (S-ELEM-C 2026-10-15): the RA / RB / QR / RW stop of the S81 SU slab (dsfd_sp_su_static /
// dsfd_sp_su_h, RXH 1, spine head) as a hardened CLUSTER, every child <= 15k clock sinks, every face registered on both
// sides, the parent wires only.  Arithmetic bit-identical to the flat tile ot_s81_su_rxt (same units, same operands,
// same rounding order); the cluster adds fixed pipeline stages only (a job runs alone; the static calendar takes the
// measured stage counts).
//
// v1 -> v2 (measured, structural):
//   * rxra (4 sqrt-softplus lanes in one leaf) = 80,137 sinks on one root, CTS 532 ps: one ot_hdc_v41x_softplus_s lane
//     alone is ~20k flops (exp 5.6k, Horner 5.5k, max(x,0) delay 3.4k, div 1.6k, u delay 1.4k, sqrt 1.2k), so a lane
//     is split at its u / u^2 point into a FRONT leaf ot_s81_su_rxsf (exp, t / (t + 2), u^2, max(x,0) to T_U2) and a
//     BACK leaf ot_s81_su_rxsb (Horner in u^2, 2 u p, max(x,0) + l, sqrt), ~10k sinks each, 16 + 16 leaves.  Seam:
//     front output flops + back input flops = +2 cycles on RA; fault pulses cross the same seam (same sampling as the
//     flat lane's |(vo & fault)).
//   * rxc (control) g2 = 11,378 sinks but setup -386 ps: the tap pin flops (N face) fed a serial 16-bit row-numbering
//     chain over 5 slots and a 5:1 x 512 b select straight into the E / W issue flops across a pin-limited 388.8 um
//     tile.  v2: slot classes from a registered pending-parameter count (popcount of <= 4 bits + a 3-bit compare), one
//     hot AND-OR selects, and ONE added register stage (stage B, the selected operand rows) between the tap and the
//     issue flops: +1 cycle on every RX kind.
//   * RW (kind 11, ffn.weights, ot_s81_su_rw; added to the flat tile after v1) was missing from v1: it now lives in the
//     RB leaf (both take the control's registered operand word xq_x), result on the same leaf result port.
// ---------------------------------------------------------------------------------------------------------------------
// RXC split (S-ELEM-C 2026-10-15, native audit of the CLOSED g4 route: R 368.1 / spread 67.2 ps, launch 265.5 > 220
// (xq_x), capture 201.3 > 190 (52 xa_r pins): one 11.6k-sink root over a pin-limited 280.8 x 367.2 tile).  Structural
// fix: the control becomes a wires-only composition of ONE control leaf (ot_s81_su_rxc_ctl: job/row context, issue
// valids, RW config, result valids/faults, write address/mask) and FOUR identical bit-slice data leaves
// (ot_s81_su_rxc_sl, hardened once, replicated).  Slice s owns bits [64s +: 64] and [256 + 64s +: 64] of every 512-bit
// row (the s-th 64-bit quarter of both 256-bit halves), so the QR coefficient select (coef word jj, 64-bit quarter s)
// is slice-local.  Every leaf captures dn_st / dn_kind / dn_v itself and runs an identical copy of the slot-class /
// row-context logic (ot_s81_su_rxc_seq, ~40 FF), so no select crosses a leaf boundary: same registers per bit, same
// stages, same cycles as the flat control (0 added cycles).  The control leaf captures only the parameter-row-0
// fields it uses (base, n, scale, k, off: 70 b per slot).
module ot_s81_su_rxc_seq #(parameter integer S_RD = 5) (
    input  wire                 clk, rst_n,
    input  wire                 dn_st_i,
    input  wire [3:0]           dn_kind_i,
    input  wire [S_RD-1:0]      dn_v_i,
    output reg                  dq_st,
    output reg  [3:0]           dq_kind,
    output reg  [S_RD-1:0]      dq_v,
    output reg  [3:0]           jk,
    output reg                  mine,
    output reg  [15:0]          rc,
    output reg  [2:0]           pend,
    output wire [3:0]           np,
    output reg  [S_RD-1:0]      sv, s0, s2,
    output reg  [S_RD*3-1:0]    sj,
    output wire                 xv, xtwo,
    output wire [15:0]          oi_a, nrc,
    output reg                  b_st, b_mine, b_xv, b_xtwo,
    output reg  [3:0]           b_jk, b_kind,
    output reg  [15:0]          b_oi
);
    localparam [3:0] K_RA = 8, K_RB = 9, K_QR = 10, K_RW = 11;
    always @(posedge clk) dq_kind <= dn_kind_i;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin dq_st <= 1'b0; dq_v <= 0; end
                                           else begin dq_st <= dn_st_i; dq_v <= dn_v_i; end
    assign np = (jk == K_QR) ? 4'd5 : 4'd1;
    function automatic [2:0] np_of(input [3:0] k); np_of = (k == K_QR) ? 3'd5 : 3'd1; endfunction
    // slot classes: cb[i] = valid slots below i; slot i is parameter row (rc + cb[i]) while cb[i] < pend, else operand
    // row cb[i] - pend of this cycle (the first is xin, the last of two or more is xin2)
    reg  [3*S_RD-1:0] cb;
    reg  [3:0]        nv;
    always @(*) begin : cls
        integer i;
        reg [3:0] c;
        c = 4'd0; sv = 0; s0 = 0; s2 = 0; sj = 0; cb = 0;
        for (i = 0; i < S_RD; i = i + 1) begin
            cb[3 * i +: 3] = c[2:0];
            if (dq_v[i]) begin
                if (c[2:0] < pend) begin sv[i] = 1'b1; sj[3 * i +: 3] = rc[2:0] + c[2:0]; end
                else if (c[2:0] == pend) s0[i] = 1'b1;
            end
            c = c + {3'd0, dq_v[i]};
        end
        nv = c;
        for (i = 0; i < S_RD; i = i + 1)
            if (dq_v[i] && {1'b0, cb[3 * i +: 3]} > {1'b0, pend} && ((dq_v >> (i + 1)) == 0)) s2[i] = 1'b1;
    end
    assign xv = {1'b0, nv} >= {2'b0, pend} + 5'd1;
    assign xtwo = {1'b0, nv} >= {2'b0, pend} + 5'd2;
    assign nrc = rc + {12'd0, nv};
    assign oi_a = rc + {13'd0, pend} - {12'd0, np};
    wire [3:0] pn = ({1'b0, pend} > nv) ? {1'b0, pend} - nv : 4'd0;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin jk <= 0; mine <= 0; rc <= 0; pend <= 3'd1; end
        else if (dq_st) begin
            jk <= dq_kind; rc <= 0; pend <= np_of(dq_kind);
            mine <= (dq_kind == K_RA || dq_kind == K_RB || dq_kind == K_QR || dq_kind == K_RW);
        end else if (mine) begin rc <= nrc; pend <= pn[2:0]; end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin b_st <= 0; b_mine <= 0; b_xv <= 0; b_xtwo <= 0; b_jk <= 0; b_kind <= 0; b_oi <= 0; end
        else begin
            b_st <= dq_st; b_kind <= dq_kind; b_mine <= mine; b_jk <= jk; b_xv <= xv; b_xtwo <= xtwo;
            b_oi <= oi_a;
        end
endmodule

// Bit-slice data leaf: one per 128-bit slice (bits [64s +: 64], [256 + 64s +: 64] of every row; the parent gathers).
module ot_s81_su_rxc_sl #(parameter integer S_RD = 5, QW = 2) (
    input  wire                   clk, rst_in,
    input  wire                   dn_st_i,
    input  wire [3:0]             dn_kind_i,
    input  wire [S_RD-1:0]        dn_v_i,
    input  wire [S_RD*128-1:0]    dn_d_i,
    output reg  [127:0]           xa_x,
    input  wire                   xa_vi,
    input  wire [127:0]           xa_r,
    output reg  [255:0]           xq_x,       // {e_b slice, e_x slice}
    output reg  [127:0]           xq_c, xq_s, // {table half 1 quarter s, table half 0 quarter s}
    input  wire [1:0]             xq_vi,
    input  wire [255:0]           xq_y,       // {row 1 slice, row 0 slice}
    input  wire                   xb_vi, xb_wi,
    input  wire [127:0]           xb_y,
    output reg  [127:0]           o_d, o_d2
);
    localparam [3:0] K_RA = 8, K_RB = 9, K_QR = 10, K_RW = 11;
    localparam integer MAXP = 5;
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    wire dq_st, mine, xv, xtwo, b_st, b_mine, b_xv, b_xtwo;
    wire [3:0] dq_kind, jk, np, b_jk, b_kind; wire [S_RD-1:0] dq_v, sv, s0, s2; wire [S_RD*3-1:0] sj;
    wire [15:0] rc, oi_a, nrc, b_oi; wire [2:0] pend;
    ot_s81_su_rxc_seq #(.S_RD(S_RD)) seq (.clk(clk), .rst_n(rst_n), .dn_st_i(dn_st_i), .dn_kind_i(dn_kind_i), .dn_v_i(dn_v_i),
        .dq_st(dq_st), .dq_kind(dq_kind), .dq_v(dq_v), .jk(jk), .mine(mine), .rc(rc), .pend(pend), .np(np),
        .sv(sv), .s0(s0), .s2(s2), .sj(sj), .xv(xv), .xtwo(xtwo), .oi_a(oi_a), .nrc(nrc),
        .b_st(b_st), .b_mine(b_mine), .b_xv(b_xv), .b_xtwo(b_xtwo), .b_jk(b_jk), .b_kind(b_kind), .b_oi(b_oi));
    // stage A: the tap data slice at the pins
    reg  [S_RD*128-1:0] dq_d;
    always @(posedge clk) dq_d <= dn_d_i;
    reg  [127:0] xin_a, xin2_a;
    always @(*) begin : sel
        integer i;
        xin_a = 128'd0; xin2_a = 128'd0;
        for (i = 0; i < S_RD; i = i + 1) begin
            xin_a  = xin_a  | ({128{s0[i]}} & dq_d[128 * i +: 128]);
            xin2_a = xin2_a | ({128{s2[i]}} & dq_d[128 * i +: 128]);
        end
    end
    // parameter rows 1..4 (the rope tables; row 0 fields live in the control leaf)
    reg  [127:0] prow [1:MAXP-1];
    reg  [MAXP-1:0]     phit;
    reg  [MAXP*128-1:0] pnew;
    always @(*) begin : psel
        integer i, jj;
        phit = 0; pnew = 0;
        for (jj = 1; jj < MAXP; jj = jj + 1)
            for (i = 0; i < S_RD; i = i + 1)
                if (sv[i] && sj[3 * i +: 3] == jj) begin
                    phit[jj] = 1'b1; pnew[128 * jj +: 128] = pnew[128 * jj +: 128] | dq_d[128 * i +: 128];
                end
    end
    integer j;
    always @(posedge clk)
        if (mine && !dq_st)
            for (j = 1; j < MAXP; j = j + 1) if (phit[j]) prow[j] <= pnew[128 * j +: 128];
    // stage B
    reg  [127:0] xin, xin2;
    always @(posedge clk) begin xin <= xin_a; xin2 <= xin2_a; end
    reg  [127:0] hold;
    wire         rbp = (b_jk == K_RB) && b_xtwo;
    wire         qrp = (QW > 1) && (b_jk == K_QR) && b_xtwo;
    wire [127:0] e_x = (b_jk == K_RB) ? (rbp ? xin : hold) : xin;
    wire [127:0] e_b = (rbp || qrp) ? xin2 : xin;
    always @(posedge clk)
        if (b_mine && !b_st && b_xv && b_jk == K_RB && !b_oi[0] && !b_xtwo) hold <= xin;
    always @(posedge clk) begin
        xa_x <= e_x;
        xq_x <= {e_b, e_x};
    end
    // QR coefficients, quarter s of coefficient word jj: word 0/1 = row 1 low/high half, 2/3 = row 2 low/high (cos);
    // rows 3/4 likewise (sin).  Kept copies of j as in the flat control (two used per slice).
    function automatic [63:0] coefq(input [1:0] jj, input [127:0] ra, input [127:0] rb);
        case (jj)
            2'd0: coefq = ra[63:0];
            2'd1: coefq = ra[127:64];
            2'd2: coefq = rb[63:0];
            default: coefq = rb[127:64];
        endcase
    endfunction
    (* keep *) reg [15:0] cj;
    always @(posedge clk) cj <= {8{oi_a[1:0]}};
    genvar gq;
    generate for (gq = 0; gq < 2; gq = gq + 1) begin : g_cf
        wire [1:0] jj = cj[2 * gq +: 2] + ((gq != 0) ? 2'd1 : 2'd0);
        always @(posedge clk) begin
            xq_c[64 * gq +: 64] <= coefq(jj, prow[1], prow[2]);
            xq_s[64 * gq +: 64] <= coefq(jj, prow[3], prow[4]);
        end
    end endgenerate
    // results from the leaves, captured at the pins; the result row slice
    reg a_vq, b_vq, b_wq; reg [1:0] q_vq; reg [127:0] a_rq, b_yq; reg [255:0] q_yq;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin a_vq <= 1'b0; q_vq <= 2'b00; b_vq <= 1'b0; b_wq <= 1'b0; end
        else begin a_vq <= xa_vi; q_vq <= xq_vi; b_vq <= xb_vi; b_wq <= xb_wi; end
    always @(posedge clk) begin a_rq <= xa_r; q_yq <= xq_y; b_yq <= xb_y; end
    wire [127:0] ed  = a_vq ? a_rq : b_vq ? b_yq : q_yq[127:0];
    wire [127:0] ed2 = q_yq[255:128];
    always @(posedge clk) begin o_d <= ed; o_d2 <= ed2; end
endmodule

// Control leaf: row/job context, engine issue valids, RW config, result valids / faults, write slot address / mask.
module ot_s81_su_rxc_ctl #(parameter integer S_RD = 5, QW = 2) (
    input  wire                   clk, rst_in,
    input  wire                   dn_st_i,
    input  wire [3:0]             dn_kind_i,
    input  wire [7:0]             dn_jid_i,
    input  wire [S_RD-1:0]        dn_v_i,
    input  wire [S_RD*70-1:0]     dn_f_i,     // per slot {d[160+:4], d[128+:4], d[96+:32], d[64+:16], d[0+:14]}
    output reg                    o_v,
    output reg  [13:0]            o_a,
    output reg  [15:0]            o_m,
    output reg                    o_v2,
    output reg  [13:0]            o_a2,
    output reg                    o_fu, o_fo, o_alive, o_den, o_rdy,
    output reg  [7:0]             o_rjid,
    output reg                    xa_v,
    input  wire                   xa_vi,
    input  wire [15:0]            xa_f,
    output reg  [1:0]             xq_v,
    input  wire [1:0]             xq_vi,
    input  wire [3:0]             xq_f,
    output reg                    xb_v, xw_st, xw_v, xw_last,
    output reg  [39:0]            xw_cfg,
    input  wire                   xb_vi, xb_wi,
    input  wire [15:0]            xb_m,
    input  wire                   xb_f
);
    localparam [3:0] K_RA = 8, K_RB = 9, K_QR = 10, K_RW = 11;
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    wire dq_st, mine, xv, xtwo, b_st, b_mine, b_xv, b_xtwo;
    wire [3:0] dq_kind, jk, np, b_jk, b_kind; wire [S_RD-1:0] dq_v, sv, s0, s2; wire [S_RD*3-1:0] sj;
    wire [15:0] rc, oi_a, nrc, b_oi; wire [2:0] pend;
    ot_s81_su_rxc_seq #(.S_RD(S_RD)) seq (.clk(clk), .rst_n(rst_n), .dn_st_i(dn_st_i), .dn_kind_i(dn_kind_i), .dn_v_i(dn_v_i),
        .dq_st(dq_st), .dq_kind(dq_kind), .dq_v(dq_v), .jk(jk), .mine(mine), .rc(rc), .pend(pend), .np(np),
        .sv(sv), .s0(s0), .s2(s2), .sj(sj), .xv(xv), .xtwo(xtwo), .oi_a(oi_a), .nrc(nrc),
        .b_st(b_st), .b_mine(b_mine), .b_xv(b_xv), .b_xtwo(b_xtwo), .b_jk(b_jk), .b_kind(b_kind), .b_oi(b_oi));
    // parameter row 0 fields
    reg  [S_RD*70-1:0] dq_f;
    always @(posedge clk) dq_f <= dn_f_i;
    reg  [69:0] p0;
    reg         p0hit;
    reg  [69:0] p0new;
    always @(*) begin : psel
        integer i;
        p0hit = 1'b0; p0new = 70'd0;
        for (i = 0; i < S_RD; i = i + 1)
            if (sv[i] && sj[3 * i +: 3] == 3'd0) begin p0hit = 1'b1; p0new = p0new | dq_f[70 * i +: 70]; end
    end
    always @(posedge clk) if (mine && !dq_st && p0hit) p0 <= p0new;
    wire [13:0] obase = p0[13:0];
    wire [15:0] p0_n = p0[14 +: 16];
    // engine issue
    wire isop = b_xv && b_mine;
    wire rbp = (b_jk == K_RB) && b_xtwo;
    wire e_v = isop && !b_st && b_jk != K_RW && (b_jk != K_RB || rbp || b_oi[0]);
    wire qrp = (QW > 1) && (b_jk == K_QR) && b_xtwo;
    wire iss_a = e_v && b_jk == K_RA;
    wire iss_q = e_v && b_jk == K_QR;
    wire iss_b = e_v && b_jk == K_RB;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin xa_v <= 1'b0; xq_v <= 2'b00; xb_v <= 1'b0; xw_st <= 1'b0; xw_v <= 1'b0; xw_last <= 1'b0; end
        else begin
            xa_v <= iss_a; xq_v <= {iss_q && qrp, iss_q}; xb_v <= iss_b;
            xw_st <= b_st && b_kind == K_RW;
            xw_v <= isop && !b_st && b_jk == K_RW;
            xw_last <= b_oi == p0_n - 16'd1;
        end
    always @(posedge clk) xw_cfg <= {p0[66 +: 4], p0[62 +: 4], p0[30 +: 32]};
    // results
    reg a_vq; reg [15:0] a_fq; reg [1:0] q_vq; reg [3:0] q_fq; reg b_vq, b_wq, b_fq; reg [15:0] b_mq;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin a_vq <= 1'b0; q_vq <= 2'b00; a_fq <= 16'd0; q_fq <= 4'd0; b_vq <= 1'b0; b_wq <= 1'b0; b_fq <= 1'b0; end
        else begin a_vq <= xa_vi; q_vq <= xq_vi; a_fq <= xa_f; q_fq <= xq_f; b_vq <= xb_vi; b_wq <= xb_wi; b_fq <= xb_f; end
    always @(posedge clk) b_mq <= xb_m;
    wire ev  = a_vq | (b_vq & !b_wq) | q_vq[0];
    wire ev2 = q_vq[1];
    wire rwv = b_vq & b_wq;
    wire ef  = |a_fq || b_fq || |q_fq;
    reg [15:0] wc;
    wire [13:0] wa = (jk == K_QR) ? obase + {wc[13:2], 5'd0} + 14'd28 + {12'd0, wc[1:0]} : obase + wc[13:0];
    wire [15:0] wc1 = wc + 16'd1;
    wire [13:0] wa2 = obase + {wc1[13:2], 5'd0} + 14'd28 + {12'd0, wc1[1:0]};
    always @(posedge clk) begin o_a <= rwv ? obase : wa; o_m <= rwv ? b_mq : 16'hFFFF; o_a2 <= wa2; end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            o_v <= 0; o_v2 <= 0; o_fu <= 0; o_fo <= 0; o_alive <= 0; o_den <= 0; o_rdy <= 0; o_rjid <= 0; wc <= 0;
        end else begin
            o_v <= ev | rwv; o_v2 <= ev2; o_alive <= 1'b1; o_den <= 1'b1; o_rdy <= 1'b0; o_rjid <= 8'd0;
            if (dq_st) wc <= 0; else if (ev) wc <= wc + (ev2 ? 16'd2 : 16'd1);
            if (ef) o_fu <= 1'b1;
            if (b_xtwo && b_mine && b_jk != K_RB && !(QW > 1 && b_jk == K_QR)) o_fo <= 1'b1;
        end
    end
`ifndef SYNTHESIS
    initial if (S_RD > 7) $fatal(1, "ot_s81_su_rxc_ctl: S_RD <= 7 (3-bit slot classes)");
    // shadow of the flat tile's serial row numbering: the slot classes must equal it every cycle
    always @(posedge clk) if (rst_n && mine && !dq_st) begin : shadow
        integer i; reg [15:0] c; reg fx, ft;
        c = rc; fx = 0; ft = 0;
        for (i = 0; i < S_RD; i = i + 1)
            if (dq_v[i]) begin
                if (c < {12'd0, np}) begin
                    if (!sv[i] || sj[3 * i +: 3] != c[2:0]) $display("RXC_SHADOW_FAIL param slot %0d", i);
                end else begin
                    if (fx) ft = 1;
                    else begin fx = 1; if (oi_a != c - {12'd0, np}) $display("RXC_SHADOW_FAIL oi"); end
                end
                c = c + 1;
            end
        if (fx != xv || ft != xtwo || c != nrc ||
            ({12'd0, pend} != ((rc < {12'd0, np}) ? {12'd0, np} - rc : 16'd0)))
            $display("RXC_SHADOW_FAIL classes rc=%0d pend=%0d", rc, pend);
    end
`endif
`ifdef SU_RX_TRACE_C
    reg [31:0] tr_cyc; reg tr_f, tr_e;
    always @(posedge clk) begin
        tr_cyc <= (!rst_n) ? 32'd0 : tr_cyc + 32'd1;
        if (dq_st) begin tr_f <= 1'b0; tr_e <= 1'b0; end
        if (isop && !b_st && !tr_f) begin tr_f <= 1'b1; $display("RXTR rxc %0d first_operand_issue", tr_cyc); end
        if (ev && !tr_e) begin tr_e <= 1'b1; $display("RXTR rxc %0d first_result", tr_cyc); end
    end
`endif
endmodule

// The RX control as a wires-only composition: control leaf + four bit-slice leaves (ports = the flat control's).
module ot_s81_su_rxc #(
    parameter integer S_RD = 5, LM = 5, LA = 4, XMUT = 0,
    parameter integer QW = 2                  // QR rope rows a cycle (2: rows j, j + 1 of a head on two read / write slots)
) (
    input  wire                   clk,
    input  wire                   rst_in,
    input  wire                   dn_st_i,
    input  wire [3:0]             dn_kind_i,
    input  wire [7:0]             dn_jid_i,
    input  wire [S_RD-1:0]        dn_v_i,
    input  wire [S_RD*512-1:0]    dn_d_i,
    output wire                   o_v,
    output wire [13:0]            o_a,
    output wire [15:0]            o_m,
    output wire [511:0]           o_d,
    output wire                   o_v2,
    output wire [13:0]            o_a2,
    output wire [511:0]           o_d2,
    output wire                   o_fu, o_fo, o_alive, o_den, o_rdy,
    output wire [7:0]             o_rjid,
    output wire                   xa_v,
    output wire [511:0]           xa_x,
    input  wire                   xa_vi,
    input  wire [511:0]           xa_r,
    input  wire [15:0]            xa_f,
    output wire [1:0]             xq_v,
    output wire [1023:0]          xq_x,
    output wire [511:0]           xq_c,
    output wire [511:0]           xq_s,
    input  wire [1:0]             xq_vi,
    input  wire [1023:0]          xq_y,
    input  wire [3:0]             xq_f,
    output wire                   xb_v, xw_st, xw_v, xw_last,
    output wire [39:0]            xw_cfg,
    input  wire                   xb_vi, xb_wi,
    input  wire [511:0]           xb_y,
    input  wire [15:0]            xb_m,
    input  wire                   xb_f
);
    wire [S_RD*70-1:0] dn_f;
    genvar i, s;
    generate for (i = 0; i < S_RD; i = i + 1) begin : g_f
        assign dn_f[70 * i +: 70] = {dn_d_i[512 * i + 160 +: 4], dn_d_i[512 * i + 128 +: 4], dn_d_i[512 * i + 96 +: 32],
                                     dn_d_i[512 * i + 64 +: 16], dn_d_i[512 * i +: 14]};
    end endgenerate
    ot_s81_su_rxc_ctl #(.S_RD(S_RD), .QW(QW)) u_ctl (.clk(clk), .rst_in(rst_in), .dn_st_i(dn_st_i), .dn_kind_i(dn_kind_i),
        .dn_jid_i(dn_jid_i), .dn_v_i(dn_v_i), .dn_f_i(dn_f), .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_v2(o_v2), .o_a2(o_a2),
        .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den), .o_rdy(o_rdy), .o_rjid(o_rjid),
        .xa_v(xa_v), .xa_vi(xa_vi), .xa_f(xa_f), .xq_v(xq_v), .xq_vi(xq_vi), .xq_f(xq_f),
        .xb_v(xb_v), .xw_st(xw_st), .xw_v(xw_v), .xw_last(xw_last), .xw_cfg(xw_cfg),
        .xb_vi(xb_vi), .xb_wi(xb_wi), .xb_m(xb_m), .xb_f(xb_f));
    generate for (s = 0; s < 4; s = s + 1) begin : g_sl
        wire [S_RD*128-1:0] d_s;
        for (i = 0; i < S_RD; i = i + 1) begin : g_d
            assign d_s[128 * i +: 128] = {dn_d_i[512 * i + 256 + 64 * s +: 64], dn_d_i[512 * i + 64 * s +: 64]};
        end
        wire [127:0] ax, cc, ss, od, od2; wire [255:0] qx;
        ot_s81_su_rxc_sl #(.S_RD(S_RD), .QW(QW)) u_sl (.clk(clk), .rst_in(rst_in), .dn_st_i(dn_st_i), .dn_kind_i(dn_kind_i),
            .dn_v_i(dn_v_i), .dn_d_i(d_s),
            .xa_x(ax), .xa_vi(xa_vi), .xa_r({xa_r[256 + 64 * s +: 64], xa_r[64 * s +: 64]}),
            .xq_x(qx), .xq_c(cc), .xq_s(ss), .xq_vi(xq_vi),
            .xq_y({xq_y[768 + 64 * s +: 64], xq_y[512 + 64 * s +: 64], xq_y[256 + 64 * s +: 64], xq_y[64 * s +: 64]}),
            .xb_vi(xb_vi), .xb_wi(xb_wi), .xb_y({xb_y[256 + 64 * s +: 64], xb_y[64 * s +: 64]}),
            .o_d(od), .o_d2(od2));
        assign {xa_x[256 + 64 * s +: 64], xa_x[64 * s +: 64]} = ax;
        assign {xq_x[768 + 64 * s +: 64], xq_x[512 + 64 * s +: 64], xq_x[256 + 64 * s +: 64], xq_x[64 * s +: 64]} = qx;
        assign {xq_c[256 + 64 * s +: 64], xq_c[64 * s +: 64]} = cc;
        assign {xq_s[256 + 64 * s +: 64], xq_s[64 * s +: 64]} = ss;
        assign {o_d[256 + 64 * s +: 64], o_d[64 * s +: 64]} = od;
        assign {o_d2[256 + 64 * s +: 64], o_d2[64 * s +: 64]} = od2;
    end endgenerate
endmodule

// RA lane FRONT leaf: x -> exp(-|x|) Horner -> u = t / (t + 2) -> u^2 (ot_hdc_v41x_softplus_s up to T_U2, the same
// units), max(x, 0) carried to T_U2; seam outputs registered.  Flat lane time t = this leaf's input-flop time t.
module ot_s81_su_rxsf #(parameter integer PCUT = 1) (
    input  wire        clk, rst_in,
    input  wire        i_v,
    input  wire [31:0] i_x,
    output reg         o_v,
    output reg  [31:0] o_u, o_u2, o_mx,
    output reg         o_f
);
    localparam integer LH = 4 + PCUT, LM = 3 + PCUT;
    localparam integer T_PN = 8 + PCUT + 6 * LH, T_U = T_PN + 19, T_U2 = T_U + LM;
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    reg v_q; reg [31:0] x_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) v_q <= 1'b0; else v_q <= i_v;
    always @(posedge clk) x_q <= i_x;
    wire [T_U2:0] vd;
    ot_hdc_vline #(.D(T_U2)) u_v (.clk(clk), .rst_n(rst_n), .v(v_q), .vd(vd));
    wire [31:0] p_pre, u, u2, u_d, mx_d;
    wire [8:0]  n_pre;
    wire f_exp, f_div, f_u2;
    ot_hdc_v41x_exp_s #(.PCUT(PCUT)) u_exp (.clk(clk), .rst_n(rst_n), .v(v_q), .x({1'b1, x_q[30:0]}), .y(), .vo(),
                             .p_pre(p_pre), .n_pre(n_pre), .fault(f_exp));
    ot_hdc_v41x_spdiv u_div (.clk(clk), .rst_n(rst_n), .v(vd[T_PN]), .p(p_pre), .n(n_pre), .y(u), .vo(), .fault(f_div));
    ot_hdc_fp32_mul_x2 #(.DOUBLE(0), .CUT(PCUT)) m_u2 (.clk(clk), .rst_n(rst_n), .v(vd[T_U]), .a(u), .b(u), .y(u2), .fault(f_u2));
    ot_hdc_delay #(.W(32), .D(T_U2 - T_U)) d_u (clk, rst_n, u, u_d);
    reg  [31:0] mx;
    wire x_nan = (x_q[30:23] == 8'hFF) && (x_q[22:0] != 23'd0);
    always @(posedge clk) mx <= (x_q[31] && !x_nan) ? 32'd0 : x_q;
    ot_hdc_delay #(.W(32), .D(T_U2 - 1)) d_mx (clk, rst_n, mx, mx_d);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin o_v <= 1'b0; o_f <= 1'b0; end
        else begin o_v <= vd[T_U2]; o_f <= f_exp | f_div | f_u2; end
    always @(posedge clk) begin o_u <= u_d; o_u2 <= u2; o_mx <= mx_d; end
endmodule

// RA lane BACK leaf: Horner in u^2 -> l = 2 u p -> sp = max(x, 0) + l -> r = sqrt(sp) (ot_hdc_v41x_softplus_s from
// T_U2, the same units); this leaf's time 0 (input flops) = flat T_U2 + 2.  o_f = |(vo & fault) as the flat lane leaf.
// MUT 1 (negative control): returns sp instead of sqrt(sp).
module ot_s81_su_rxsb #(parameter integer PCUT = 1, MUT = 0) (
    input  wire        clk, rst_in,
    input  wire        i_v,
    input  wire [31:0] i_u, i_u2, i_mx,
    input  wire        i_f,
    output reg         o_v,
    output reg  [31:0] o_r,
    output reg         o_f
);
    localparam integer LH = 4 + PCUT, LM = 3 + PCUT;
    localparam integer T_PN = 8 + PCUT + 6 * LH, T_U = T_PN + 19, T_U2 = T_U + LM, T_P = T_U2 + 8 * LH;
    localparam integer T_L = T_P + LM, T_SP = T_L + 2, DEPTH = T_SP + 16;
    localparam integer B = T_U2;              // this leaf's time 0
    localparam [32*9-1:0] C = {32'h3D70F0F1, 32'h3D888889, 32'h3D9D89D9, 32'h3DBA2E8C, 32'h3DE38E39,
                               32'h3E124925, 32'h3E4CCCCD, 32'h3EAAAAAB, 32'h3F800000};  // 1/17 .. 1/1
    function automatic [31:0] coef(input integer i); coef = C[32*(8-i) +: 32]; endfunction
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    reg v_q, f_q; reg [31:0] u_q, u2_q, mx_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin v_q <= 1'b0; f_q <= 1'b0; end else begin v_q <= i_v; f_q <= i_f; end
    always @(posedge clk) begin u_q <= i_u; u2_q <= i_u2; mx_q <= i_mx; end
    wire [DEPTH-B:0] vd;
    ot_hdc_vline #(.D(DEPTH - B)) u_v (.clk(clk), .rst_n(rst_n), .v(v_q), .vd(vd));
    wire [31:0] u2d [0:7];
    wire [31:0] pa  [0:8];
    wire [8:1]  hf;
    assign u2d[0] = u2_q;
    assign pa[0] = coef(0);
    genvar k;
    generate
        for (k = 1; k <= 8; k = k + 1) begin : g_h
            if (k < 8) begin : g_d
                ot_hdc_delay #(.W(32), .D(LH)) d_u2 (clk, rst_n, u2d[k-1], u2d[k]);
            end
            ot_hdc_hstep #(.K(coef(k)), .CUT(PCUT)) u_h (.clk(clk), .rst_n(rst_n), .v(vd[LH*(k-1)]),
                                            .a(pa[k-1]), .b(u2d[k-1]), .y(pa[k]), .vo(), .fault(hf[k]));
        end
    endgenerate
    wire [31:0] u_d, l, mx_d, spv, r, sp;
    wire f_l, f_sp, f_sq, f_sp_d;
    ot_hdc_delay #(.W(32), .D(T_P - B)) d_u (clk, rst_n, u_q, u_d);
    ot_hdc_fp32_mul_x2 #(.CUT(PCUT)) m_l (.clk(clk), .rst_n(rst_n), .v(vd[T_P - B]), .a(u_d), .b(pa[8]), .y(l), .fault(f_l));
    ot_hdc_delay #(.W(32), .D(T_L - B)) d_mx (clk, rst_n, mx_q, mx_d);
    ot_hdc_addpos2 a_sp (.clk(clk), .rst_n(rst_n), .v(vd[T_L - B]), .a(mx_d), .b(l), .y(spv), .fault(f_sp));
    ot_hdc_fsqrt4 u_sq (.clk(clk), .rst_n(rst_n), .v(vd[T_SP - B]), .a(spv), .y(r), .vo(), .fault(f_sq));
    ot_hdc_delay #(.W(32), .D(DEPTH - T_SP)) d_sp (clk, rst_n, spv, sp);
    ot_hdc_delay #(.W(1), .D(DEPTH - T_SP), .RESET(1)) d_fsp (clk, rst_n, f_sp, f_sp_d);
    wire fault = f_sp_d | f_sq | (|hf) | f_l | f_q;
    wire vo = vd[DEPTH - B];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin o_v <= 1'b0; o_f <= 1'b0; end
        else begin o_v <= vo; o_f <= vo & fault; end
    always @(posedge clk) o_r <= (MUT == 1) ? sp : r;
endmodule

// One QR row leaf: forward RoPE of QL / 2 pairs on QL lanes (2 multiplies + 1 add, BF16 RNE out), the flat core's
// units; i_c / i_s = the row's cos / sin coefficients (pair p at [32 p +: 32]); input and output pin flops.
// MUT 3 (bench negative control): the inverse rotation.
module ot_s81_su_rxqr #(
    parameter integer LM = 5, LA = 4, MUT = 0,
    parameter integer QL = 16                 // lanes of this leaf (even: a lane's rotation pair stays inside the leaf)
) (
    input  wire               clk, rst_in,
    input  wire               i_v,
    input  wire [32*QL-1:0]   i_x,
    input  wire [16*QL-1:0]   i_c, i_s,
    output reg                o_v,
    output reg  [32*QL-1:0]   o_y,
    output reg                o_f
);
    localparam integer LMR = LM + 1, LAR = (LA >= 5) ? LA : LA + 1;
    localparam integer DQ  = LMR + LAR + 1;
    function automatic [31:0] bf16(input [31:0] x);
        reg [32:0] s;
        begin
            s = {1'b0, x} + 33'h7FFF + {32'd0, x[16]};
            bf16 = {s[31:16], 16'd0};
        end
    endfunction
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    reg v_q; reg [32*QL-1:0] x_q; reg [16*QL-1:0] c_q, s_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) v_q <= 1'b0; else v_q <= i_v;
    always @(posedge clk) begin x_q <= i_x; c_q <= i_c; s_q <= i_s; end
    wire [DQ:0] vq;
    ot_hdc_vline #(.D(DQ)) u_vq (.clk(clk), .rst_n(rst_n), .v(v_q), .vd(vq));
    wire [32*QL-1:0] y; wire [QL-1:0] f;
    genvar l;
    integer g;
    generate for (l = 0; l < QL; l = l + 1) begin : g_qr
        localparam integer ODD = l % 2, P = l / 2;
        wire [31:0] cc = c_q[32 * P +: 32], sn = s_q[32 * P +: 32];
        wire [31:0] mine = x_q[32 * l +: 32], pair = x_q[32 * (ODD ? l - 1 : l + 1) +: 32];
        wire [31:0] sg = ((ODD != 0) ^ (MUT == 3)) ? sn : {~sn[31], sn[30:0]};
        wire [31:0] pp, qq, rs;
        wire f0, f1, f2;
        ot_hdc_qmul_lat #(LMR) u_p (clk, rst_n, v_q, mine, cc, pp, f0);
        ot_hdc_qmul_lat #(LMR) u_q (clk, rst_n, v_q, pair, sg, qq, f1);
        ot_dsrom_qadd #(.LAT(LAR)) u_a (clk, rst_n, vq[LMR], pp, qq, rs, f2);
        assign y[32 * l +: 32] = rs;
        assign f[l] = f0 | f1 | f2;
    end endgenerate
    reg [32*QL-1:0] yo;
    always @(posedge clk) for (g = 0; g < QL; g = g + 1) yo[32 * g +: 32] <= bf16(y[32 * g +: 32]);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin o_v <= 1'b0; o_f <= 1'b0; end
        else begin o_v <= vq[DQ]; o_f <= |f; end
    always @(posedge clk) o_y <= yo;
endmodule

// RB + RW leaf.  RB: 16 lanes score + bias (ot_dsrom_qadd, bit-identical to ot_s81_su_rxe), i_x = {bias, score}.
// RW: ot_s81_su_rw (ffn.weights, unchanged) on i_x[511:0], start / row / last / configuration from the control's
// registered issue flops.  One result port (a job runs alone): o_w marks RW's row (word mask o_m).
// MUT 2: RB drops the bias; MUT 4: RW skips route_scale (ot_s81_su_rw MUT 4).
module ot_s81_su_rxrb #(
    parameter integer LM = 5, LA = 4, MUT = 0
) (
    input  wire            clk, rst_in,
    input  wire            i_v,
    input  wire [1023:0]   i_x,
    input  wire            w_st, w_v, w_last,
    input  wire [39:0]     w_cfg,
    output reg             o_v,
    output reg             o_w,
    output reg  [511:0]    o_y,
    output reg  [15:0]     o_m,
    output reg             o_f
);
    localparam integer LAR = (LA >= 5) ? LA : LA + 1;
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    reg v_q, ws_q, wv_q, wl_q; reg [1023:0] x_q; reg [39:0] wc_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin v_q <= 1'b0; ws_q <= 1'b0; wv_q <= 1'b0; wl_q <= 1'b0; end
        else begin v_q <= i_v; ws_q <= w_st; wv_q <= w_v; wl_q <= w_last; end
    always @(posedge clk) begin x_q <= i_x; wc_q <= w_cfg; end
    wire [511:0] y; wire [15:0] f;
    genvar l;
    generate for (l = 0; l < 16; l = l + 1) begin : g_rb
        ot_dsrom_qadd #(.LAT(LAR)) u_a (clk, rst_n, v_q, x_q[32 * l +: 32], (MUT == 2) ? 32'd0 : x_q[512 + 32 * l +: 32],
                                        y[32 * l +: 32], f[l]);
    end endgenerate
    wire [LAR:0] vd;
    ot_hdc_vline #(.D(LAR)) u_v (.clk(clk), .rst_n(rst_n), .v(v_q), .vd(vd));
    wire        rwv, rwf; wire [511:0] rwd; wire [15:0] rwm;
    ot_s81_su_rw #(.LM(LM), .LA(LA), .MUT((MUT == 4) ? 4 : 0)) u_rw (
        .clk(clk), .rst_n(rst_n), .start(ws_q), .k_i(wc_q[39:36]), .scale_i(wc_q[31:0]), .off_i(wc_q[35:32]),
        .i_v(wv_q), .i_x(x_q[511:0]), .i_last(wl_q), .o_v(rwv), .o_d(rwd), .o_m(rwm), .fault(rwf));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin o_v <= 1'b0; o_w <= 1'b0; o_f <= 1'b0; end
        else begin o_v <= vd[LAR] | rwv; o_w <= rwv; o_f <= |f | rwf; end
    always @(posedge clk) begin o_y <= rwv ? rwd : y; o_m <= rwv ? rwm : 16'hFFFF; end
endmodule

// The cluster (wires only): control + 16 RA lanes (front + back leaf each) + 2 x QR row (2 leaves of QL lanes each)
// + the RB / RW leaf.  Ports = ot_s81_su_rxt at S_RD, QW 2.
module ot_s81_su_rxh #(
    parameter integer S_RD = 5, LM = 5, LA = 4, XMUT = 0,
    parameter integer QL = 8                  // QR lanes a leaf (16 / QL leaves a QR row; one 16-lane row = 23.8k sinks)
) (
    input  wire                   clk, rst_in,
    input  wire                   dn_st_i,
    input  wire [3:0]             dn_kind_i,
    input  wire [7:0]             dn_jid_i,
    input  wire [S_RD-1:0]        dn_v_i,
    input  wire [S_RD*512-1:0]    dn_d_i,
    output wire                   o_v,
    output wire [13:0]            o_a,
    output wire [15:0]            o_m,
    output wire [511:0]           o_d,
    output wire                   o_v2,
    output wire [13:0]            o_a2,
    output wire [511:0]           o_d2,
    output wire                   o_fu, o_fo, o_alive, o_den, o_rdy,
    output wire [7:0]             o_rjid
);
    wire xa_v; wire [511:0] xa_x, xa_r; wire [15:0] a_vo, a_f;
    wire [1:0] xq_v, xq_vi; wire [3:0] xq_f; wire [1023:0] xq_x, xq_y; wire [511:0] xq_c, xq_s;
    wire xb_v, xb_vi, xb_wi, xb_f, xw_st, xw_v, xw_last; wire [39:0] xw_cfg; wire [511:0] xb_y; wire [15:0] xb_m;
    ot_s81_su_rxc #(.S_RD(S_RD), .LM(LM), .LA(LA), .XMUT(XMUT), .QW(2)) u_c (
        .clk(clk), .rst_in(rst_in), .dn_st_i(dn_st_i), .dn_kind_i(dn_kind_i), .dn_jid_i(dn_jid_i), .dn_v_i(dn_v_i),
        .dn_d_i(dn_d_i), .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_v2(o_v2), .o_a2(o_a2), .o_d2(o_d2),
        .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den), .o_rdy(o_rdy), .o_rjid(o_rjid),
        .xa_v(xa_v), .xa_x(xa_x), .xa_vi(a_vo[0]), .xa_r(xa_r), .xa_f(a_f),
        .xq_v(xq_v), .xq_x(xq_x), .xq_c(xq_c), .xq_s(xq_s), .xq_vi(xq_vi), .xq_y(xq_y), .xq_f(xq_f),
        .xb_v(xb_v), .xw_st(xw_st), .xw_v(xw_v), .xw_last(xw_last), .xw_cfg(xw_cfg),
        .xb_vi(xb_vi), .xb_wi(xb_wi), .xb_y(xb_y), .xb_m(xb_m), .xb_f(xb_f));
    ot_s81_su_rxrb #(.LM(LM), .LA(LA), .MUT((XMUT == 2 || XMUT == 4) ? XMUT : 0)) u_b (.clk(clk), .rst_in(rst_in),
        .i_v(xb_v), .i_x(xq_x), .w_st(xw_st), .w_v(xw_v), .w_last(xw_last), .w_cfg(xw_cfg),
        .o_v(xb_vi), .o_w(xb_wi), .o_y(xb_y), .o_m(xb_m), .o_f(xb_f));
    genvar k;
    generate for (k = 0; k < 16; k = k + 1) begin : g_ra
        wire sv, sf; wire [31:0] su, su2, smx;
        ot_s81_su_rxsf #(.PCUT(1)) u_f (.clk(clk), .rst_in(rst_in), .i_v(xa_v), .i_x(xa_x[32 * k +: 32]),
            .o_v(sv), .o_u(su), .o_u2(su2), .o_mx(smx), .o_f(sf));
        ot_s81_su_rxsb #(.PCUT(1), .MUT(XMUT == 1 ? 1 : 0)) u_b (.clk(clk), .rst_in(rst_in), .i_v(sv), .i_u(su),
            .i_u2(su2), .i_mx(smx), .i_f(sf), .o_v(a_vo[k]), .o_r(xa_r[32 * k +: 32]), .o_f(a_f[k]));
    end endgenerate
    localparam integer NQ = 16 / QL;
    generate for (k = 0; k < 2; k = k + 1) begin : g_qr
        wire [NQ-1:0] q_vo, q_f;
        genvar j;
        for (j = 0; j < NQ; j = j + 1) begin : g_ql
            ot_s81_su_rxqr #(.LM(LM), .LA(LA), .MUT(XMUT == 3 ? 3 : 0), .QL(QL)) u_q (.clk(clk), .rst_in(rst_in),
                .i_v(xq_v[k]), .i_x(xq_x[512 * k + 32 * QL * j +: 32 * QL]), .i_c(xq_c[256 * k + 16 * QL * j +: 16 * QL]),
                .i_s(xq_s[256 * k + 16 * QL * j +: 16 * QL]), .o_v(q_vo[j]), .o_y(xq_y[512 * k + 32 * QL * j +: 32 * QL]),
                .o_f(q_f[j]));
        end
        assign xq_vi[k] = q_vo[0];
        assign xq_f[NQ * k +: NQ] = q_f;               // registered at the control's pins, ORed there
    end endgenerate
endmodule

// hardened leaf / cluster tops at the production parameters
module dsfd_su_t_rxc (
    input  wire          ck, rst,
    input  wire          dn_st, input wire [3:0] dn_kind, input wire [7:0] dn_jid, input wire [4:0] dn_v,
    input  wire [2559:0] dn_d,
    output wire          o_v, output wire [13:0] o_a, output wire [15:0] o_m, output wire [511:0] o_d,
    output wire          o_v2, output wire [13:0] o_a2, output wire [511:0] o_d2,
    output wire          o_fu, o_fo, o_alive, o_den, o_rdy, output wire [7:0] o_rjid,
    output wire          xa_v, output wire [511:0] xa_x, input wire xa_vi, input wire [511:0] xa_r, input wire [15:0] xa_f,
    output wire [1:0]    xq_v, output wire [1023:0] xq_x, output wire [511:0] xq_c, xq_s,
    input  wire [1:0]    xq_vi, input wire [1023:0] xq_y, input wire [3:0] xq_f,
    output wire          xb_v, xw_st, xw_v, xw_last, output wire [39:0] xw_cfg,
    input  wire          xb_vi, xb_wi, input wire [511:0] xb_y, input wire [15:0] xb_m, input wire xb_f
);
    ot_s81_su_rxc #(.S_RD(5), .LM(5), .LA(4), .QW(2)) u_c (
        .clk(ck), .rst_in(rst), .dn_st_i(dn_st), .dn_kind_i(dn_kind), .dn_jid_i(dn_jid), .dn_v_i(dn_v), .dn_d_i(dn_d),
        .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_v2(o_v2), .o_a2(o_a2), .o_d2(o_d2),
        .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den), .o_rdy(o_rdy), .o_rjid(o_rjid),
        .xa_v(xa_v), .xa_x(xa_x), .xa_vi(xa_vi), .xa_r(xa_r), .xa_f(xa_f),
        .xq_v(xq_v), .xq_x(xq_x), .xq_c(xq_c), .xq_s(xq_s), .xq_vi(xq_vi), .xq_y(xq_y), .xq_f(xq_f),
        .xb_v(xb_v), .xw_st(xw_st), .xw_v(xw_v), .xw_last(xw_last), .xw_cfg(xw_cfg),
        .xb_vi(xb_vi), .xb_wi(xb_wi), .xb_y(xb_y), .xb_m(xb_m), .xb_f(xb_f));
endmodule
// RXC split leaves at the production parameters (hardened once each; the slice is replicated x4)
module dsfd_su_t_rxcc (
    input  wire          ck, rst,
    input  wire          dn_st, input wire [3:0] dn_kind, input wire [7:0] dn_jid, input wire [4:0] dn_v,
    input  wire [349:0]  dn_f,
    output wire          o_v, output wire [13:0] o_a, output wire [15:0] o_m, output wire o_v2, output wire [13:0] o_a2,
    output wire          o_fu, o_fo, o_alive, o_den, o_rdy, output wire [7:0] o_rjid,
    output wire          xa_v, input wire xa_vi, input wire [15:0] xa_f,
    output wire [1:0]    xq_v, input wire [1:0] xq_vi, input wire [3:0] xq_f,
    output wire          xb_v, xw_st, xw_v, xw_last, output wire [39:0] xw_cfg,
    input  wire          xb_vi, xb_wi, input wire [15:0] xb_m, input wire xb_f
);
    ot_s81_su_rxc_ctl #(.S_RD(5), .QW(2)) u_c (.clk(ck), .rst_in(rst), .dn_st_i(dn_st), .dn_kind_i(dn_kind), .dn_jid_i(dn_jid),
        .dn_v_i(dn_v), .dn_f_i(dn_f), .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_v2(o_v2), .o_a2(o_a2),
        .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den), .o_rdy(o_rdy), .o_rjid(o_rjid),
        .xa_v(xa_v), .xa_vi(xa_vi), .xa_f(xa_f), .xq_v(xq_v), .xq_vi(xq_vi), .xq_f(xq_f),
        .xb_v(xb_v), .xw_st(xw_st), .xw_v(xw_v), .xw_last(xw_last), .xw_cfg(xw_cfg),
        .xb_vi(xb_vi), .xb_wi(xb_wi), .xb_m(xb_m), .xb_f(xb_f));
endmodule
module dsfd_su_t_rxcs (
    input  wire          ck, rst,
    input  wire          dn_st, input wire [3:0] dn_kind, input wire [4:0] dn_v, input wire [639:0] dn_d,
    output wire [127:0]  xa_x, input wire xa_vi, input wire [127:0] xa_r,
    output wire [255:0]  xq_x, output wire [127:0] xq_c, xq_s, input wire [1:0] xq_vi, input wire [255:0] xq_y,
    input  wire          xb_vi, xb_wi, input wire [127:0] xb_y,
    output wire [127:0]  o_d, o_d2
);
    ot_s81_su_rxc_sl #(.S_RD(5), .QW(2)) u_s (.clk(ck), .rst_in(rst), .dn_st_i(dn_st), .dn_kind_i(dn_kind), .dn_v_i(dn_v),
        .dn_d_i(dn_d), .xa_x(xa_x), .xa_vi(xa_vi), .xa_r(xa_r), .xq_x(xq_x), .xq_c(xq_c), .xq_s(xq_s), .xq_vi(xq_vi),
        .xq_y(xq_y), .xb_vi(xb_vi), .xb_wi(xb_wi), .xb_y(xb_y), .o_d(o_d), .o_d2(o_d2));
endmodule
module dsfd_su_t_rxrb (
    input wire ck, rst, i_v, input wire [1023:0] i_x, input wire w_st, w_v, w_last, input wire [39:0] w_cfg,
    output wire o_v, o_w, output wire [511:0] o_y, output wire [15:0] o_m, output wire o_f
);
    ot_s81_su_rxrb #(.LM(5), .LA(4)) u_b (.clk(ck), .rst_in(rst), .i_v(i_v), .i_x(i_x), .w_st(w_st), .w_v(w_v),
        .w_last(w_last), .w_cfg(w_cfg), .o_v(o_v), .o_w(o_w), .o_y(o_y), .o_m(o_m), .o_f(o_f));
endmodule
module dsfd_su_t_rxsf (
    input wire ck, rst, i_v, input wire [31:0] i_x,
    output wire o_v, output wire [31:0] o_u, o_u2, o_mx, output wire o_f
);
    ot_s81_su_rxsf #(.PCUT(1)) u_f (.clk(ck), .rst_in(rst), .i_v(i_v), .i_x(i_x), .o_v(o_v), .o_u(o_u), .o_u2(o_u2),
        .o_mx(o_mx), .o_f(o_f));
endmodule
module dsfd_su_t_rxsb (
    input wire ck, rst, i_v, input wire [31:0] i_u, i_u2, i_mx, input wire i_f,
    output wire o_v, output wire [31:0] o_r, output wire o_f
);
    ot_s81_su_rxsb #(.PCUT(1)) u_b (.clk(ck), .rst_in(rst), .i_v(i_v), .i_u(i_u), .i_u2(i_u2), .i_mx(i_mx), .i_f(i_f),
        .o_v(o_v), .o_r(o_r), .o_f(o_f));
endmodule
module dsfd_su_t_rxqr (
    input wire ck, rst, i_v, input wire [255:0] i_x, input wire [127:0] i_c, i_s,
    output wire o_v, output wire [255:0] o_y, output wire o_f
);
    ot_s81_su_rxqr #(.LM(5), .LA(4), .QL(8)) u_q (.clk(ck), .rst_in(rst), .i_v(i_v), .i_x(i_x), .i_c(i_c), .i_s(i_s),
        .o_v(o_v), .o_y(o_y), .o_f(o_f));
endmodule
