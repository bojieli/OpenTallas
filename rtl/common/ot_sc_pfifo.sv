`timescale 1ns/1ps
// ot_sc_pfifo: pin-safe valid/ready FIFO (stream struct-close, 2026-10-09; templates C + D).
//
// Drop-in for a 2-entry valid/ready skid at a die-block pin whose wide data path failed because a pin-arriving
// handshake bit (in_valid or out_ready, ~518 ps of the cycle spent outside under the die-link budget) or one read
// pointer fanned out to every data bit (fence_p: host_wr_ready -> 4,105 output-register enables; drf_fan:
// f_civ -> 1,026 storage enables, r -> 513 output-mux selects).
//
// Construction (all exact, 0 added cycles vs a 2-entry skid with registered in_ready):
//  * in_valid and out_ready touch ONLY the count / pointer state and the registered per-group copies below
//    (G-bit groups: ceil(W/G)*S + ~6 flops), never a data-bit enable.
//  * Storage slot i of group g loads in_data every cycle while it is the free write slot (we[g][i], a flop:
//    write pointer == i and not full).  A beat is committed by advancing the write pointer on in_valid & in_ready;
//    an uncommitted write lands only in a free slot, so it is never observed.
//  * out_data of group g = OR_i (rs[g][i] & slot i): one AND-OR level from flops (rs[g][i] a flop copy of the
//    one-hot read pointer, fanout G).
//  * in_ready and out_valid are flops.
// Copies are ot_sc_rep_ff instances (keep_hierarchy) so synthesis (opt_merge) cannot merge them back into one
// high-fanout net; checked with the ORFS yosys 0.68 (plain (* keep *) regs were merged: 22 -> 9 control flops).
// MUT 1 (bench mutant): the write slot is not protected when full (a full FIFO overwrites its tail).
module ot_sc_pfifo #(
    parameter integer W = 32,
    parameter integer S = 2,       // entries (>= 2)
    parameter integer G = 32,      // data bits per pointer copy
    parameter integer MUT = 0,
    // PINREG=1 (sys-takeover 2026-10-10, opt-in): in_valid / in_data are captured by a bare pin flop first and pushed one
    // edge later (no handshake logic between the pin and a flop: collvmpub rsp_valid pin -> we copies 11 levels); in_ready
    // reserves room for that in-flight word (ready while count + in-flight < S; use S >= 3 for full rate).
    parameter integer PINREG = 0
) (
    input  wire         clk,
    input  wire         rst_n,     // synchronous, active low
    input  wire         in_valid,
    output reg          in_ready,
    input  wire [W-1:0] in_data,
    output reg          out_valid,
    input  wire         out_ready,
    output wire [W-1:0] out_data
);
    localparam integer NG = (W + G - 1) / G;
    localparam integer SB = (S <= 2) ? 1 : $clog2(S);
    localparam integer CB = $clog2(S + 1);
    reg [CB-1:0] n;
    reg [SB-1:0] w, r;
    reg          pv; reg [W-1:0] pd;
    always @(posedge clk) begin
        if (!rst_n) pv <= 1'b0; else pv <= in_valid && in_ready;
        pd <= in_data;
    end
    wire push = PINREG ? pv : (in_valid && in_ready);
    wire [W-1:0] wdat = PINREG ? pd : in_data;
    wire pop  = out_valid && out_ready;
    wire [CB-1:0] n_nx = n + {{(CB-1){1'b0}}, push} - {{(CB-1){1'b0}}, pop};
    wire [SB-1:0] w_nx = push ? ((w == S - 1) ? {SB{1'b0}} : w + 1'b1) : w;
    wire [SB-1:0] r_nx = pop  ? ((r == S - 1) ? {SB{1'b0}} : r + 1'b1) : r;
    wire full_nx = (n_nx == S);
    always @(posedge clk) begin
        if (!rst_n) begin n <= 0; w <= 0; r <= 0; in_ready <= 1'b1; out_valid <= 1'b0; end   // empty after reset: ready at once
        else begin
            n <= n_nx; w <= w_nx; r <= r_nx;
            in_ready <= PINREG ? (({1'b0, n_nx} + {{CB{1'b0}}, in_valid && in_ready}) < S) : !full_nx;
            out_valid <= (n_nx != 0);
        end
    end
    // late select (struct-close r2, fence_p2 TT -85 on host_wr_ready -> pop -> next-pointer arithmetic -> copies): the
    // next value of every copy is precomputed from flops for the four {push, pop} cases; the pin handshake only selects
    // (one 4:1 mux level after the AND with the registered in_ready / out_valid).
    wire [S-1:0] we_t [0:3];
    wire [S-1:0] rs_t [0:3];
    genvar c4;
    generate for (c4 = 0; c4 < 4; c4 = c4 + 1) begin : g_c4
        wire pu = c4[1], po = c4[0];
        wire [CB-1:0] n_c = n + {{(CB-1){1'b0}}, pu} - {{(CB-1){1'b0}}, po};
        wire [SB-1:0] w_c = pu ? ((w == S - 1) ? {SB{1'b0}} : w + 1'b1) : w;
        wire [SB-1:0] r_c = po ? ((r == S - 1) ? {SB{1'b0}} : r + 1'b1) : r;
        genvar j;
        for (j = 0; j < S; j = j + 1) begin : g_j
            assign we_t[c4][j] = (w_c == j) && (MUT == 1 ? 1'b1 : (n_c != S));
            assign rs_t[c4][j] = (r_c == j);
        end
    end endgenerate
    genvar g, i;
    generate for (g = 0; g < NG; g = g + 1) begin : g_g
        localparam integer LO = g * G;
        localparam integer GW = (W - LO < G) ? (W - LO) : G;
        wire [S-1:0] we, rs;
        reg [GW-1:0] m [0:S-1];
        wire [GW-1:0] sel [0:S];
        assign sel[0] = {GW{1'b0}};
        for (i = 0; i < S; i = i + 1) begin : g_s
            ot_sc_rep_ff #(.RV(i == 0)) u_we (.clk(clk), .rst_n(rst_n), .d(we_t[{push, pop}][i]), .q(we[i]));
            ot_sc_rep_ff #(.RV(i == 0)) u_rs (.clk(clk), .rst_n(rst_n), .d(rs_t[{push, pop}][i]), .q(rs[i]));
            always @(posedge clk) if (we[i]) m[i] <= wdat[LO +: GW];
            assign sel[i+1] = sel[i] | ({GW{rs[i]}} & m[i]);
        end
        assign out_data[LO +: GW] = sel[S];
    end endgenerate
endmodule

// One replicated control flop; keep_hierarchy stops opt_merge from folding identical copies together.
(* keep_hierarchy *)
module ot_sc_rep_ff #(parameter RV = 1'b0) (input wire clk, input wire rst_n, input wire d, output reg q);
    always @(posedge clk) if (!rst_n) q <= RV; else q <= d;
endmodule
