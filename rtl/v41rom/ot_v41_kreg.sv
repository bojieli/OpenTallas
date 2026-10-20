`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_kreg: a W-bit register that synthesis keeps as its own instance (DS-V4.1 ROM q-element QZ, 2026-10-04).
//
// Yosys opt_merge merges flip-flops with identical inputs even when the reg carries (* keep *) / dont_touch
// (measured on the ORFS image's Yosys 0.68: two `(* keep *) reg r` copies fed by one net leave one cell).  In the
// QPIPE q-pair that silently undid the per-macro copies of the issue control and merged the two macro halves'
// lanes (x operand registers, chain forward selects): one register drove both halves across the 510 um die
// (R_cap0 routed netlist: g_mac[0] p0_xq only, r_i2_bk only in g_mac[1]).  A keep_hierarchy module instance is
// not a built-in cell, so it is never merged; each instance is placed and timed on its own.
//
// Function: q <= d on every rising clk edge; with AR = 1, q is held at RV while arst_n is low (asynchronous).
// ---------------------------------------------------------------------------
(* keep_hierarchy *)
module ot_v41_kreg #(
    parameter integer W = 1,
    parameter integer AR = 0,
    parameter [W-1:0] RV = '0
) (
    input  wire         clk,
    input  wire         arst_n,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    if (AR != 0) begin : g_ar
        always @(posedge clk or negedge arst_n) if (!arst_n) q <= RV; else q <= d;
    end else begin : g_nar
        always @(posedge clk) q <= d;
    end
endmodule

`ifdef OT_BF_N32
// ---------------------------------------------------------------------------
// S81-BF6 native32 (2026-10-20, opt-in OT_BF_N32): kept COMBINATIONAL copies.  ABC merges structurally identical
// logic across the flattened design (one zero detect of a chain sum served the chain's PD step 0 AND the next tree
// adder: 68 loads), so a replicated predicate is only replicated when it is its own keep_hierarchy instance (the
// ot_v41_kreg rule for registers, applied to gates).  Each instance computes the same function of the same nets; no
// state, no cycle.
// ---------------------------------------------------------------------------
// fp32 field class of x[30:0]: fz = exponent field 0, ff = exponent field all ones, mz = |x| == 0
(* keep_hierarchy *)
module ot_v41_n32_fcls (
    input  wire [30:0] x,
    output wire        fz,
    output wire        ff,
    output wire        mz
);
    assign fz = (x[30:23] == 8'd0);
    assign ff = (x[30:23] == 8'hff);
    assign mz = (x[30:0] == 31'd0);
endmodule
// y = a & b (kept copy of a two-register valid term)
(* keep_hierarchy *)
module ot_v41_n32_kand2 (input wire a, input wire b, output wire y);
    assign y = a & b;
endmodule
// bterm coarse normalise predicates of m[40:0]: z = {z32, z16, z8} of the 32 / 16 / 8 leading-zero steps, and the
// shift lza = 8 * z as a ONE-HOT oh[k] (lza == 8k), so a caller slice selects m << lza as one AND-OR per bit
(* keep_hierarchy *)
module ot_v41_n32_cnz (input wire [40:0] m, output wire [2:0] z, output wire [7:0] oh);
    wire        z32 = (m[40:9] == 32'd0);
    wire [40:0] m1 = z32 ? (m << 32) : m;
    wire        z16 = (m1[40:25] == 16'd0);
    wire [40:0] m2 = z16 ? (m1 << 16) : m1;
    wire        z8 = (m2[40:33] == 8'd0);
    assign z = {z32, z16, z8};
    for (genvar k = 0; k < 8; k = k + 1) begin : g_oh
        assign oh[k] = (z == k);
    end
endmodule
// fadd step 0 bypass-code selects of (a, b): sa = take a, sb = take b (code = sa ? a : sb ? b : 0, as
// nonf ? 0 : az ? (bz ? 0 : b) : a)
(* keep_hierarchy *)
module ot_v41_n32_csel (input wire [30:0] a, input wire [30:0] b, output wire sa, output wire sb);
    wire nonf = (a[30:23] == 8'hff) || (b[30:23] == 8'hff);
    wire az = (a == 31'd0);
    wire bz = (b == 31'd0);
    assign sa = !nonf && !az;
    assign sb = !nonf && az && !bz;
endmodule
// fadd step 0 bundle (identical to ot_v41_fadd_s0 / the step 0 of ot_v41_fadd*): the operand classes for the fields
// and flags come from kept ot_v41_n32_fcls copies, the bypass code halves each from their own kept ot_v41_n32_csel
// (the zero / non-finite selects of the code mux were the 33..68-load fanout of the native85 census)
module ot_v41_n32_s0 (
    input  wire         valid_in,
    input  wire [31:0]  a,
    input  wire [31:0]  b,
    output wire [104:0] o0
);
    wire afz0, aff0, amz0, bfz0, bff0, bmz0, sa0, sb0, sa1, sb1;
    ot_v41_n32_fcls u_a0 (.x(a[30:0]), .fz(afz0), .ff(aff0), .mz(amz0));
    ot_v41_n32_fcls u_b0 (.x(b[30:0]), .fz(bfz0), .ff(bff0), .mz(bmz0));
    ot_v41_n32_csel u_k0 (.a(a[30:0]), .b(b[30:0]), .sa(sa0), .sb(sb0));
    ot_v41_n32_csel u_k1 (.a(a[30:0]), .b(b[30:0]), .sa(sa1), .sb(sb1));
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [7:0]  a_exp0 = afz0 ? 8'd1 : a_field;
    wire [7:0]  b_exp0 = bfz0 ? 8'd1 : b_field;
    wire [23:0] a_man0 = {!afz0, a[22:0]};
    wire [23:0] b_man0 = {!bfz0, b[22:0]};
    wire        nonf0 = aff0 || bff0;
    wire [23:0] dm0;
    wire        age0;
    ot_v41_ksadd #(.W(24)) u_cm0 (.a(a_man0), .b(~b_man0), .cin(1'b1), .s(dm0), .cout(age0));
    wire [15:0] code_l = ({16{sa0}} & a[15:0]) | ({16{sb0}} & b[15:0]);
`ifdef OT_BF_N32_MUT_S0
    // negative control: the high code half drops its b select (a zero a no longer bypasses to b's high half)
    wire [15:0] code_h = {16{sa1}} & a[31:16];
`else
    wire [15:0] code_h = ({16{sa1}} & a[31:16]) | ({16{sb1}} & b[31:16]);
`endif
    assign o0 = {valid_in, a_exp0, b_exp0, a_man0, b_man0, a[31], b[31], nonf0, amz0, bmz0,
                 b_exp0 > a_exp0, b_exp0 == a_exp0, !age0, code_h, code_l};
endmodule
`endif
