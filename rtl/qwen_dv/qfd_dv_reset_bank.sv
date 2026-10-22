`timescale 1ns/1ps
// Registered data bank with <=32 async reset loads per kept leaf.
// The existing synchronized reset feeds two extra release stages; data is
// sampled each edge, preserving the comparator pipeline's steady latency.
module qfd_dv_reset_bank #(parameter integer W=32)(
 input wire ck,rst_n,input wire[W-1:0] d,output wire[W-1:0] q
);
 localparam integer N=(W+31)/32;
 wire[N-1:0] leaf;
 qfd_dv_reset_tree #(.N(N)) u_rt(.ck(ck),.rst_n(rst_n),.q(leaf));
 genvar i;
 generate for(i=0;i<N;i=i+1) begin:g_b
  localparam integer B=((W-32*i)<32)?(W-32*i):32;
  reg[B-1:0] data;
  always @(posedge ck or negedge leaf[i])
   if(!leaf[i]) data<=0;
   else data<=d[32*i+:B];
  assign q[32*i+:B]=data;
 end endgenerate
endmodule
