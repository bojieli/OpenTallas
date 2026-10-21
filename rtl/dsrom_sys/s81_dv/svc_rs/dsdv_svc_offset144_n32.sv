`timescale 1ns/1ps
// Constant-source byte muxes; codes are copies from the existing pin-register edge.
module dsdv_svc_offset144_n32(input wire[71:0]codes,input wire[511:0]banks,output wire[143:0]word_out);
 for(genvar b=0;b<18;b=b+1)begin:g_byte
  wire[15:0]onehot;
  for(genvar c=0;c<16;c=c+1)begin:g_code
   assign onehot[c]=codes[4*b+:4]==4'(c);
  end
  reg[7:0]v;
  always@*begin
   v=0;
   for(integer c=0;c<16;c=c+1)v=v|({8{onehot[c]}}&banks[8*b+((144*c)%256)+:8]);
  end
  assign word_out[8*b+:8]=v;
 end
endmodule
