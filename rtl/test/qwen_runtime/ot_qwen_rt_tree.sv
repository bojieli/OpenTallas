`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// SIMULATION-ONLY runtime decomposition of rtl/hdc/ot_hdc_matvec.sv, part 3.
//
// ot_qwen_rt_tree_cell: split-tree level `lv`, output group position q.  The
// original level holds the whole previous level for TA cycles (u_hold) and
// registers, per lane, either the pair sum of groups 2q and 2q+1 (q < G>>lv)
// or the held value of group q.  ADDS = 1 is a position that owns a pair;
// ADDS = 0 is the g_rest (held-only) region.  Timing, adder and select are
// the original's; the host drives v/sel from the sequencer's per-level
// b_reduce_valid / b_reduce_select.
//
// ot_qwen_rt_amax_tree: LEVELS registered compare levels of the argmax tree,
// the original g_node statement unchanged.  The host stacks instances above
// the per-group nodes produced by ot_qwen_rt_matvec_slice; padded leaves are
// constant zero exactly as in the original g_leaf_pad/g_pad.
// ---------------------------------------------------------------------------
module ot_qwen_rt_tree_cell #(
    parameter integer W = 16,
    parameter integer ADDS = 1
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            v,
    input  wire            sel,
    input  wire [W*32-1:0] h,
    input  wire [W*32-1:0] a,
    input  wire [W*32-1:0] b,
    output wire [W*32-1:0] y,
    output wire            fault
);
    localparam integer TA = 3;
    wire [W*32-1:0] held;
    ot_hdc_delay #(.W(W*32), .D(TA)) u_hold (.clk(clk), .rst_n(rst_n), .d(h), .q(held));
    reg [W*32-1:0] lq;
    genvar p;
    generate if (ADDS != 0) begin : g_add
        wire [W-1:0] pf;
        for (p = 0; p < W; p = p + 1) begin : g_pair
            wire [31:0] s_out;
            ot_hdc_qadd u_add (clk, rst_n, v, a[32*p +: 32], b[32*p +: 32], s_out, pf[p]);
            always @(posedge clk) lq[32*p +: 32] <= sel ? s_out : held[32*p +: 32];
        end
        assign fault = |pf;
    end else begin : g_rest
        always @(posedge clk) lq <= held;
        assign fault = 1'b0;
    end endgenerate
    assign y = lq;
endmodule

module ot_qwen_rt_amax_tree #(
    parameter integer NW = 16,
    parameter integer LEVELS = 4
) (
    input  wire                            clk,
    input  wire [(1+32+NW)*(1<<LEVELS)-1:0] x,
    output wire [1+32+NW-1:0]              y
);
    localparam integer CW = 1 + 32 + NW;
    localparam integer AN = 1 << LEVELS;
    wire [CW*AN-1:0] alv [0:LEVELS];
    assign alv[0] = x;
    genvar lv, e;
    generate
        for (lv = 1; lv <= LEVELS; lv = lv + 1) begin : g_alvl
            for (e = 0; e < (AN >> lv); e = e + 1) begin : g_node
                wire [CW-1:0] x0 = alv[lv-1][CW*(2*e) +: CW];
                wire [CW-1:0] x1 = alv[lv-1][CW*(2*e+1) +: CW];
                wire          x0_wins = x0[CW-1] && (!x1[CW-1] || x0[CW-2 -: 32] > x1[CW-2 -: 32] ||
                                        (x0[CW-2 -: 32] == x1[CW-2 -: 32] && x0[NW-1:0] < x1[NW-1:0]));
                reg  [CW-1:0] c;
                always @(posedge clk) c <= x0_wins ? x0 : x1;
                assign alv[lv][CW*e +: CW] = c;
            end
            if ((AN >> lv) < AN) begin : g_pad
                assign alv[lv][CW*AN-1 : CW*(AN >> lv)] = 0;
            end
        end
    endgenerate
    assign y = alv[LEVELS][CW-1:0];
endmodule
