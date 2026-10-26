`timescale 1ns/1ps
// Exact CLOSED SR leaf module bodies; original whole source and replay readset are archived.
module qfd_coll_eslice257(input wire ck, input wire [256:0] d, output reg [256:0] q);
 always @(posedge ck) q <= d;
endmodule

module qfd_coll_eslice113(input wire ck, input wire [112:0] d, output reg [112:0] q);
 always @(posedge ck) q <= d;
endmodule
