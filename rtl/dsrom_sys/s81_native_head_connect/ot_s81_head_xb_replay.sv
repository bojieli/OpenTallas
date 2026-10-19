`timescale 1ns/1ps
// Existing rstop selected gather port ABI: BF16 family, global beat5*sid+k,
// 64 BF16 lanes at g_d[16*lane+:16]. No arithmetic or fixture stream.
// The actual compiler must reserve one upstream gather source and guarantee
// token/epoch lifetime: this untagged XB ABI cannot detect a stale same-index
// packet from another token. This wrapper does not invent an epoch guarantee.
module ot_s81_head_xb_replay (
 input wire clk,rst_n,load_begin,g_v,g_fam,go,
 input wire [46:0] owner,input wire [63:0] sequence_id,
 input wire [6:0] g_idx,input wire [1023:0] g_d,
 output wire[255:0]xa,xb,output wire active,output wire fault
);
 wire[2047:0]expanded;
 for(genvar j=0;j<64;j=j+1)begin:unpack
  assign expanded[32*j+:32]={g_d[16*j+:16],16'b0};
 end
 reg family_fault;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)family_fault<=0;else if(g_v&&!g_fam)family_fault<=1;
 wire f;
 ot_s81_head_input_replay u_replay(.clk(clk),.rst_n(rst_n),.load_begin(load_begin),.load_v(g_v),.go(go),
  .owner(owner),.sequence_id(sequence_id),.load_i(g_idx),.load_d(expanded),.xa(xa),.xb(xb),.active(active),.fault(f));
 assign fault=f|family_fault;
endmodule
