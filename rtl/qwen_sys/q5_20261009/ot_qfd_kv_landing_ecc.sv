`timescale 1ns/1ps
// Native HBM return correction BEFORE crossing into the core-domain landing
// FIFO. One prepaid controller credit remains occupied until real retirement.
// A UE quarantines that credit; it cannot be recycled as successful delivery.
// Cold reset requires the parent's positive all-copy/PHY drain fence.
module ot_qfd_kv_landing_ecc #(parameter integer ENABLE=0, MUT=0, INTERLEAVED=1)(
 input wire hclk,h_rst_n,
 input wire i_v,input wire [287:0] i_code,
 input wire [16:0] i_sec,input wire [7:0] i_row,
 output wire o_v,output wire [255:0] o_data,
 output reg [16:0] o_sec,output reg [7:0] o_row,
 output wire ce,ue,output wire fault,output wire [31:0] ce_count
);
 import ot_gpu_w6_secded_pkg::*;
 reg dv,dc,du,sticky;
 reg [255:0] corrected;
 reg [31:0] count;
 reg [255:0] decoded;
 reg any_ce,any_ue;
 function automatic [71:0] unpack(input [71:0] s);
  integer p,j,k;begin j=0;k=0;unpack=0;
   for(p=1;p<=71;p=p+1)
    if((p&(p-1))!=0)begin unpack[p-1]=s[j];j=j+1;end
    else begin unpack[p-1]=s[64+k];k=k+1;end
   unpack[71]=s[71];
  end
 endfunction
 // ECC storage layout is {32 check bits,256 data bits}; no assumed free PHY
 // sideband. The parent must bind real check storage and every check pin.
 integer w;
 always @* begin
  decoded=0;any_ce=0;any_ue=0;
  for(w=0;w<4;w=w+1)begin : decode_word
   reg [65:0] d;reg [71:0] code;
   code=(INTERLEAVED!=0)?i_code[w*72+:72]:unpack({i_code[256+w*8+:8],i_code[w*64+:64]});
   d=decode64(code);
   decoded[w*64+:64]=(MUT!=0)?unpack_data(code):d[63:0];
   any_ce=any_ce|d[64];any_ue=any_ue|d[65];
  end
 end
 function automatic [63:0] unpack_data(input [71:0] code);
  integer p,j;begin j=0;unpack_data=0;
   for(p=1;p<=71;p=p+1)if((p&(p-1))!=0)begin unpack_data[j]=code[p-1];j=j+1;end
  end
 endfunction
 always @(posedge hclk or negedge h_rst_n)
  if(!h_rst_n)begin dv<=0;dc<=0;du<=0;sticky<=0;count<=0;end
  else begin
   dv<=(ENABLE!=0)&&i_v;dc<=(ENABLE!=0)&&i_v&&any_ce;du<=(ENABLE!=0)&&i_v&&any_ue;
   if((ENABLE!=0)&&i_v&&any_ue)sticky<=1;
   if((ENABLE!=0)&&i_v&&any_ce&&!any_ue)count<=count+1'b1;
  end
 always @(posedge hclk)if(i_v)corrected<=decoded;
 assign ce_count=count;
 always @(posedge hclk) if(i_v) begin o_sec<=i_sec;o_row<=i_row;end
 assign fault=(ENABLE!=0)&&sticky;
 assign ce=(ENABLE!=0)&&dc;
 assign ue=(ENABLE!=0)&&du;
 assign o_v=(ENABLE!=0)&&dv&&!du&&!sticky;
 assign o_data=corrected;
endmodule
