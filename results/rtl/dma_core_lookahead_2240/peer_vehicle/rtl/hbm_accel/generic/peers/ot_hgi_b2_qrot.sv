`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// el1011-hbm-b2 (2026-10-12): the B2 cluster DMA's stack rotation, so ONE hardened DMA unit serves every cluster (harden
// once, replicate; the cluster number is a strap pin, not a parameter).  The DMA core is built as cluster 0 (B2 = 1,
// QID = 0).  In: an HBM-space descriptor (space d[1:0] = 0, byte base d[47:8]) has its stack field d[8+SBIT+1:8+SBIT]
// rotated by -qid (mod 4), so the cluster's own stack appears as stack 0 to the core and every other stack keeps its
// relative position (STRIPE4 row o of base stack s sits on core stack (s + o - qid) mod 4, own rows <=> core stack 0; a
// linear move off the cluster's stack is off core stack 0 and faults as before; address arithmetic carries across stack
// bits mod 4 the same way).  Out: an HBM request address gets +qid on its stack field (mod 4).  Pure wiring + 2-bit
// adders; no state.  The STRIPE4 code d[47:45] and every non-HBM descriptor pass unchanged.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_b2_qrot_d #(parameter integer SBIT = 35) (
    input  wire [1:0]   qid,
    input  wire [255:0] d,
    output wire [255:0] r
);
    wire hbm = d[1:0] == 2'd0;
    wire [1:0] s = d[8 + SBIT +: 2] - qid;
    generate if (SBIT + 10 < 256) begin : g
        assign r = hbm ? {d[255:8 + SBIT + 2], s, d[8 + SBIT - 1:0]} : d;
    end endgenerate
endmodule

module ot_hgi_b2_qrot_a #(parameter integer SBIT = 35, parameter integer AW = 37) (
    input  wire [1:0]    qid,
    input  wire [AW-1:0] a,
    output wire [AW-1:0] r
);
    wire [1:0] s = a[SBIT +: 2] + qid;
    generate if (SBIT + 2 == AW) begin : top
        assign r = {s, a[SBIT - 1:0]};
    end else begin : mid
        assign r = {a[AW-1:SBIT + 2], s, a[SBIT - 1:0]};
    end endgenerate
endmodule
`default_nettype wire
