`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// BUS-GEAR-1 (2026-11-12, COORD ruling (B) + OWNER adoption): S81 x feed 2:1, per forwarded-clock lane.
//
// The x feed is NL = 4 lanes of LW = 276 b (x[276k +: 276] = lane k, the V-rung fragment format), each landed on its
// own forwarded clock xk[k] (dsfd_cfifo_crs4 contract L1).  The gear keeps that structure: every lane is serialised on
// its own and becomes a 139-b beat lane {f, beat[137:0]} (f = first-beat flag), so the x bus is 4 x 139 = 556 b
// instead of 1104 b, with the same 4 clock domains.
//
// TX (slice C, in place of the x_o face register): a word is taken on an edge where v_i is high (the compiler's x
// cadence 2: v_i never rises on two consecutive edges; a violation is a sticky fault, never arbitrated); beat 0 =
// word[137:0] leaves on the next edge, beat 1 = word[275:138] on the one after.  Edges without a word send zero beats.
// Relay stations (ot_s81_rly, frame xo forward chain) carry beats unchanged: the frames FORWARD the 556-b beat lanes
// and land the word through the RX, so x_i / xo_o / ft x slots all halve.
// RX (frame, in front of dsfd_cfifo_crs4 xl<k> on xk[k]): the word appears on the edge its beat 1 arrives (one xk[k]
// edge after beat 0), zero on every other edge.  Because the in-band markers (xl0[0], xl2[14] = the source's released
// reset) are then 0 on non-word edges, the landing reads those slots as bubbles, which is the existing crs4 semantics
// (a word read while its marker is 0 is a bubble).  Latency: +1 xk[k] edge on the lane (word_cycles = cycles + 1) -- a
// landing calendar change (K / E per lane) owned by S81-ARCH-RTL-2 and the plan event (DIE-S81-87).
// MUT (bench only): passed to ot_bus_gear_tx / _rx (1 beat order, 2 n/a, 3 no spacing fault).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_xlane_gear_tx #(
    parameter integer NL = 4,
    parameter integer LW = 276,
    parameter integer MUT = 0,
    localparam integer BL = (LW + 1) / 2 + 1          // beat lane width incl. f (139)
) (
    input  wire clk,
    input  wire rst_n,
    input  wire v_i,                                  // word strobe (x cadence 2)
    input  wire [NL*LW-1:0] x_i,
    output wire [NL*BL-1:0] xb_o,                     // lane k = xb_o[BL*k +: BL] = {f, beat}
    output wire fault_o
);
    wire [NL-1:0] fl;
    genvar k;
    generate for (k = 0; k < NL; k = k + 1) begin : g_l
        ot_bus_gear_tx #(.W(LW), .BEATS(2), .MUT(MUT)) u_tx (.clk(clk), .rst_n(rst_n), .v_i(v_i),
            .d_i(x_i[LW*k +: LW]), .b_o(xb_o[BL*k +: BL-1]), .f_o(xb_o[BL*k+BL-1]), .fault_o(fl[k]));
    end endgenerate
    assign fault_o = |fl;
endmodule

module ot_s81_xlane_gear_rx #(
    parameter integer NL = 4,
    parameter integer LW = 276,
    parameter integer MUT = 0,
    localparam integer BL = (LW + 1) / 2 + 1
) (
    input  wire [NL-1:0] xk,                          // lane k forwarded clock (the lane's last station clock)
    input  wire [NL-1:0] rst_n,                       // lane k reset, synchronous to xk[k]
    input  wire [NL*BL-1:0] xb_i,
    output wire [NL*LW-1:0] x_o,                      // = the unserialised x word layout, zero on non-word edges
    output wire [NL-1:0] v_o
);
    genvar k;
    generate for (k = 0; k < NL; k = k + 1) begin : g_l
        /* verilator lint_off PINCONNECTEMPTY */   // no side-band on the x lanes
        ot_bus_gear_rx #(.W(LW), .BEATS(2), .SW(1), .MUT(MUT)) u_rx (.clk(xk[k]), .rst_n(rst_n[k]),
            .b_i(xb_i[BL*k +: BL-1]), .f_i(xb_i[BL*k+BL-1]), .s_i(1'b0), .v_o(v_o[k]), .d_o(x_o[LW*k +: LW]), .s_o());
        /* verilator lint_on PINCONNECTEMPTY */
    end endgenerate
endmodule
`default_nettype wire
