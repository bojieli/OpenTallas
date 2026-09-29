`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Adding return network of the V4.1 ROM element array (W10).
//
// A partial {row, lo, k, nseg, value} is the golden csum tree node over the row's segments
// [lo, lo + 2^k) (segments are equal power-of-two runs of chunks, so segment-level nodes are chunk-
// level nodes).  Two partials of one row are golden siblings when they have the same k and
// lo_a ^ lo_b == 2^k; their FP32 sum (left + right; IEEE addition commutes bit for bit) is the parent.
// A node whose right sibling lies wholly in the +0 padding (lo + 2^k >= nseg, lo even at level k)
// is promoted unchanged (+0 is an identity: no zero here is -0).  A partial is complete when
// lo = 0 and 2^k >= nseg.
//
// ot_v41_ret_node: one binary node of the return tree.  If the two children's head partials are
//   siblings it adds them (ot_fp32_add_rne_pipe, 5 cycles); otherwise it forwards one partial (older
//   side first; a lone head is forwarded after WAIT cycles or when its FIFO fills).  Every output is
//   5 cycles after its decision, one per cycle.
// ot_v41_ret_root: finishes every row: a D-entry buffer pairs arbitrary siblings and emits complete
//   rows as FP32 and BF16 (RNE).  Where partials are forwarded instead of added below, the root adds
//   them; the arithmetic, and therefore the result, is the same.
// ---------------------------------------------------------------------------
package ot_v41_ret_pkg;
    localparam integer TW = 16 + 5 + 3 + 5;   // {row, lo, k, nseg}
    function automatic [TW-1:0] norm(input [TW-1:0] t);
        reg [15:0] row;
        reg [4:0] lo, n;
        reg [2:0] k;
        integer i;
        begin
            {row, lo, k, n} = t;
            for (i = 0; i < 5; i = i + 1)
                if (!(lo == 5'd0 && (6'd1 << k) >= {1'b0, n}) && lo[k] == 1'b0 &&
                    ({1'b0, lo} + (6'd1 << k)) >= {1'b0, n})
                    k = k + 3'd1;
            norm = {row, lo, k, n};
        end
    endfunction
    function automatic complete(input [TW-1:0] t);
        complete = t[12:8] == 5'd0 && (6'd1 << t[7:5]) >= {1'b0, t[4:0]};
    endfunction
    function automatic sibling(input [TW-1:0] a, input [TW-1:0] b);
        sibling = a[28:13] == b[28:13] && a[7:5] == b[7:5] && a[4:0] == b[4:0] &&
                  (a[12:8] ^ b[12:8]) == (5'd1 << a[7:5]);
    endfunction
    function automatic [TW-1:0] parent(input [TW-1:0] a, input [TW-1:0] b);
        reg [4:0] lo;
        begin
            lo = (a[12:8] < b[12:8]) ? a[12:8] : b[12:8];
            parent = norm({a[28:13], lo, a[7:5] + 3'd1, a[4:0]});
        end
    endfunction
endpackage

module ot_v41_ret_node #(
    parameter integer D = 4,
    parameter integer WAIT = 2
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        a_v,
    input  wire [28:0] a_t,
    input  wire [31:0] a_d,
    input  wire        a_e,
    input  wire        b_v,
    input  wire [28:0] b_t,
    input  wire [31:0] b_d,
    input  wire        b_e,
    output wire        o_v,
    output wire [28:0] o_t,
    output wire [31:0] o_d,
    output wire        o_e,
    output reg         fault
);
    import ot_v41_ret_pkg::*;
    localparam integer AW = $clog2(D);
    reg [28:0] at [0:D-1], bt [0:D-1];
    reg [31:0] ad [0:D-1], bd [0:D-1];
    reg        ae [0:D-1], be [0:D-1];
    reg [AW-1:0] ar, aw, br, bw;
    reg [AW:0] ac, bc;
    reg [4:0] aw8, bw8;
    wire ah = ac != 0, bh = bc != 0;
    wire [28:0] ta = at[ar], tb = bt[br];
    wire add = ah && bh && sibling(ta, tb);
    wire fwd_a = !add && ah && (complete(ta) || bh || aw8 >= WAIT || ac == D);
    wire fwd_b = !add && !fwd_a && bh && (complete(tb) || aw8 >= WAIT || bw8 >= WAIT || bc == D);
    wire pop_a = add || fwd_a, pop_b = add || fwd_b;
    wire [31:0] sum;
    wire [1:0] err;
    wire sv;
    ot_fp32_add_rne_pipe u_add (.clk(clk), .rst_n(rst_n), .valid_in(add), .a(ad[ar]), .b(bd[br]),
                                .y(sum), .err(err), .valid_out(sv));
    wire [28:0] nt = add ? parent(ta, tb) : (fwd_a ? ta : tb);
    wire [31:0] fd = fwd_a ? ad[ar] : bd[br];
    wire fe = add ? (ae[ar] | be[br]) : (fwd_a ? ae[ar] : be[br]);
    wire [31:0] fdd;
    wire [30:0] dt;
    ot_hdc_delay #(.W(32), .D(5)) u_fd (.clk(clk), .rst_n(rst_n), .d(fd), .q(fdd));
    ot_hdc_delay #(.W(31), .D(5)) u_dt (.clk(clk), .rst_n(rst_n), .d({nt, add, fe}), .q(dt));
    reg [4:0] vp;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ar <= 0; aw <= 0; br <= 0; bw <= 0; ac <= 0; bc <= 0; vp <= 0; aw8 <= 0; bw8 <= 0; fault <= 1'b0;
        end else begin
            vp <= {vp[3:0], add | fwd_a | fwd_b};
            if (a_v) aw <= aw + 1'b1;
            if (b_v) bw <= bw + 1'b1;
            if (pop_a) ar <= ar + 1'b1;
            if (pop_b) br <= br + 1'b1;
            ac <= ac + (a_v ? 1'b1 : 1'b0) - (pop_a ? 1'b1 : 1'b0);
            bc <= bc + (b_v ? 1'b1 : 1'b0) - (pop_b ? 1'b1 : 1'b0);
            aw8 <= (pop_a || !ah) ? 5'd0 : (aw8 == 5'd31 ? aw8 : aw8 + 1'b1);
            bw8 <= (pop_b || !bh) ? 5'd0 : (bw8 == 5'd31 ? bw8 : bw8 + 1'b1);
            if ((a_v && ac == D && !pop_a) || (b_v && bc == D && !pop_b)) fault <= 1'b1;
        end
    end
    always @(posedge clk) begin
        if (a_v) begin at[aw] <= norm(a_t); ad[aw] <= a_d; ae[aw] <= a_e; end
        if (b_v) begin bt[bw] <= norm(b_t); bd[bw] <= b_d; be[bw] <= b_e; end
    end
    assign o_v = vp[4];
    assign o_t = dt[30:2];
    assign o_d = dt[1] ? sum : fdd;
    assign o_e = dt[0] | (dt[1] && err != 2'd0);
endmodule

module ot_v41_ret_root #(
    parameter integer D = 16,
    parameter integer QD = 16
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        i_v,
    input  wire [28:0] i_t,
    input  wire [31:0] i_d,
    input  wire        i_e,
    output reg         r_v,
    output reg  [15:0] r_row,
    output reg  [31:0] r_fp32,
    output reg  [15:0] r_bf16,
    output reg         r_e,
    output reg         fault
);
    import ot_v41_ret_pkg::*;
    localparam integer QW = $clog2(QD);
    // input queue
    reg [28:0] qt [0:QD-1];
    reg [31:0] qd [0:QD-1];
    reg        qe [0:QD-1];
    reg [QW-1:0] qr, qw;
    reg [QW:0] qc;
    // buffer
    reg        bv [0:D-1];
    reg [28:0] bt [0:D-1];
    reg [31:0] bd [0:D-1];
    reg        be [0:D-1];
    // adder
    wire [31:0] sum;
    wire [1:0] err;
    wire sv;
    reg add;
    reg [31:0] add_a, add_b;
    wire [29:0] st;
    // candidate: adder result first, else the queue head
    wire use_q = !sv && qc != 0;
    wire [28:0] ct = sv ? st[29:1] : norm(qt[qr]);
    wire [31:0] cd = sv ? sum : qd[qr];
    wire        ce = sv ? (st[0] | err != 2'd0) : qe[qr];
    wire        cv = sv || qc != 0;
    integer k, hit, fr;
    always @* begin
        hit = -1; fr = -1;
        for (k = D - 1; k >= 0; k = k - 1) begin
            if (bv[k] && sibling(bt[k], ct)) hit = k;
            if (!bv[k]) fr = k;
        end
    end
    wire [28:0] pt = (hit >= 0) ? parent(bt[hit], ct) : 29'd0;
    ot_fp32_add_rne_pipe u_add (.clk(clk), .rst_n(rst_n), .valid_in(add), .a(add_a), .b(add_b),
                                .y(sum), .err(err), .valid_out(sv));
    reg [29:0] tag_in;
    ot_hdc_delay #(.W(30), .D(5)) u_t (.clk(clk), .rst_n(rst_n), .d(tag_in), .q(st));
    wire [32:0] rb = {1'b0, cd} + 33'h7FFF + {32'd0, cd[16]};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            qr <= 0; qw <= 0; qc <= 0; r_v <= 1'b0; fault <= 1'b0; add <= 1'b0;
            for (k = 0; k < D; k = k + 1) bv[k] <= 1'b0;
        end else begin
            r_v <= 1'b0;
            add <= 1'b0;
            if (i_v) qw <= qw + 1'b1;
            if (use_q) qr <= qr + 1'b1;
            qc <= qc + (i_v ? 1'b1 : 1'b0) - (use_q ? 1'b1 : 1'b0);
            if (i_v && qc == QD && !use_q) fault <= 1'b1;
            if (cv) begin
                if (complete(ct)) begin
                    r_v <= 1'b1;
                end else if (hit >= 0) begin
                    add <= 1'b1;
                    bv[hit] <= 1'b0;
                end else if (fr >= 0) begin
                    bv[fr] <= 1'b1;
                end else fault <= 1'b1;
            end
        end
    end
    always @(posedge clk) begin
        if (i_v) begin qt[qw] <= i_t; qd[qw] <= i_d; qe[qw] <= i_e; end
        r_row <= ct[28:13]; r_fp32 <= cd; r_bf16 <= rb[31:16]; r_e <= ce;
        if (cv && !complete(ct) && hit >= 0) begin
            // left operand: lower lo
            if (bt[hit][12:8] < ct[12:8]) begin add_a <= bd[hit]; add_b <= cd; end
            else begin add_a <= cd; add_b <= bd[hit]; end
        end
        tag_in <= {pt, (hit >= 0) ? (be[hit] | ce) : 1'b0};
        if (cv && !complete(ct) && hit < 0 && fr >= 0) begin bt[fr] <= ct; bd[fr] <= cd; be[fr] <= ce; end
    end
endmodule
