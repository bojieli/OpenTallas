`timescale 1ns/1ps
`default_nettype none
// D opt-in profile. Each tile owns64 actual macros and its capture data stays
// inside that tile. Four explicit bank clocks must be synchronous/phase matched
// with clk. Physical CTS/skew/buffering remain qualification obligations.
module ot_hbm_attn_pv_serializer_local_tile(
 input wire clk,capture_v,capture_epoch,input wire[3:0]capture_dim,
 input wire[511:0]capture_data,input wire[15:0]capture_flags,
 input wire drain_v,drain_epoch,input wire[3:0]drain_head,
 output wire[511:0]drain_data,output wire[15:0]drain_flags
);
 wire[127:0]q[0:63];wire[3:0]fq[0:63];reg[1:0]hg_q,hl_q;
 always @(posedge clk)if(drain_v)begin hg_q<=drain_head[3:2];hl_q<=drain_head[1:0];end
 genvar b,e,d;
 generate for(b=0;b<64;b=b+1)begin:g_bank
  localparam integer C=b/4,G=b%4;
  wire we=capture_v&&capture_dim==4'(C);
  wire re=drain_v&&drain_head[3:2]==2'(G);
  ot_sram_1r1w_32x128_m1 u_data(.clk(clk),.r_ce_in(re),.r_addr_in({4'd0,drain_epoch}),.rd_out(q[b]),
   .w_ce_in(we),.w_addr_in({4'd0,capture_epoch}),.wd_in(capture_data[G*128+:128]),.w_mask_in({128{1'b1}}));
  wire[7:0]flags_by_epoch;
  for(e=0;e<2;e=e+1)begin:g_flags
   reg[3:0]f;always @(posedge clk)if(we&&capture_epoch==1'(e))f<=capture_flags[G*4+:4];
   assign flags_by_epoch[e*4+:4]=f;
  end
  reg[3:0]fr;always @(posedge clk)if(re)fr<=flags_by_epoch[drain_epoch*4+:4];
  assign fq[b]=fr;
 end
 for(d=0;d<16;d=d+1)begin:g_word
  assign drain_data[d*32+:32]=q[d*4+int'(hg_q)][hl_q*32+:32];
  assign drain_flags[d]=fq[d*4+int'(hg_q)][hl_q];
 end endgenerate
endmodule
module ot_hbm_attn_pv_serializer_local(
 input wire clk,rst_n,input wire[3:0]bank_clk,
 input wire capture_v,capture_epoch,input wire[3:0]capture_dim,
 input wire[16383:0]capture_data,input wire[511:0]capture_flags,
 input wire drain_v,drain_epoch,input wire[3:0]drain_head,
 input wire[2:0]drain_block,input wire[15:0]drain_base_sector,
 output reg write_v,output wire[2047:0]write_data,
 output wire[63:0]write_flags,output reg[15:0]write_base_sector,
 output reg fault
);
 wire[511:0]td[0:31];wire[15:0]tf[0:31];reg[2:0]block_q;
 reg[15:0]seen[0:1];genvar t,d;
 generate for(t=0;t<32;t=t+1)begin:g_tile
  ot_hbm_attn_pv_serializer_local_tile u_store(.clk(bank_clk[t%4]),
   .capture_v(capture_v),.capture_epoch(capture_epoch),.capture_dim(capture_dim),
   .capture_data(capture_data[t*512+:512]),.capture_flags(capture_flags[t*16+:16]),
   .drain_v(drain_v&&drain_block==3'(t/4)),.drain_epoch(drain_epoch),.drain_head(drain_head),
   .drain_data(td[t]),.drain_flags(tf[t]));
 end
 for(d=0;d<4;d=d+1)begin:g_out
  assign write_data[d*512+:512]=td[int'(block_q)*4+d];
  assign write_flags[d*16+:16]=tf[int'(block_q)*4+d];
 end endgenerate
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  seen[0]<=0;seen[1]<=0;write_v<=0;write_base_sector<=0;block_q<=0;fault<=0;
 end else begin
  write_v<=drain_v;
  if(capture_v)begin
   if(capture_dim==0)seen[capture_epoch]<=16'h0001;
   else begin
    if(seen[capture_epoch][capture_dim]||!seen[capture_epoch][capture_dim-1])fault<=1;
    seen[capture_epoch][capture_dim]<=1;
   end
  end
  if(drain_v)begin
   block_q<=drain_block;
   write_base_sector<=drain_base_sector+16'(int'(drain_head)*64+int'(drain_block)*8);
   if(seen[drain_epoch]!=16'hffff||drain_base_sector[2:0]!=0||
     (capture_v&&capture_epoch==drain_epoch))fault<=1;
  end
 end
endmodule
`default_nettype wire
