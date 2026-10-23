`timescale 1ns/1ps
// HD-CTL (S81-HEAD 10-21): small kept-hierarchy helpers of the head-die controller (census structure: <= 32 loads per
// driver).  All are parameter-free, so Yosys keeps their instance names and never merges two copies back into one.

// one kept register copy of a 1-bit control (fan-out tree leaf)
(* keep_hierarchy = "yes" *) module ot_s81hd_kf (input wire ck, input wire d, output reg q);
    always @(posedge ck) q <= d;
endmodule

// 32-bit hold register with its own landed copies of the load enable (+1 edge on d and en together): one kept enable
// flop per 16 data bits (a mapped 2:1 hold mux loads its select twice), so the caller's enable drives 2 flops instead of
// every data flop.  Data unreset.
(* keep_hierarchy = "yes" *) module ot_s81hd_hreg32 (input wire ck, input wire en, input wire [31:0] d, output reg [31:0] q);
    (* keep = "true" *) reg en_a, en_b;
    reg [31:0] d_q;
    always @(posedge ck) begin
        en_a <= en; en_b <= en;
        d_q <= d;
        if (en_a) q[15:0] <= d_q[15:0];
        if (en_b) q[31:16] <= d_q[31:16];
    end
endmodule

// deterministic argmax compare (ot_rom_argmax_rows / ot_dsrom_head_bundle rule): v replaces u when its FP32 logit is
// strictly greater as a real (order-preserving key, -0 == +0), or equal with a LOWER row id.  One instance per select
// pick (ot_s81hd_pick) evaluates it once and fans the decision out through kept register copies.
(* keep_hierarchy = "yes" *) module ot_s81hd_cmp (
    input wire [31:0] ub, input wire [16:0] ur, input wire [31:0] vb, input wire [16:0] vr, output wire take);
    // FP32 real order without a conditional key inversion (the sign bits reach only the final select, so no sign net
    // fans out across the word): one magnitude compare, then the sign cases; +0 == -0.
    wire su = ub[31], sv = vb[31];
    wire mgt = vb[30:0] > ub[30:0];
    wire meq = vb[30:0] == ub[30:0];
    wire zz = (ub[30:0] == 31'd0) && (vb[30:0] == 31'd0);
    wire gt = !zz && ((su != sv) ? !sv : (sv ? (!mgt && !meq) : mgt));
    wire eq = zz || (su == sv && meq);
`ifdef OT_S81HD_CMP_MUT_TIE
    assign take = gt || (eq && vr > ur);     // mutant: highest id wins ties
`else
    assign take = gt || (eq && vr < ur);
`endif
endmodule

// registered deterministic pick of two {bits [48:17], row [16:0]} records: edge 1 = one compare + 4 kept copies of the
// decision (<= 13 mux bits each) + the operands delayed, edge 2 = the selected record.  Latency 2.
(* keep_hierarchy = "yes" *) module ot_s81hd_pick (input wire ck, input wire [48:0] u, input wire [48:0] v, output reg [48:0] y);
    wire take;
    ot_s81hd_cmp u_c (.ub(u[48:17]), .ur(u[16:0]), .vb(v[48:17]), .vr(v[16:0]), .take(take));
    (* keep = "true" *) reg [3:0] tk;
    reg [48:0] ud, vd;
    always @(posedge ck) begin
        tk <= {4{take}};
        ud <= u; vd <= v;
        y[12:0]  <= tk[0] ? vd[12:0]  : ud[12:0];
        y[24:13] <= tk[1] ? vd[24:13] : ud[24:13];
        y[36:25] <= tk[2] ? vd[36:25] : ud[36:25];
        y[48:37] <= tk[3] ? vd[48:37] : ud[48:37];
    end
endmodule
