`timescale 1ns/1ps
`default_nettype none
// Kept low-nibble copies capture the same input edge as the existing quarter
// index register. Each copy selects at most sixteen bitmap bits. No new age.
module ot_hidx_keep171_f32(input wire clk,input wire[170:0]kb_registered,
 input wire[7:0]index_registered,input wire[3:0]index_next,output wire q);
 wire[10:0]part;
 for(genvar g=0;g<11;g=g+1)begin:g_group
  (*keep="true",dont_touch="true"*)reg[3:0]lo;
  always@(posedge clk)lo<=index_next;
  wire[15:0]bits;
  for(genvar b=0;b<16;b=b+1)begin:g_bit
   if(16*g+b<171)assign bits[b]=kb_registered[16*g+b];else assign bits[b]=1'bx;
  end
  assign part[g]=(index_registered[7:4]==4'(g)) && bits[lo];
 end
 assign q=(index_registered<=8'd170)?|part:1'bx;
endmodule
`default_nettype wire
