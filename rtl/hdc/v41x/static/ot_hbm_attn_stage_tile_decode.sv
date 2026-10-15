`timescale 1ns/1ps
`default_nettype none
// Localconsumer of actual mode34 codebank TILE. K uses all32dimensions of one
// lane; V uses16dimensions for bothlanes, withFP4 scaleinsideeach128bhalf.
module ot_hbm_attn_stage_tile_decode #(parameter integer TILE=0,MUT=0)(
 input wire[255:0]codes,input wire[8:0]qk_metadata,
 input wire[17:0]pv_metadata,input wire qk_pad,
 output wire[575:0]qk_operand,output wire[529:0]pv_groups
);
 genvar x,l;
 generate for(x=0;x<32;x=x+1)begin:g_qk
  assign qk_operand[x*18+:18]=qk_metadata[8]?
   {qk_pad,1'b1,4'b0,codes[x*4+:4],codes[128+8*(x/16)+:8]}:
   {qk_pad,1'b0,codes[x*8+:8],qk_metadata[7:0]};
 end
 for(l=0;l<2;l=l+1)begin:g_pv
  localparam integer ODD=TILE%2;
  wire[127:0]half=codes[l*128+:128];wire[8:0]m=pv_metadata[l*9+:9];
  wire[255:0]packed_fp4=(256'(half[63:0]) << (ODD*64))|
    (256'(half[(MUT==1?72:64)+:8]) << (128+ODD*8));
  wire[255:0]packed_fp8=256'(half) << (ODD*128);
  assign pv_groups[l*265+:265]={m,m[8]?packed_fp4:packed_fp8};
 end endgenerate
endmodule
`default_nettype wire
