`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// qwen-coll-io r2 2026-10-14: ot_coll_tp8_die WT 3 = the WT 2 registered-return column datapath with a PIN-REGISTERED
// data leaf and the controller-facing metadata column flat beside the controller.
//
// Why (native audit of the closed WT 2 leaf ot_coll_tp8_col_tile_r, results/rtl/qwen_coll_io_1014/native_audit/):
// at TT, phi - R (R 312.2): c_pop / c_takel / c_sel / c_push capture 385-459 ps, hv launch 346 ps, s_lo / s_hi launch
// 418 ps (combinational head muxes), 1,038 pins over the 220 / 190 budget.  The parent controller reads hv from the
// meta leaf and returns c_pop in the SAME edge (346 + controller + 458 > 833 ps before any wire), so no cluster of
// WT 2 leaves can close: the queue handshake crossed a hardened-leaf boundary twice per edge.
//
// WT 3 structure:
//   * ot_coll_tp8_col_core: the WT 2 leaf body, parameterised (W, per-queue widths, MEM 1 = 32x128 macros, MEM 2 =
//     flop storage with a registered read = the macro's exact read timing, so hv / head timing is identical).
//   * metadata column (column 4: tag / mode / last, LQ {mode, rank, err, last}, TQ / RQ {err, last}) = the SAME core
//     with MEM 2 and per-queue widths, synthesised FLAT in the cluster glue next to the controller: hv and every head
//     the controller reads are local logic, no hardened boundary inside the handshake loop.
//   * data leaves ot_coll_tp8_col_tile_r3 (x4, 128-bit data columns): one pin flop on EVERY input (control and data)
//     ahead of the unchanged core, one pin flop on s_lo / s_hi.  A leaf is therefore an exact replica of the WT 2
//     column delayed by one edge (s_lo / s_hi by two); the parent pairs each leaf output with its own valid / meta
//     delayed by the same edges (ot_coll_tp8_die WT 3).  No leaf output is consumed by the controller.
// Negative controls: OT_TP8_MUT_OWNER / OT_TP8_MUT_GATHER / OT_TP8R_MUT_SEAM as WT 2 (inside the core), and
// OT_TP8R3_MUT_SKEW (bench only): the leaf s_lo / s_hi output flop is bypassed, the fold slices see words one edge
// early against their delayed red_in -> the exact bench must fail.
// ---------------------------------------------------------------------------

// First-word-fall-through queue, D / 32 banks behind a 2-entry output buffer (one pop per edge sustained).
// MEM 1: ot_sram_1r1w_32x128_m1 macros (registered read).  MEM 2: flop storage read through a register at the same
// edge as the macro's read (identical hv / hd timing to MEM 1; used for the narrow metadata column).
module ot_coll_tp8_cq #(parameter integer W = 128, parameter integer D = 32, parameter integer MEM = 1) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         push,
    input  wire [W-1:0] wd,
    input  wire         pop,
    output wire         hv,
    output wire [W-1:0] hd,
    output reg          ovf
);
    localparam integer AB = $clog2(D);
    localparam integer K = D / 32;
    initial if (D % 32 != 0 || W > 128 || (K & (K - 1)) != 0 || (MEM != 1 && MEM != 2))
        $error("ot_coll_tp8_cq: D = 32 * 2^k, W <= 128, MEM 1 or 2");
    wire qr;
    (* keep_hierarchy *) ot_coll_rst_leaf u_qr (.clk(clk), .arst_n(rst_n), .q(qr));
    reg [AB-1:0] wp, rp;
    reg [AB:0] mcnt;
    reg rf;
    reg [1:0] obn;
    reg [W-1:0] ob0, ob1;
    reg [(K > 1 ? $clog2(K) : 1)-1:0] rsel;
    wire popv = pop && (obn != 0);
    wire [2:0] after = {1'b0, obn} + {2'b0, rf} - {2'b0, popv};
    wire rd = (mcnt != 0) && (after <= 3'd1);
    wire [W-1:0] rdat;
    generate if (MEM == 1) begin : g_mac
        wire [127:0] rdo [0:K-1];
        genvar gk;
        for (gk = 0; gk < K; gk = gk + 1) begin : g_k
            wire sel_r = (K == 1) ? 1'b1 : (rp >> 5) == gk;
            wire sel_w = (K == 1) ? 1'b1 : (wp >> 5) == gk;
            ot_sram_1r1w_32x128_m1 u_m (.clk(clk), .r_ce_in(rd && sel_r), .r_addr_in(rp[4:0]), .rd_out(rdo[gk]),
                .w_ce_in(push && sel_w), .w_addr_in(wp[4:0]), .wd_in({{(128-W){1'b0}}, wd}), .w_mask_in({128{1'b1}}));
        end
        assign rdat = rdo[rsel][W-1:0];
    end else begin : g_flop
        reg [W-1:0] m [0:D-1];
        reg [W-1:0] rq;
        always @(posedge clk) begin
            if (push) m[wp] <= wd;
            if (rd) rq <= m[rp];
        end
        assign rdat = rq;
    end endgenerate
    wire [1:0] n0 = obn - (popv ? 2'd1 : 2'd0);
    always @(posedge clk) begin
        if (popv) ob0 <= ob1;
        if (rf) begin if (n0 == 0) ob0 <= rdat; else ob1 <= rdat; end
        if (rd) rsel <= (K == 1) ? 0 : (rp >> 5);
    end
    always @(posedge clk or negedge qr)
        if (!qr) begin wp <= 0; rp <= 0; mcnt <= 0; rf <= 1'b0; obn <= 0; ovf <= 1'b0; end
        else begin
            if (push) wp <= wp + 1'b1;
            if (rd) rp <= rp + 1'b1;
            mcnt <= mcnt + (push ? 1'b1 : 1'b0) - (rd ? 1'b1 : 1'b0);
            rf <= rd;
            obn <= n0 + (rf ? 2'd1 : 2'd0);
            if ((push && mcnt == D && !rd) || (pop && obn == 0)) ovf <= 1'b1;
        end
    assign hv = (obn != 0);
    assign hd = ob0;
endmodule

// The WT 2 column body (rtl/rom/ot_coll_tp8_col_tile_r.sv, same edges), parameterised.  WLB applies to LB / PQ / EQ
// and the pairing registers; WLQ / WTQ / WRQ to the result queues (the metadata column keeps only the bits it owns).
module ot_coll_tp8_col_core #(
    parameter integer W   = 128,
    parameter integer WLQ = 128,
    parameter integer WTQ = 128,
    parameter integer WRQ = 128,
    parameter integer MEM = 1
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         die_s,
    input  wire         meta_s,
    input  wire [W-1:0] in_d, dp_d, dr_d,
    input  wire [3*W-1:0] sr_d,
    input  wire [W-1:0] sum_d,
    input  wire [W-1:0] lq_wd, tq_wd,
    input  wire [W-1:0] e_tx,
    input  wire [5:0]   c_push, c_pop,
    input  wire         c_hold,
    input  wire [1:0]   c_sel,
    input  wire         c_takel,
    output reg  [W-1:0] up, ur, od,
    output reg  [3*W-1:0] sr, sx,
    output wire [W-1:0] s_lo, s_hi,
    output wire [W-1:0] lb_hd, pq_hd, eq_hd, lq_hd, tq_hd, rq_hd,
    output wire [5:0]   hv, ovf
);
    reg [W-1:0] ir, rl, dp, dr, gh, hl, hh, hl_p, hh_p;
    reg [W-1:0] sum_q, loc_q, lqw_q, tqw_q;
    reg         sel_q, hold_q;
    reg [2:0]   push_q;
    wire        qr;
    (* keep_hierarchy *) ot_coll_rst_leaf u_cr (.clk(clk), .arst_n(rst_n), .q(qr));
    (* keep *) reg [7:0] die_q, meta_q;
    always @(posedge clk) begin die_q <= {8{die_s}}; meta_q <= {8{meta_s}}; end
    wire [W-1:0] die_v, meta_v;
    genvar gs;
    generate for (gs = 0; gs < W; gs = gs + 1) begin : g_strap
        assign die_v[gs] = die_q[(gs * 8) / W];
        assign meta_v[gs] = meta_q[(gs * 8) / W];
    end endgenerate
    wire [W-1:0] lo_i = (die_v & pq_hd) | (~die_v & lb_hd);
    wire [W-1:0] hi_i = (die_v & lb_hd) | (~die_v & pq_hd);
`ifdef OT_TP8_MUT_OWNER
    wire [W-1:0] held = die_v;
`else
    wire [W-1:0] held = ~die_v;
`endif
`ifdef OT_TP8_MUT_GATHER
    wire [W-1:0] gd_w = lo_i, gf_w = hi_i;
`else
    wire [W-1:0] gd_w = hi_i, gf_w = lo_i;
`endif
    // metadata column: {tag of lo, mode 1, last} (the tag occupies bits 33:2 of the 128-bit record slice)
    wire [W-1:0] gh_m = {{(W-34){1'b0}}, lo_i[33:2], 1'b1, lb_hd[0]};
    wire [W-1:0] gf_m = {{(W-34){1'b0}}, lo_i[33:2], 1'b1, 1'b0};
    wire [W-1:0] gh_n = (meta_v & gh_m) | (~meta_v & gd_w);
    wire [W-1:0] gf_n = (meta_v & gf_m) | (~meta_v & gf_w);
    wire [W-1:0] hl_e = hold_q ? hl_p : hl;
    wire [W-1:0] hh_e = hold_q ? hh_p : hh;
    assign s_lo = (held & hl_e) | (~held & lo_i);
    assign s_hi = (held & hh_e) | (~held & hi_i);
    always @(posedge clk) begin
        ir <= in_d; rl <= ir; up <= rl; dp <= dp_d; dr <= dr_d;
        sr <= sr_d; sx <= {3{e_tx}}; ur <= tq_hd;
        od <= c_takel ? lq_hd : rq_hd;
        hl_p <= lo_i; hh_p <= hi_i;
        if (hold_q) begin hl <= hl_p; hh <= hh_p; end
        gh <= gh_n;
        sum_q <= sum_d;
        loc_q <= c_sel[0] ? gf_n : gh;
        sel_q <= c_sel[1];
        lqw_q <= lq_wd; tqw_q <= tq_wd;
    end
    always @(posedge clk or negedge qr)
        if (!qr) begin hold_q <= 1'b0; push_q <= 3'd0; end
        else begin hold_q <= c_hold; push_q <= c_push[4:2]; end
`ifdef OT_TP8R_MUT_SEAM
    wire [W-1:0] eq_w = c_sel[1] ? sum_d : (c_sel[0] ? gf_n : gh);
`else
    wire [W-1:0] eq_w = sel_q ? sum_q : loc_q;
`endif
    wire [WLQ-1:0] lq_h; wire [WTQ-1:0] tq_h; wire [WRQ-1:0] rq_h;
    ot_coll_tp8_cq #(.W(W),   .D(64),  .MEM(MEM)) u_lb(.clk(clk),.rst_n(rst_n),.push(c_push[0]),.pop(c_pop[0]),.wd(rl),.hd(lb_hd),.hv(hv[0]),.ovf(ovf[0]));
    ot_coll_tp8_cq #(.W(W),   .D(64),  .MEM(MEM)) u_pq(.clk(clk),.rst_n(rst_n),.push(c_push[1]),.pop(c_pop[1]),.wd(dp),.hd(pq_hd),.hv(hv[1]),.ovf(ovf[1]));
    ot_coll_tp8_cq #(.W(W),   .D(32),  .MEM(MEM)) u_eq(.clk(clk),.rst_n(rst_n),.push(push_q[0]),.pop(c_pop[2]),.wd(eq_w),.hd(eq_hd),.hv(hv[2]),.ovf(ovf[2]));
    ot_coll_tp8_cq #(.W(WLQ), .D(128), .MEM(MEM)) u_lq(.clk(clk),.rst_n(rst_n),.push(push_q[1]),.pop(c_pop[3]),.wd(lqw_q[WLQ-1:0]),.hd(lq_h),.hv(hv[3]),.ovf(ovf[3]));
    ot_coll_tp8_cq #(.W(WTQ), .D(128), .MEM(MEM)) u_tq(.clk(clk),.rst_n(rst_n),.push(push_q[2]),.pop(c_pop[4]),.wd(tqw_q[WTQ-1:0]),.hd(tq_h),.hv(hv[4]),.ovf(ovf[4]));
    ot_coll_tp8_cq #(.W(WRQ), .D(32),  .MEM(MEM)) u_rq(.clk(clk),.rst_n(rst_n),.push(c_push[5]),.pop(c_pop[5]),.wd(dr[WRQ-1:0]),.hd(rq_h),.hv(hv[5]),.ovf(ovf[5]));
    assign lq_hd = {{(W-WLQ){1'b0}}, lq_h};
    assign tq_hd = {{(W-WTQ){1'b0}}, tq_h};
    assign rq_hd = {{(W-WRQ){1'b0}}, rq_h};
endmodule

// The hardened WT 3 data leaf (x4 per die, one 128-bit data column each).  Every input lands in a pin flop; the core
// then runs the WT 2 column one edge late; s_lo / s_hi leave through pin flops (two edges late).  Pins: as
// ot_coll_tp8_col_tile_r minus the controller-facing heads / hv / meta strap (the controller reads the flat metadata
// column instead).
module ot_coll_tp8_col_tile_r3 (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         die_s,
    input  wire [127:0] in_d, dp_d, dr_d,
    input  wire [383:0] sr_d,
    input  wire [127:0] sum_d,
    input  wire [127:0] lq_wd, tq_wd,
    input  wire [127:0] e_tx,
    input  wire [5:0]   c_push, c_pop,
    input  wire         c_hold,
    input  wire [1:0]   c_sel,
    input  wire         c_takel,
    output wire [127:0] up, ur, od,
    output wire [383:0] sr, sx,
    output reg  [127:0] s_lo, s_hi,
    output wire [127:0] eq_hd,
    output wire [5:0]   ovf
);
    wire pr;
    (* keep_hierarchy *) ot_coll_rst_leaf u_pr (.clk(clk), .arst_n(rst_n), .q(pr));
    // pin stage: data (no reset) and control (reset: no phantom push / pop while the queues release)
    reg [127:0] in_q, dp_q, dr_q, sum_q, lq_q, tq_q, tx_q;
    reg [383:0] sr_q;
    reg [5:0]   push_p, pop_p;
    reg         hold_p, takel_p;
    reg [1:0]   sel_p;
    always @(posedge clk) begin
        in_q <= in_d; dp_q <= dp_d; dr_q <= dr_d; sr_q <= sr_d; sum_q <= sum_d;
        lq_q <= lq_wd; tq_q <= tq_wd; tx_q <= e_tx;
        sel_p <= c_sel; takel_p <= c_takel;
    end
    always @(posedge clk or negedge pr)
        if (!pr) begin push_p <= 6'd0; pop_p <= 6'd0; hold_p <= 1'b0; end
        else begin push_p <= c_push; pop_p <= c_pop; hold_p <= c_hold; end
    wire [127:0] lo_c, hi_c;
    wire [127:0] lb_h, pq_h, lq_h, tq_h, rq_h;
    wire [5:0]   hv_c;
    ot_coll_tp8_col_core #(.W(128), .MEM(1)) u_c (.clk(clk), .rst_n(rst_n), .die_s(die_s), .meta_s(1'b0),
        .in_d(in_q), .dp_d(dp_q), .dr_d(dr_q), .sr_d(sr_q), .sum_d(sum_q), .lq_wd(lq_q), .tq_wd(tq_q), .e_tx(tx_q),
        .c_push(push_p), .c_pop(pop_p), .c_hold(hold_p), .c_sel(sel_p), .c_takel(takel_p),
        .up(up), .ur(ur), .od(od), .sr(sr), .sx(sx), .s_lo(lo_c), .s_hi(hi_c),
        .lb_hd(lb_h), .pq_hd(pq_h), .eq_hd(eq_hd), .lq_hd(lq_h), .tq_hd(tq_h), .rq_hd(rq_h), .hv(hv_c), .ovf(ovf));
`ifdef OT_TP8R3_MUT_SKEW
    always @(*) begin s_lo = lo_c; s_hi = hi_c; end
`else
    always @(posedge clk) begin s_lo <= lo_c; s_hi <= hi_c; end
`endif
endmodule
