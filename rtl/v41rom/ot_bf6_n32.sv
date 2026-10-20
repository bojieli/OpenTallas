`timescale 1ns/1ps
// S81-BF6 2026-10-20: native-census (<= 32 loads per driver) building blocks for the BF front core
// (ot_v41_bf_front_core_roots N32 = 1).  Zero added cycles: every copy is the same register function of the same inputs.
//
// ot_bf6_cen_pool: N kept copies of the core's registered gate enable cen (c10: one ungated balanced tree, every former
// gclk register block loads under cen).  The original is u_cen = kreg(D = ze_d = go_pin || z_q, async set by rst_n_pin)
// with z_q = u_z = kreg(D = z_d, async set).  Here NA = ceil(N / 32) kept copies of u_z (same D, same async set) each
// feed one ze_d copy (go_pin || za) that drives <= 32 leaf copies.  The leaves carry no reset: every leaf loads
// go_pin || 1 = 1 on each clock edge while rst_n_pin is low (as the async-set original holds 1), so from the first
// clock edge of reset on every leaf equals the original u_cen (the reset net then drives NA flops, not N).
(* keep_hierarchy *)
module ot_bf6_cen_pool #(
    parameter integer N = 1
) (
    input  wire         clk,
    input  wire         rst_n_pin,
    input  wire         z_d,
    input  wire         go_pin,
    output wire [N-1:0] ce
);
    localparam integer NA = (N + 31) / 32;
    wire [NA-1:0] za;
    for (genvar a = 0; a < NA; a = a + 1) begin : g_a
        ot_v41_kreg #(.W(1), .AR(1), .RV(1'b1)) u_za (.clk(clk), .arst_n(rst_n_pin), .d(z_d), .q(za[a]));
    end
    // one kept OR per u_z copy (ze_d = go_pin || z_q), so go_pin drives exactly NA gates and each OR <= 32 leaves
    wire [NA-1:0] zed;
    for (genvar a = 0; a < NA; a = a + 1) begin : g_o
        ot_bf6_kor u_or (.a(go_pin), .b(za[a]), .y(zed[a]));
    end
    for (genvar c = 0; c < N; c = c + 1) begin : g_l
        ot_v41_kreg #(.W(1)) u_ce (.clk(clk), .arst_n(1'b1), .d(zed[c / 32]), .q(ce[c]));
    end
endmodule

// ot_bf6_ereg: a W-bit register loaded under chunk enables: chunk k (bits [CW*k +: CW]) loads d when ce[k].  With the
// ASAP7 flop-plus-hold-mux mapping each bit is 2 enable loads, so CW = 16 keeps every enable copy at <= 32 loads.
module ot_bf6_ereg #(
    parameter integer W = 16,
    parameter integer CW = 16
) (
    input  wire                     clk,
    input  wire [(W+CW-1)/CW-1:0]   ce,
    input  wire [W-1:0]             d,
    output reg  [W-1:0]             q
);
    localparam integer NC = (W + CW - 1) / CW;
    for (genvar k = 0; k < NC; k = k + 1) begin : g_c
        localparam integer LO = CW * k;
        localparam integer HI = (CW * (k + 1) < W) ? CW * (k + 1) : W;
        always @(posedge clk) if (ce[k]) q[HI-1:LO] <= d[HI-1:LO];
    end
endmodule

// ot_bf6_kcopy: K kept copies of a 1-bit register (q[k] <= d every edge, optional async reset to RV), so each copy can
// drive its own <= 32-load group.  Used for go_e, the core reset synchroniser and the FP8 half select.
module ot_bf6_kcopy #(
    parameter integer K = 1,
    parameter integer AR = 0,
    parameter         RV = 1'b0
) (
    input  wire         clk,
    input  wire         arst_n,
    input  wire         d,
    output wire [K-1:0] q
);
    for (genvar k = 0; k < K; k = k + 1) begin : g_k
        ot_v41_kreg #(.W(1), .AR(AR), .RV(RV)) u_k (.clk(clk), .arst_n(arst_n), .d(d), .q(q[k]));
    end
endmodule

// ot_bf6_kand: a 2-input AND that synthesis keeps as its own instance, so a per-group select formed from a shared
// term is a real net of its own (technology mapping cannot fold the shared term back into every bit of the group).
(* keep_hierarchy *)
module ot_bf6_kand (
    input  wire a,
    input  wire b,
    output wire y
);
    assign y = a & b;
endmodule

// ot_bf6_kor: a 2-input OR kept as its own instance (see ot_bf6_kand).
(* keep_hierarchy *)
module ot_bf6_kor (
    input  wire a,
    input  wire b,
    output wire y
);
    assign y = a | b;
endmodule
