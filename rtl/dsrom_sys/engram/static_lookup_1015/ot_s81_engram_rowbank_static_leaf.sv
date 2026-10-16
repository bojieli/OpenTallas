`timescale 1ns/1ps
// One real clock owner for one 9x256 Engram row payload buffer (static lookup, 2026-10-16).
// write_en is one-hot per atom, registered in the core root by the lookup (flop-to-flop root crossing);
// the per-atom enable fanout is local to this root.
module ot_s81_engram_rowbank_static_leaf #(parameter integer ATOMS=9)(
 input wire ck, input wire [ATOMS-1:0] write_en,
 input wire [255:0] write_data, output wire [256*ATOMS-1:0] rows);
 reg [255:0] payload [0:ATOMS-1];
 genvar atom;
 generate for(atom=0;atom<ATOMS;atom=atom+1) begin:g_rows
  always @(posedge ck) if(write_en[atom]) payload[atom] <= write_data;
  assign rows[256*atom+:256]=payload[atom];
 end endgenerate
endmodule
