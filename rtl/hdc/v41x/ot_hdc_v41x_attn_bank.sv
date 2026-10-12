`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// HBM attention die tile (margin version, Claude HBM SU/attn 2026-10-06): the hardened PIPELINE BANK -- W flops,
// q <= d, nothing else.  Two physical tops with the same function and different pin geometry, so a die-tile hop is a
// bank macro -> straight wires -> the next bank macro (bit b of d and q on the same track, 0.192 um apart per bit, the
// die's tile pin pitch), and the tile's clock tree sees one clk pin per bank instead of hundreds of flops:
//   ot_attn_bank_sn544  105.84 x 11.88 um, d on the S edge, q on the N edge (M5)   -- vertical flows
//   ot_attn_bank_ew544  11.88 x 105.84 um, d on the W edge, q on the E edge (M4)   -- horizontal flows
// Power: rails M1/M2, M5 / M6 straps, PG pins M6; routing <= M5, so M6 / M7 above the bank stay the tile's.
// ---------------------------------------------------------------------------
module ot_attn_bank #(parameter integer W = 544) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    always @(posedge clk) q <= d;
endmodule

module ot_attn_bank_sn544 (input wire clk, input wire [543:0] d, output wire [543:0] q);
    ot_attn_bank #(.W(544)) u (.clk(clk), .d(d), .q(q));
endmodule

module ot_attn_bank_ew544 (input wire clk, input wire [543:0] d, output wire [543:0] q);
    ot_attn_bank #(.W(544)) u (.clk(clk), .d(d), .q(q));
endmodule
