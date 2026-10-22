`timescale 1ns/1ps
// One real clock owner for one 9x256 Engram row payload buffer (static lookup, 2026-10-16).
// write_en is one-hot per atom, a core-root POSEDGE register of the lookup (st8; st6/st7 used a negedge copy, a
// half-cycle crossing); we_q/wd_q capture it on this root's posedge (full-cycle flop-to-flop root crossing) and write one cycle later, so the per-atom
// enable fanout (256 per atom) is a full cycle local to this root.
module ot_s81_engram_rowbank_static_leaf #(parameter integer ATOMS=9)(
 input wire ck, input wire [ATOMS-1:0] write_en,
 input wire [255:0] write_data, output wire [256*ATOMS-1:0] rows);
 reg [255:0] payload [0:ATOMS-1];
 reg [ATOMS-1:0] we_q;
 reg [255:0] wd_q;
 always @(posedge ck) begin we_q <= write_en; wd_q <= write_data; end
 genvar atom;
 generate for(atom=0;atom<ATOMS;atom=atom+1) begin:g_rows
  always @(posedge ck) if(we_q[atom]) payload[atom] <= wd_q;
  assign rows[256*atom+:256]=payload[atom];
 end endgenerate
endmodule
