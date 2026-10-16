`timescale 1ns/1ps
`default_nettype none
// Structural successor to the congested field16 pilot. Four independent hard leaves preserve every bit and edge.
module s81_a2f_field4(
 input wire ck,rst_n,input wire [211:0] i_data,input wire [671:0] i_sel,
 input wire [31:0] i_drain_v,input wire [63:0] i_drain_slot,
 output wire [31:0] o_v,output wire [127:0] o_data,output wire [3:0] fault
);
 s81_a2f_field #(.NSRC(53),.W(4)) u_impl(ck,rst_n,i_data,i_sel,i_drain_v,i_drain_slot,o_v,o_data,fault);
endmodule
// Wires-only compound. Each child has a real independent clock/reset entry. The die delivers phi-R per child.
module s81_a2f_field16_split4(
 input wire [3:0] ck,rst_n,input wire [847:0] i_data,input wire [671:0] i_sel,
 input wire [31:0] i_drain_v,input wire [63:0] i_drain_slot,
 output wire [31:0] o_v,output wire [511:0] o_data,output wire [3:0] fault
);
 wire [127:0] vv;wire [15:0] ff;
 genvar k,s,b;
 generate for(k=0;k<4;k=k+1)begin:bitslice
  wire [211:0] di;wire [127:0] dout;
  for(s=0;s<53;s=s+1)begin:src assign di[4*s+:4]=i_data[16*s+4*k+:4];end
  s81_a2f_field4 u_leaf(ck[k],rst_n[k],di,i_sel,i_drain_v,i_drain_slot,vv[32*k+:32],dout,ff[4*k+:4]);
  for(b=0;b<32;b=b+1)begin:bank assign o_data[16*b+4*k+:4]=dout[4*b+:4];end
 end endgenerate
 // Valid/fault logic depends only on shared selectors and drain state, hence all four copies agree.
 // Use one copy; no new logic or cycle is added to the parent.
 assign o_v=vv[31:0];assign fault=ff[3:0];
endmodule
`default_nettype wire
