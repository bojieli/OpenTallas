`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen TP8 vector memory, BIT-PLANE x transport (claude/qwen-tp8-vm-1013, 2026-10-13).
// Why: the x read of ot_qfd_sp_vector_memory_bv moves NRB * 512 = 32,768 b from the bank regions to one rotation
// (rot1 coarse, rot2 fine, bv element shift).  With the rotation in the parent every mux stage is a die-wide bus:
// the 1,536-lane stage plan was REJECTED from real pins (512 lanes routed, centre cut 0.624).  rot1 / rot2 / bv move
// whole elements, so bit p of every 32-b element never meets another bit position: the network is cut into 32 PLANE
// leaves, each takes bit p of all NRB * 16 elements ONCE (2,048 lanes x 16 b) and keeps all three mux stages inside.
//
//   ot_qfd_vm_xrelay_t   one me-enabled register stage of W bits on an x lane (register at the pin; the next stage
//                        sits <= 500 um away).  x words leave the tile FIFO on ENGINE edges, so a relay must hold on
//                        a stalled edge: it owns a registered replica of me (MEREG: me_e is me one edge early).
//   ot_qfd_vm_xplane_t   one bit plane: pin flop (data and control), rot1, rot2, bv.  Control is the beat address
//                        (bank + element offset) and the count of in-range elements, registered at the pin one
//                        engine edge before the parent's s3 and carried inside (a3 / a4 / a5 = the parent's
//                        s3_a / s4_a / s5_a low bits).
// Latency: XPR relays + the plane pin flop replace the parent's RO x relays: x gains XPR + 1 - RO engine edges
// (parent XS / XVM carry it).  No arithmetic, order, credit or FIFO change: pop timing and NPP are untouched.
// MUT (bench negative controls): xrelay 1 = free-running (ignores me); xplane 1 = fine rotation one bank off,
// 2 = element shift one off, 3 = the in-range count ignored.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_vm_xrelay_t #(
    parameter integer W = 512,
    parameter integer MEREG = 1,
    parameter integer MUT = 0
) (
    input  wire         clk,
    input  wire         me_e,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    wire me;
    generate if (MEREG != 0) begin : g_mr
        (* keep = "true", dont_touch = "true" *) reg me_r;
        always @(posedge clk) me_r <= me_e;
        assign me = me_r;
    end else begin : g_mp
        assign me = me_e;
    end endgenerate
    always @(posedge clk) if (me || MUT == 1) q <= d;
endmodule

module ot_qfd_vm_xplane_t #(
    parameter integer NRB = 64,                 // row banks (multiple of 8)
    parameter integer MEREG = 1,
    parameter integer MUT = 0
) (
    input  wire                         clk,
    input  wire                         me_e,
    input  wire [NRB*16-1:0]            d,      // bit p of every element, bank-major
    input  wire [$clog2(NRB)+3:0]       c_a,    // beat address low bits {bank, element}, one engine edge before s3
    input  wire [$clog2((NRB-1)*16+1)-1:0] c_nv,   // in-range elements of the beat (0 .. BEAT), aligned with c_a
    output reg  [(NRB-1)*16-1:0]        q       // bv plane
);
    localparam integer LNRB = $clog2(NRB);
    localparam integer BEAT = (NRB - 1) * 16;
    localparam integer NVW = $clog2(BEAT + 1);
    wire me;
    generate if (MEREG != 0) begin : g_mr
        (* keep = "true", dont_touch = "true" *) reg me_r;
        always @(posedge clk) me_r <= me_e;
        assign me = me_r;
    end else begin : g_mp
        assign me = me_e;
    end endgenerate
    reg [NRB*16-1:0] pf, r1, r2;
    reg [LNRB+3:0]   a3, a4, a5;
    reg [NVW-1:0]    n3, n4, n5;
    wire [LNRB-1:0]  rc = a3[4 +: LNRB] & ~{{(LNRB-3){1'b0}}, 3'b111};
    wire [LNRB-1:0]  rf = {{(LNRB-3){1'b0}}, a4[6:4]} + ((MUT == 1) ? 1 : 0);
    wire [4:0]       sh = {1'b0, a5[3:0]} + ((MUT == 2) ? 5'd1 : 5'd0);
    integer i;
    always @(posedge clk) if (me) begin
        pf <= d; a3 <= c_a; n3 <= c_nv;
        a4 <= a3; n4 <= n3;
        a5 <= a4; n5 <= n4;
        for (i = 0; i < NRB; i = i + 1) begin
            r1[i*16 +: 16] <= pf[((i + rc) % NRB)*16 +: 16];
            r2[i*16 +: 16] <= r1[((i + rf) % NRB)*16 +: 16];
        end
        for (i = 0; i < BEAT; i = i + 1)
            q[i] <= (i < n5 || MUT == 3) ? r2[i + sh] : 1'b0;
    end
endmodule
