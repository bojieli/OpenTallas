`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_segtree3: ot_v41_segtree2 with LOCAL decision logic (QPIPE, DS-V4.1 ROM q-pair, 2026-10-03; zero cycles,
// same events, same adds, same order).  segtree2 forms pair / hold from x_have = |(have & x_oh) over all NT*LV
// held slots and drives every slot's write enable from that global decision.  Because x_oh is one-hot (or zero at
// the top level, where neither pair nor hold can occur), the selected slot's own bit IS x_have, and
//   pair  on slot h  <=>  x_v && x_oh[h] &&  have[h]                 (a held slot is never the early-exit case)
//   hold  on slot h  <=>  x_v && x_oh[h] && !have[h] && !x_f
// so each slot's have / herr / held update is a function of that slot's own bits.  The in-flight counters
// likewise need only their own tree's LV slots (x_toh: the event's tree, one-hot, registered with x_oh).
// ot_v41_segtree2: ot_v41_segtree on the LAT-stage ot_v41_fadd with the adder result registered before it is
// an event and a 2-stage event pipeline (select + one-hot decode | decide) (W10, 1.2 GHz at SS): LAT + 3
// cycles per level (was 6).  Same order and results.
// ot_v41_segtree: the golden csum padded pairwise tree over one segment's chunk sums, for up to NT
// segments (trees) in flight, on ONE pipelined binary32 adder (ot_fp32_add_rne_pipe, 5 cycles).
//
// Base nodes of a tree arrive IN ORDER (FP8 chunk sums, FP4 chunk-pair sums); `final` marks the tree's last.
// An event {tree, level, value, final} at level l either pairs with the tree's held left operand of level l
// (held + value, left first) or, if none is held, is held -- unless it is final, when it is promoted to
// level l+1 by adding +0 (the golden's padding; x + 0 = x here, since no zero is -0).  Both go through the
// adder (operands registered first: 6 cycles per level), so every event at level l+1 leaves the adder in the
// order its level-l inputs entered it, and a
// promoted final can never overtake an in-flight sum of its own tree.  A final event at level LV leaves as
// the segment's partial.  Base nodes queue in a QD-entry FIFO while the adder serves its own results first.
// Adds per tree: (base nodes - 1) + at most LV promotions -- under one per cycle for any base-node rate the
// element can produce, so one adder replaces LV.
// ---------------------------------------------------------------------------
module ot_v41_segtree3 #(
    parameter integer NT = 4,
    parameter integer LV = 5,
    parameter integer QD = 8,
    parameter [8:0] CUT = 9'b1_0111_1011,
    parameter integer LAT = 1 + CUT[0] + CUT[1] + CUT[2] + CUT[3] + CUT[4] + CUT[5] + CUT[6] + CUT[7] + CUT[8],
    parameter integer EARLY = 0      // 1: a final node with nothing held above it and nothing of its tree in the
                                     //    adder leaves at once instead of being promoted (+0) level by level
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire                     in_v,
    input  wire [$clog2(NT)-1:0]    in_tree,
    input  wire [2:0]               in_pos,     // position (MTP) of the tree's nodes; leaves with its value
    input  wire [31:0]              in_val,
    input  wire                     in_final,
    input  wire                     in_err,
    output reg                      ov,
    output reg  [$clog2(NT)-1:0]    otree,
    output reg  [2:0]               opos,
    output reg  [31:0]              oval,
    output reg                      oerr,
    output reg                      fault
);
    localparam integer PW = $clog2(NT);
    localparam integer LW = $clog2(LV + 1);
    localparam integer QW = $clog2(QD);
    // base-node queue
    reg [31:0] qv [0:QD-1];
    reg [PW-1:0] qt [0:QD-1];
    reg qf [0:QD-1], qe [0:QD-1];
    reg [2:0] qp [0:QD-1];
    reg [2:0] tpos [0:NT-1];
    reg [QW-1:0] qr, qw;
    reg [QW:0] qc;
    // held left operands
    reg [31:0] held [0:NT*LV-1];
    reg [NT*LV-1:0] have, herr;
    // adder result (event at level + 1), registered once before it is an event (1.2 GHz: the event decision and
    // the held-operand write no longer follow the adder's output stage in the same cycle)
    wire [31:0] sum_a;
    wire [1:0] err_a;
    wire sv_a;
    wire [PW+LW+1:0] st_a;
    reg  [31:0] sum;
    reg  [1:0] err;
    reg  sv;
    reg  [PW+LW+1:0] st;     // {tree, level, final, err}
    always @(posedge clk or negedge rst_n) if (!rst_n) sv <= 1'b0; else sv <= sv_a;
    always @(posedge clk) begin sum <= sum_a; err <= err_a; st <= st_a; end
    // STAGE 1 -- the event considered this cycle: adder result first, else the queue head.  It is registered
    // (x_*) with its held-operand index decoded one-hot and the mask of its tree's levels above it, so the
    // decision stage below is a few AND-OR levels over registers (1.2 GHz at SS).  An event spends one cycle in
    // each stage; the decision stage reads and writes the held operands in the same cycle, so consecutive
    // events of one tree see each other's updates.
    wire use_q = !sv && qc != 0;
    reg [31:0] h_v;
    reg [PW-1:0] h_t;
    reg h_f, h_e;
    reg [2:0] h_p;
    wire        e_v = sv || qc != 0;
    wire [PW-1:0] e_t = sv ? st[PW+LW+1 -: PW] : h_t;
    wire [LW-1:0] e_l = sv ? st[LW+1 -: LW] : {LW{1'b0}};
    wire        e_f = sv ? st[1] : h_f;
    wire        e_e = sv ? (st[0] | err != 2'd0) : h_e;
    wire [31:0] e_d = sv ? sum : h_v;
    localparam integer NH = NT * LV;
    reg [NH-1:0] e_oh, e_above;
    integer li, ti, hi;
    always @* begin
        e_oh = '0; e_above = '0;
        for (hi = 0; hi < NH; hi = hi + 1) begin
            if (hi / LV == e_t && hi % LV == e_l) e_oh[hi] = 1'b1;
            if (hi / LV == e_t && hi % LV > e_l) e_above[hi] = 1'b1;
        end
    end
    reg          x_v, x_f, x_e, x_add;
    reg [PW-1:0] x_t;
    reg [LW-1:0] x_l;
    reg [31:0]   x_d;
    reg [NH-1:0] x_oh, x_above;
    reg [NT-1:0] x_toh;
    reg [2:0]    x_pos;
    always @(posedge clk or negedge rst_n) if (!rst_n) x_v <= 1'b0; else x_v <= e_v;
    always @(posedge clk) begin
        x_t <= e_t; x_l <= e_l; x_f <= e_f; x_e <= e_e; x_d <= e_d; x_add <= sv;
        x_oh <= e_oh; x_above <= e_above;
        for (ti = 0; ti < NT; ti = ti + 1) x_toh[ti] <= e_t == ti;
        x_pos <= use_q ? h_p : tpos[e_t];
    end
    // STAGE 2 -- decide: pair with the held left operand, promote a final node (+0), hold it, or emit at the top
    localparam integer IW = $clog2(LAT + 4);
    reg [IW-1:0] infl [0:NT-1];
    wire x_have = |(have & x_oh);
    wire above = |(have & x_above);
    wire idle_tree = infl[x_t] == (x_add ? {{(IW-1){1'b0}}, 1'b1} : {IW{1'b0}});
    wire early = (EARLY != 0) && x_v && x_f && !x_have && !above && idle_tree;
    wire top = x_l == LV[LW-1:0] || early;
    wire pair = x_v && !top && x_have;
    wire promote = x_v && !top && !x_have && x_f;
    wire hold = x_v && !top && !x_have && !x_f;
    // local forms (see the header): per tree its own slots, per slot its own bit
    reg [NT-1:0] t_inc, t_dec;
    reg [NH-1:0] s_hold, s_pair;
    integer tj;
    reg hv_t, ab_t, id_t, ea_t, tp_t;
    always @* begin
        for (tj = 0; tj < NT; tj = tj + 1) begin
            hv_t = |(have[tj*LV +: LV] & x_oh[tj*LV +: LV]);
            ab_t = |(have[tj*LV +: LV] & x_above[tj*LV +: LV]);
            id_t = infl[tj] == (x_add ? {{(IW-1){1'b0}}, 1'b1} : {IW{1'b0}});
            ea_t = (EARLY != 0) && x_f && !hv_t && !ab_t && id_t;
            tp_t = x_l == LV[LW-1:0] || ea_t;
            t_inc[tj] = x_v && x_toh[tj] && !tp_t && (hv_t || x_f);
            t_dec[tj] = x_v && x_toh[tj] && x_add;
        end
        for (tj = 0; tj < NH; tj = tj + 1) begin
`ifdef QP_MUTANT_TREE
            s_hold[tj] = x_v && x_oh[tj] && !x_f;                         // negative control: ignores the held bit
`else
            s_hold[tj] = x_v && x_oh[tj] && !have[tj] && !x_f;
`endif
            s_pair[tj] = x_v && x_oh[tj] && have[tj];
        end
    end
    reg [31:0] x_held;
    reg        x_herr;
    always @* begin
        x_held = 32'd0; x_herr = 1'b0;
        for (hi = 0; hi < NH; hi = hi + 1)
            if (x_oh[hi]) begin x_held = x_held | held[hi]; x_herr = x_herr | herr[hi]; end
    end
    wire [PW-1:0] out_t = x_t;
    reg [31:0] add_a, add_b;
    reg        add_v;
    always @(posedge clk) begin
        add_a <= pair ? x_held : x_d;
        add_b <= pair ? x_d : 32'd0;
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) add_v <= 1'b0; else add_v <= pair | promote;
    ot_v41_fadd #(.CUT(CUT)) u_add (.clk(clk), .rst_n(rst_n), .valid_in(add_v), .a(add_a), .b(add_b),
                                     .y(sum_a), .err(err_a), .valid_out(sv_a));
    ot_hdc_delay #(.W(PW + LW + 2), .D(LAT + 1)) u_t (.clk(clk), .rst_n(rst_n),
        .d({x_t, x_l + 1'b1, x_f, x_e | (pair && x_herr)}), .q(st_a));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            qr <= 0; qw <= 0; qc <= 0; have <= '0; herr <= '0; ov <= 1'b0; oerr <= 1'b0; fault <= 1'b0;
            for (ti = 0; ti < NT; ti = ti + 1) infl[ti] <= '0;
        end else begin
            if (in_v) qw <= qw + 1'b1;
            if (use_q) qr <= qr + 1'b1;
            qc <= qc + (in_v ? 1'b1 : 1'b0) - (use_q ? 1'b1 : 1'b0);
            if (in_v && qc == QD && !use_q) fault <= 1'b1;
            if (x_v && x_l == LV[LW-1:0] && !x_f) fault <= 1'b1;    // more base nodes than 2^LV: not the root
            for (ti = 0; ti < NT; ti = ti + 1)
                infl[ti] <= infl[ti] + (t_inc[ti] ? 1'b1 : 1'b0) - (t_dec[ti] ? 1'b1 : 1'b0);
            have <= (have & ~s_pair) | s_hold;
            herr <= (herr & ~s_hold) | (x_e ? s_hold : '0);
            ov <= x_v && top;
            oerr <= x_v && top && x_e;
        end
    end
    always @(posedge clk) begin
        if (in_v) begin qv[qw] <= in_val; qt[qw] <= in_tree; qf[qw] <= in_final; qe[qw] <= in_err; qp[qw] <= in_pos; end
        if (use_q) tpos[h_t] <= h_p;
        opos <= x_pos;
        if (qr + (use_q ? 1'b1 : 1'b0) == qw) begin      // the head-to-be is the node arriving now (if any)
            h_v <= in_val; h_t <= in_tree; h_f <= in_final; h_e <= in_err; h_p <= in_pos;
        end else begin
            h_v <= qv[qr + (use_q ? 1'b1 : 1'b0)]; h_t <= qt[qr + (use_q ? 1'b1 : 1'b0)];
            h_f <= qf[qr + (use_q ? 1'b1 : 1'b0)]; h_e <= qe[qr + (use_q ? 1'b1 : 1'b0)];
            h_p <= qp[qr + (use_q ? 1'b1 : 1'b0)];
        end
        for (hi = 0; hi < NH; hi = hi + 1) if (s_hold[hi]) held[hi] <= x_d;
        oval <= x_d;
        otree <= x_t;
    end
`ifdef QP_CHECK
    // the local forms against the global decision of ot_v41_segtree2, every cycle
    always @(negedge clk) if (rst_n) begin
        if (s_hold !== (hold ? x_oh : {NH{1'b0}})) begin $display("QP_CHECK FAIL segtree hold %m %t", $time); $fatal(1); end
        if (s_pair !== (pair ? x_oh : {NH{1'b0}})) begin $display("QP_CHECK FAIL segtree pair %m %t", $time); $fatal(1); end
        for (int t = 0; t < NT; t++) begin
            if (t_inc[t] !== ((pair | promote) && x_t == t)) begin $display("QP_CHECK FAIL segtree inc %m %t", $time); $fatal(1); end
            if (t_dec[t] !== (x_v && x_add && out_t == t)) begin $display("QP_CHECK FAIL segtree dec %m %t", $time); $fatal(1); end
        end
    end
`endif
endmodule
