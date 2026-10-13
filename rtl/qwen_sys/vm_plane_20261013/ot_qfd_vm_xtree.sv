`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen TP8 vector memory, bit-plane x transport: the leaves AROUND the plane (claude/qwen-tp8-vm-rtl, 2026-10-13).
// ot_qfd_vm_xplane.sv left three things in the parent that have no physical owner: (1) the plane control and me were
// broadcast in ONE edge to 32 plane leaves / 328 relay leaves / 8 regions; (2) line (NX * 32 = 65,536 flops, a 14:1
// constant-source mux per entry) and (3) x_q (65,536 flops, the 2^sp replication) were parent soft logic.
//
//   ot_qfd_vm_fan_t     one stage of a registered fan-out tree: a W-bit register at the pin, its q wired to <= ~32
//                       loads (<= 4 child leaves of <= 8 pins each, or the next fan stages).  EN = 0: free-running
//                       (the me tree itself: me enters the tree K + 1 edges early and leaves it as every leaf's me_e).
//                       EN = 1: engine-enabled (control words: tapped K engine edges early in the parent's seam
//                       queue, so K stages land them on the original edge).  No replicated outputs, no logic.
//   ot_qfd_vm_xline_t   ONE BIT POSITION of line and of the x_q replication stage.  line[c] takes bv[(c * DV) % BEAT]
//                       of descriptor DV and x_q[i] takes line[i mod 2^sp]: both move whole elements, so bit p never
//                       meets another bit position (the same cut as rot1 / rot2 / bv).  Pin flops on the bv plane
//                       and on both control words, line, then the registered replication q.  q is the flat x_q
//                       plane delayed by EXACTLY one engine edge when c_* = the parent's s6_* and o_* = co_*.
//   ot_qfd_vm_xqface_t  the x_q register AT THE CONSUMER FACE: W bits of x_q (element-major slice), engine-enabled.
//                       xline q -> XQR x ot_qfd_vm_xrelay_t -> this leaf; x_q = xline q + XQR + 1 engine edges.
// x latency: + 1 (xline pin flop) + XQR + 1 (face) engine edges on top of the plane transport; the parent schedules
// against XVM - (XQR + 2) internally, so the consumer's XVM grows by XQR + 2.  Control latency: 0 (tapped early).
// MUT (negative controls): fan 1 = transparent (one edge short); xline 1 = line source one element off, 2 = the
// 2^sp write bound ignored, 3 = replication mask one bit wide; xqface 1 = free-running (ignores me).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_vm_fan_t #(
    parameter integer W = 1,
    parameter integer EN = 0,
    parameter integer MEREG = 1,
    parameter integer MUT = 0
) (
    input  wire         clk,
    input  wire         me_e,           // EN = 1 only (tie 0 when EN = 0)
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    wire me;
    generate if (EN != 0 && MEREG != 0) begin : g_mr
        (* keep = "true", dont_touch = "true" *) reg me_r;
        always @(posedge clk) me_r <= me_e;
        assign me = me_r;
    end else begin : g_mp
        assign me = (EN != 0) ? me_e : 1'b1;
    end endgenerate
    (* keep = "true", dont_touch = "true" *) reg [W-1:0] r;
    always @(posedge clk) if (me) r <= d;
    assign q = (MUT == 1) ? d : r;
endmodule

module ot_qfd_vm_xline_t #(
    parameter integer NRB = 64,
    parameter integer SMIN = 7,
    parameter integer SMAX = 11,
    parameter integer BMAX = 8,
    parameter integer ND = 14,
    parameter [ND*8-1:0] DSET = {8'd96, 8'd64, 8'd48, 8'd32, 8'd24, 8'd16, 8'd12, 8'd8, 8'd6, 8'd4, 8'd3, 8'd2, 8'd1, 8'd0},
    parameter integer MEREG = 1,
    parameter integer MUT = 0
) (
    input  wire                        clk,
    input  wire                        me_e,
    input  wire [(NRB-1)*16-1:0]       d,       // bv plane (ot_qfd_vm_xplane_t q)
    input  wire                        c_v,     // line write: the parent's s6_bv / s6_d / s6_j / s6_sp (aligned with d)
    input  wire [ND-1:0]               c_d,
    input  wire [$clog2(BMAX):0]       c_j,
    input  wire [3:0]                  c_sp,
    input  wire                        o_v,     // x_q capture: the parent's co_v / co_sp
    input  wire [3:0]                  o_sp,
    output reg  [(1<<SMAX)-1:0]        q        // x_q plane, one engine edge after the flat x_q
);
    localparam integer BEAT = (NRB - 1) * 16;
    localparam integer NX = 1 << SMAX;
    localparam integer LB = $clog2(BMAX) + 1;
    wire me;
    generate if (MEREG != 0) begin : g_mr
        (* keep = "true", dont_touch = "true" *) reg me_r;
        always @(posedge clk) me_r <= me_e;
        assign me = me_r;
    end else begin : g_mp
        assign me = me_e;
    end endgenerate
    reg [BEAT-1:0] pd;
    reg            pv, ov;
    reg [ND-1:0]   pdd;
    reg [LB-1:0]   pj;
    reg [3:0]      psp, osp;
    always @(posedge clk) if (me) begin
        pd <= d; pv <= c_v; pdd <= c_d; pj <= c_j; psp <= c_sp; ov <= o_v; osp <= o_sp;
    end
    reg [NX-1:0] line;
    genvar c, dd;
    generate for (c = 0; c < NX; c = c + 1) begin : g_ent
        wire [ND-1:0] hit, src;
        for (dd = 0; dd < ND; dd = dd + 1) begin : g_d
            localparam integer DV = DSET[dd*8 +: 8];
            localparam integer JJ = (c * DV) / BEAT;
            localparam integer MM = ((c * DV) % BEAT + ((MUT == 1 && c == 5) ? 1 : 0)) % BEAT;
            if (JJ < BMAX) begin : g_ok
                assign hit[dd] = pdd[dd] && (pj == JJ);
                assign src[dd] = pd[MM];
            end else begin : g_no
                assign hit[dd] = 1'b0;
                assign src[dd] = 1'b0;
            end
        end
        reg pick;
        integer kk;
        always @(*) begin
            pick = 1'b0;
            for (kk = 0; kk < ND; kk = kk + 1) if (hit[kk]) pick = src[kk];
        end
        always @(posedge clk) if (me && pv && (|hit) && (c < (1 << psp) || MUT == 2)) line[c] <= pick;
    end endgenerate
    wire [4:0] osw = {1'b0, osp} + ((MUT == 3) ? 5'd1 : 5'd0);
    integer i;
    always @(posedge clk) if (me && ov) begin
        for (i = 0; i < NX; i = i + 1) q[i] <= line[i & ((1 << osw) - 1)];
    end
endmodule

module ot_qfd_vm_xqface_t #(
    parameter integer W = 1024,
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
