`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// qwen-coll-io 2026-10-14: ot_coll_tp8_col_tile_r -- the TP8 wrapper column leaf with REGISTERED RETURNS
// (ot_coll_tp8_die WT 2; WT 1 keeps the closed ot_coll_tp8_col_tile).  Hardened once, replicated x5 (four 128-bit data
// columns + the meta column {tag, mode, last} of the 546-bit record).
//
// Why (qfd_io_collective, 29 failed routes): the WT 1 leaf takes every word in on W and gives it out on E, and the
// cluster's pairing / pre-fold / engine glue sat between, so three loops left the leaf on E and came back on W into
// UN-registered SRAM write pins across 500-900 um:
//   (a) LB/PQ heads -> parent pairing mux (lo/hi) -> leaf hl/hh/gh capture       (pure wire loop, ~600 um)
//   (b) heads / gh -> parent eq mux -> eq_wd -> EQ macro write pins               (wire loop, unregistered write)
//   (c) fold-slice sum (clk->out <= 536 ps) -> parent mux -> eq_wd -> EQ write     (cross-cluster, unregistered write)
//   (d) engine result e_od -> lq_wd / tq_wd -> LQ / TQ macro write pins            (cross-cluster, unregistered write)
//   (e) LQ/RQ heads -> parent merger mux m_d -> leaf od                             (wire loop)
// This leaf closes every one of them:
//   (a)(e) the static die-strap muxes (lo/hi, the gather word, the merger select) move INSIDE the leaf: no data word
//          leaves the leaf to come back; the parent sends only 1-bit decisions (c_hold, c_sel, c_takel).
//   (b)(c)(d) every write port fed from outside the leaf is captured at the leaf pin (pin flop on data AND push) and
//          written one edge later: EQ gets the fold-slice sum (data columns) or the meta {ml_tag, 0, ml_last} (meta
//          column) on sum_d, LQ / TQ get the engine result.  The local alternatives of the EQ write (gather first
//          word / held gather word) are selected at edge t into a local register, so the late write uses the words
//          of edge t exactly.  Cost: EQ, LQ and TQ heads become visible one edge later (+1 on the reduce path, +1 on
//          the result path); every queue is reservation-managed by the parent, so no credit changes.
//   c_hold (was 512 loads straight from the port) lands in one pin flop: the leaf copies lo/hi into a free-running
//   pre-hold register every edge and commits it one edge later, with a bypass for the issue that follows at once.
// Result reservations sized to the board crossing (qwen-coll-io 10-14 sweep): LQ 128 and TQ 128 words (4 macros
// each; the WT 1 leaf had 64 / 32): the engine reserves one LQ/TQ word per reduce word at intake, so these depths bound
// the words in flight across the board.  With the DEPTH 64 engine (ot_coll_col_tile_d64): AR256 953 at LAT 339.
// Pins (kit): face P (to the pre-fold slices) s_lo, s_hi out / sum_d in; face E (to the engine) eq_hd out,
// lq_wd / tq_wd in; the link / local words on the remaining faces, as the cluster floorplan assigns.
// Straps (static, tied by the parent): die_s = DIE, meta_s = 1 on the meta column.
// Negative controls (bench only): OT_TP8_MUT_OWNER, OT_TP8_MUT_GATHER (as ot_coll_tp8_die) and OT_TP8R_MUT_SEAM (the
// EQ write uses the un-aligned live word, not the registered one) must fail the exact bench.
// ---------------------------------------------------------------------------
module ot_coll_tp8_col_tile_r (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         die_s,
    input  wire         meta_s,
    input  wire [127:0] in_d, dp_d, dr_d,
    input  wire [383:0] sr_d,
    input  wire [127:0] sum_d,        // EQ reduce word (fold-slice sum / meta) -- registered at the pin
    input  wire [127:0] lq_wd, tq_wd, // engine result words -- registered at the pin
    input  wire [127:0] e_tx,
    input  wire [5:0]   c_push, c_pop,
    input  wire         c_hold,       // pr_red && !wpar: the first pair of an owned couple is held
    input  wire [1:0]   c_sel,        // {sl_tail, pr_gat} of the EQ write at this edge
    input  wire         c_takel,      // merger takes the local result (LQ) this edge
    output reg  [127:0] up, ur, od,
    output reg  [383:0] sr, sx,
    output wire [127:0] s_lo, s_hi,   // pre-fold operands (held / current pair)
    output wire [127:0] lb_hd, pq_hd, eq_hd, lq_hd, tq_hd, rq_hd,
    output wire [5:0]   hv, ovf
);
    // ---------------- registered seams ----------------
    reg [127:0] ir, rl, dp, dr, gh, hl, hh, hl_p, hh_p;
    reg [127:0] sum_q, loc_q, lqw_q, tqw_q;
    reg         sel_q, hold_q;
    reg [2:0]   push_q;               // EQ, LQ, TQ pushes, one edge late with their words
    wire        qr;
    (* keep_hierarchy *) ot_coll_rst_leaf u_cr (.clk(clk), .arst_n(rst_n), .q(qr));
    // static die-strap selects
    wire [127:0] lo_i = die_s ? pq_hd : lb_hd;
    wire [127:0] hi_i = die_s ? lb_hd : pq_hd;
`ifdef OT_TP8_MUT_OWNER
    wire held = die_s;
`else
    wire held = !die_s;               // die 0 owns the even word (held), die 1 the odd word (current)
`endif
    // gather words: data columns hi (held word) / lo (first word); meta column {tag of lo, mode 1, last}
`ifdef OT_TP8_MUT_GATHER
    wire [127:0] gd_w = lo_i, gf_w = hi_i;
`else
    wire [127:0] gd_w = hi_i, gf_w = lo_i;
`endif
    wire [127:0] gh_n = meta_s ? {94'd0, lo_i[33:2], 1'b1, lb_hd[0]} : gd_w;
    wire [127:0] gf_n = meta_s ? {94'd0, lo_i[33:2], 1'b1, 1'b0}    : gf_w;
    // held operands: hl/hh commit one edge after c_hold; the issue right after the hold reads the pre-hold copy
    wire [127:0] hl_e = hold_q ? hl_p : hl;
    wire [127:0] hh_e = hold_q ? hh_p : hh;
    assign s_lo = held ? hl_e : lo_i;
    assign s_hi = held ? hh_e : hi_i;
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
    wire [127:0] eq_w = c_sel[1] ? sum_d : (c_sel[0] ? gf_n : gh);   // live word, written one edge late
`else
    wire [127:0] eq_w = sel_q ? sum_q : loc_q;
`endif
    ot_coll_tp8_col_q #(.W(128),.D(64),.MEM(1)) u_lb(.clk(clk),.rst_n(rst_n),.push(c_push[0]),.pop(c_pop[0]),.wd(rl),.hd(lb_hd),.hv(hv[0]),.ovf(ovf[0]));
    ot_coll_tp8_col_q #(.W(128),.D(64),.MEM(1)) u_pq(.clk(clk),.rst_n(rst_n),.push(c_push[1]),.pop(c_pop[1]),.wd(dp),.hd(pq_hd),.hv(hv[1]),.ovf(ovf[1]));
    ot_coll_tp8_col_q #(.W(128),.D(32),.MEM(1)) u_eq(.clk(clk),.rst_n(rst_n),.push(push_q[0]),.pop(c_pop[2]),.wd(eq_w),.hd(eq_hd),.hv(hv[2]),.ovf(ovf[2]));
    ot_coll_tp8_col_q #(.W(128),.D(128),.MEM(1)) u_lq(.clk(clk),.rst_n(rst_n),.push(push_q[1]),.pop(c_pop[3]),.wd(lqw_q),.hd(lq_hd),.hv(hv[3]),.ovf(ovf[3]));
    ot_coll_tp8_col_q #(.W(128),.D(128),.MEM(1)) u_tq(.clk(clk),.rst_n(rst_n),.push(push_q[2]),.pop(c_pop[4]),.wd(tqw_q),.hd(tq_hd),.hv(hv[4]),.ovf(ovf[4]));
    ot_coll_tp8_col_q #(.W(128),.D(32),.MEM(1)) u_rq(.clk(clk),.rst_n(rst_n),.push(c_push[5]),.pop(c_pop[5]),.wd(dr),.hd(rq_hd),.hv(hv[5]),.ovf(ovf[5]));
endmodule
