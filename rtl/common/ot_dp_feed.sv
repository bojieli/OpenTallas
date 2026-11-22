`timescale 1ns/1ps
`default_nettype none
// ot_dp_feed: plain feed-through leaf of a partition piece (type_split, gen-mode types).  A bus whose leaf sits in another
// piece crosses this piece from its face register to the cut-face register (or back): the piece needs a leaf that binds
// both buses.  No logic, no register: the two face registers of the piece are the only flops on the path.
module ot_dp_feed #(parameter integer W = 1) (input wire [W-1:0] d, output wire [W-1:0] q);
    assign q = d;
endmodule
`default_nettype wire
