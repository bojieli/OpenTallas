`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_qfd_vm_xpad2_t (PLAN 2026-10-13): TWO me-enabled register stages of W bits in one leaf = two ot_qfd_vm_xrelay_t in
// series with no pins between them.  Every x lane is padded to the common relay depth XPR (the plane column captures a
// whole beat on one edge); a pad pair in one tile costs one tile footprint instead of two (half of the padded depth of
// the plan is pads), and a pad stage needs no 500-um reach.  Same me discipline as the relay (own registered replicas
// of me, one per 128 flops per stage).  MUT (bench negative controls): 1 = stage 0 free-runs; 2 = one stage short.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_vm_xpad2_t #(
    parameter integer W = 512,
    parameter integer MEREG = 1,
    parameter integer MUT = 0
) (
    input  wire         clk,
    input  wire         me_e,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    wire [W-1:0] s;
    ot_qfd_vm_xrelay_t #(.W(W), .MEREG(MEREG), .MUT((MUT == 1) ? 1 : 0)) u_s0 (.clk(clk), .me_e(me_e), .d(d), .q(s));
    generate if (MUT == 2) begin : g_short
        assign q = s;
    end else begin : g_s1
        ot_qfd_vm_xrelay_t #(.W(W), .MEREG(MEREG)) u_s1 (.clk(clk), .me_e(me_e), .d(s), .q(q));
    end endgenerate
endmodule
