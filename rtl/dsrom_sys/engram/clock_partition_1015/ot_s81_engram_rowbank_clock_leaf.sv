`timescale 1ns/1ps
// One real clock owner for one unchanged 9x256 row payload buffer.
module ot_s81_engram_rowbank_clock_leaf #(parameter integer ATOMS=9)(
 input wire ck, input wire write_v, input wire [3:0] write_idx,
 input wire [255:0] write_data, output wire [256*ATOMS-1:0] rows);
 reg [255:0] payload [0:ATOMS-1];
 always @(posedge ck) if(write_v) payload[write_idx] <= write_data;
 genvar atom;
 generate for(atom=0;atom<ATOMS;atom=atom+1) begin:g_rows
  assign rows[256*atom+:256]=payload[atom];
 end endgenerate
endmodule
