`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// SIMULATION copy of rtl/hdc/ot_hdc_prefix.sv (W13b): the same modules (ot_hdc_ksadd_k, ot_hdc_inc_k), each prefix
// level written as one vector assignment instead of a per-bit generate, whose L x (W+1) scopes make Icarus
// elaboration quadratic (tc_col L=16: 15.3 s -> 0.17 s; a 256-lane SM did not compile in 5 h).  Proven equal to
// the synthesised file by yosys equiv_status (results/rtl/ot_hdc_prefix_vec_equiv.json).  Used only by the
// exactness campaigns (tools/rtl_gpu_sm_exact.py); synthesis keeps rtl/hdc/ot_hdc_prefix.sv (pinned by records).
//
// Explicit log-depth adders (W10, 72f00b86; shared FP primitive copy owned by W11, rtl/hdc/ot_hdc_prefix.sv).
//
// Written as behavioural `a + b` or `a + inc`, yosys/ABC maps these adders as carry ripples (chains of MAJ or
// OR cells) even with ADDER_MAP_FILE cleared: measured at ORFS WC, 0.833 ns, a 28-bit add inside the element
// took 920 ps and a 24-bit rounding increment a chain of ten OR4/OR5 cells (W10 and W13, 2026-09-30).  Here each
// Kogge-Stone prefix level is a (* keep *) net, so synthesis must keep log2(W) levels.
//
// ot_v41_ksadd: s = a + b + cin (W bits), cout.
// ot_v41_inc:   y = a + inc (W bits), co (the carry out of the top bit).
// ---------------------------------------------------------------------------
module ot_hdc_ksadd_k #(
    parameter integer W = 28
) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    input  wire         cin,
    output wire [W-1:0] s,
    output wire         cout
);
    localparam integer L = $clog2(W + 1);
    // position 0 is the carry-in; bit i of the operands is position i + 1
    (* keep *) wire [W:0] g [0:L];
    (* keep *) wire [W:0] p [0:L];
    assign g[0] = {a & b, cin};
    assign p[0] = {a ^ b, 1'b0};
    // one vector assignment per level (bit i >= 2^l combines with bit i - 2^l, the rest pass through): the same
    // gates as a per-bit generate, without its L x (W+1) scopes, which make Icarus elaboration quadratic in the
    // instance count (a 256-lane SM did not finish compiling in 5 h)
    genvar l;
    generate
        for (l = 0; l < L; l = l + 1) begin : g_lv
            localparam [W:0] LOW = (({{W{1'b0}}, 1'b1}) << (1 << l)) - 1'b1;
            assign g[l + 1] = g[l] | (p[l] & (g[l] << (1 << l)));
            assign p[l + 1] = p[l] & ((p[l] << (1 << l)) | LOW);
        end
    endgenerate
    // carry into operand bit i = the group generate of positions [0, i]
    assign s = (a ^ b) ^ g[L][W-1:0];
    assign cout = g[L][W];
endmodule


module ot_hdc_inc_k #(
    parameter integer W = 24
) (
    input  wire [W-1:0] a,
    input  wire         inc,
    output wire [W-1:0] y,
    output wire         co
);
    localparam integer L = $clog2(W + 1);
    // t[i]: all of positions [0, i] are one, position 0 being the increment
    (* keep *) wire [W:0] t [0:L];
    assign t[0] = {a, inc};
    genvar l;
    generate
        for (l = 0; l < L; l = l + 1) begin : g_lv
            localparam [W:0] LOW = (({{W{1'b0}}, 1'b1}) << (1 << l)) - 1'b1;
            assign t[l + 1] = t[l] & ((t[l] << (1 << l)) | LOW);
        end
    endgenerate
    assign y = a ^ t[L][W-1:0];
    assign co = t[L][W];
endmodule
