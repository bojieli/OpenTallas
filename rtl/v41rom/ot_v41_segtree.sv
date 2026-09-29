`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_segtree: the golden csum padded pairwise tree over one segment's chunk sums, for up to NT
// segments (trees) in flight, on ONE pipelined binary32 adder (ot_fp32_add_rne_pipe, 5 cycles).
//
// Base nodes of a tree arrive IN ORDER (FP8 chunk sums, FP4 chunk-pair sums); `final` marks the tree's last.
// An event {tree, level, value, final} at level l either pairs with the tree's held left operand of level l
// (held + value, left first) or, if none is held, is held -- unless it is final, when it is promoted to
// level l+1 by adding +0 (the golden's padding; x + 0 = x here, since no zero is -0).  Both go through the
// adder, so every event at level l+1 leaves the adder in the order its level-l inputs entered it, and a
// promoted final can never overtake an in-flight sum of its own tree.  A final event at level LV leaves as
// the segment's partial.  Base nodes queue in a QD-entry FIFO while the adder serves its own results first.
// Adds per tree: (base nodes - 1) + at most LV promotions -- under one per cycle for any base-node rate the
// element can produce, so one adder replaces LV.
// ---------------------------------------------------------------------------
module ot_v41_segtree #(
    parameter integer NT = 4,
    parameter integer LV = 5,
    parameter integer QD = 8,
    parameter integer EARLY = 0      // 1: a final node with nothing held above it and nothing of its tree in the
                                     //    adder leaves at once instead of being promoted (+0) level by level
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire                     in_v,
    input  wire [$clog2(NT)-1:0]    in_tree,
    input  wire [31:0]              in_val,
    input  wire                     in_final,
    input  wire                     in_err,
    output reg                      ov,
    output reg  [$clog2(NT)-1:0]    otree,
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
    reg [QW-1:0] qr, qw;
    reg [QW:0] qc;
    // held left operands
    reg [31:0] held [0:NT*LV-1];
    reg [NT*LV-1:0] have, herr;
    // adder result (event at level + 1)
    wire [31:0] sum;
    wire [1:0] err;
    wire sv;
    wire [PW+LW+1:0] st;     // {tree, level, final, err}
    // the event considered this cycle: adder result first, else the queue head
    wire use_q = !sv && qc != 0;
    wire        e_v = sv || qc != 0;
    wire [PW-1:0] e_t = sv ? st[PW+LW+1 -: PW] : qt[qr];
    wire [LW-1:0] e_l = sv ? st[LW+1 -: LW] : {LW{1'b0}};
    wire        e_f = sv ? st[1] : qf[qr];
    wire        e_e = sv ? (st[0] | err != 2'd0) : qe[qr];
    wire [31:0] e_d = sv ? sum : qv[qr];
    wire [PW+LW-1:0] hidx = e_t * LV + e_l;
    // trees' events inside the adder, and whether a tree holds anything above level e_l
    reg [2:0] infl [0:NT-1];
    reg above;
    integer li, ti;
    always @* begin
        above = 1'b0;
        for (li = 0; li < LV; li = li + 1)
            if (li > e_l && have[e_t * LV + li]) above = 1'b1;
    end
    wire mine_out = sv;                               // the event leaving the adder now is e_t's own
    wire idle_tree = infl[e_t] == (mine_out ? 3'd1 : 3'd0);
    wire early = (EARLY != 0) && e_v && e_f && !have[hidx] && !above && idle_tree;
    wire top = e_l == LV[LW-1:0] || early;
    wire pair = e_v && !top && have[hidx];
    wire promote = e_v && !top && !have[hidx] && e_f;
    wire hold = e_v && !top && !have[hidx] && !e_f;
    wire [PW-1:0] out_t = st[PW+LW+1 -: PW];
    wire [31:0] add_a = pair ? held[hidx] : e_d;
    wire [31:0] add_b = pair ? e_d : 32'd0;
    ot_fp32_add_rne_pipe u_add (.clk(clk), .rst_n(rst_n), .valid_in(pair | promote), .a(add_a), .b(add_b),
                                .y(sum), .err(err), .valid_out(sv));
    ot_hdc_delay #(.W(PW + LW + 2), .D(5)) u_t (.clk(clk), .rst_n(rst_n),
        .d({e_t, e_l + 1'b1, e_f, e_e | (pair && herr[hidx])}), .q(st));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            qr <= 0; qw <= 0; qc <= 0; have <= '0; herr <= '0; ov <= 1'b0; oerr <= 1'b0; fault <= 1'b0;
            for (ti = 0; ti < NT; ti = ti + 1) infl[ti] <= 3'd0;
        end else begin
            if (in_v) qw <= qw + 1'b1;
            if (use_q) qr <= qr + 1'b1;
            qc <= qc + (in_v ? 1'b1 : 1'b0) - (use_q ? 1'b1 : 1'b0);
            if (in_v && qc == QD && !use_q) fault <= 1'b1;
            for (ti = 0; ti < NT; ti = ti + 1)
                infl[ti] <= infl[ti] + (((pair | promote) && e_t == ti) ? 3'd1 : 3'd0)
                                     - ((sv && out_t == ti) ? 3'd1 : 3'd0);
            if (pair) have[hidx] <= 1'b0;
            if (hold) begin have[hidx] <= 1'b1; herr[hidx] <= e_e; end
            ov <= e_v && top;
            oerr <= e_v && top && e_e;
        end
    end
    always @(posedge clk) begin
        if (in_v) begin qv[qw] <= in_val; qt[qw] <= in_tree; qf[qw] <= in_final; qe[qw] <= in_err; end
        if (hold) held[hidx] <= e_d;
        oval <= e_d;
        otree <= e_t;
    end
endmodule
