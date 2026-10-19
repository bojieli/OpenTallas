`timescale 1ns/1ps
`default_nettype none
// H-NETLIST/vmsm 2026-10-15 (G-SMVM-AQFP4): the x-load block-dot quantiser with its format MODE folded in as a parameter.
// The HBM SM x-load quantises x to FP8 (quant_fp8 / qdq_fp8) for BOTH block-dot weight formats (x_fmt 1 = FP8 weights,
// 2 = FP4 weights: FP8 activations); FP4 activation QDQ (qdq_fp4_e8m0: indexer q / k) is the QUANT engine's, never the
// x-load's.  The cl2 parent tied ot_hbm_xp_aq_tree13.fp4 to 1'b0 -- a mode is not an identity strap (owner rule), so the
// die master of the 8 x-load quantisers is this leaf with FP4 a compile-time parameter (FP4=0 for the x-load).  Body =
// the CLOSED tile ot_hbm_xp_aq_tree13 unchanged (S0 input / output registers at its pins, 13 edges); with FP4 constant
// synthesis drops the fp4 pipeline bits: the hgi_xp_aq kit must be re-hardened under this name (no new arithmetic).
module ot_hbm_xp_aq_tree13_fmt #(parameter integer FP4=0, parameter integer MUT=0,
    parameter integer RSMUT=0) (   // RSMUT bench only: 1 = a mid-run reset does not reach the body (power-on reset only)
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire [1023:0] x,
    output wire          vo,
    output wire [255:0]  q,
    output wire signed [9:0] e,
    output wire [511:0]  y,
    output wire          fault
);
    initial if (FP4 != 0 && FP4 != 1) $fatal(1, "ot_hbm_xp_aq_tree13_fmt: FP4 is 0 (fp8) or 1 (fp4_e8m0)");
    localparam [0:0] MODE = (FP4 != 0) ? 1'b1 : 1'b0;
    // Local reset synchroniser at the pin (HBM-NATIVE 2026-10-17; the col_su r3 collar shape). The native pin audit of
    // the closed f1 view found the raw rst_n pin async-clearing the body's valid chain across the 183.6-um tile
    // (capture 272.7 ps > 190). The pin now drives ONE plain clk flop; its stage-2 Q is the body reset. Assert and
    // release both take +2 clk edges; the 13-edge datapath is unchanged (cycles 0).
    reg [1:0] rsync;
    always @(posedge clk) rsync <= {rsync[0], rst_n};
    wire rst_q_n;
    generate if (RSMUT == 1) begin : g_rsmut
        reg por_done = 1'b0;
        always @(posedge clk) if (rsync[1] === 1'b1) por_done <= 1'b1;
        assign rst_q_n = rsync[1] | por_done;
    end else begin : g_rsync
        assign rst_q_n = rsync[1];
    end endgenerate
    ot_hbm_xp_aq_tree13 #(.MUT(MUT)) u_aq (.clk(clk), .rst_n(rst_q_n), .v(v), .fp4(MODE), .x(x),
        .vo(vo), .q(q), .e(e), .y(y), .fault(fault));
endmodule
`default_nettype wire
