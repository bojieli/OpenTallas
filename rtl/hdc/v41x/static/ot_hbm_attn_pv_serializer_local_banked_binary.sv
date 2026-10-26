`timescale 1ns/1ps
`default_nettype none
// D successor with explicit physical group mux leaf boundaries.
module ot_hbm_attn_pv_serializer_local_banked_binary(
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
 reg[15:0]seen[0:1];reg[1:0]valid_pipe;reg[15:0]sector0,sector1;genvar t,d;
 generate for(t=0;t<32;t=t+1)begin:g_tile
  ot_hbm_attn_pv_serializer_local_tile u_store(.clk(bank_clk[t%4]),
   .capture_v(capture_v),.capture_epoch(capture_epoch),.capture_dim(capture_dim),
   .capture_data(capture_data[t*512+:512]),.capture_flags(capture_flags[t*16+:16]),
   .drain_v(drain_v&&drain_block==3'(t/4)),.drain_epoch(drain_epoch),.drain_head(drain_head),
   .drain_data(td[t]),.drain_flags(tf[t]));
 end
 for(d=0;d<8;d=d+1)begin:g_out
  wire[2047:0]group_data;wire[63:0]group_flags;
  for(genvar k=0;k<8;k=k+1)begin:g_input
   assign group_data[k*256+:256]=td[k*4+d/2][(d%2)*256+:256];
   assign group_flags[k*8+:8]=tf[k*4+d/2][(d%2)*8+:8];
  end
  ot_hbm_attn_pv_bank_gather_binary u_mux(.clk(bank_clk[d/2]),.rst_n(rst_n),.capture_v(valid_pipe[0]),.tile_data(group_data),.tile_flags(group_flags),.block_select(block_q),
   .bank_data(write_data[d*256+:256]),.bank_flags(write_flags[d*8+:8]),.output_v());
 end endgenerate
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  seen[0]<=0;seen[1]<=0;write_v<=0;write_base_sector<=0;block_q<=0;fault<=0;valid_pipe<=0;sector0<=0;sector1<=0;
 end else begin
  valid_pipe<={valid_pipe[0],drain_v};write_v<=valid_pipe[1];sector1<=sector0;write_base_sector<=sector1;
  if(capture_v)begin
   if(capture_dim==0)seen[capture_epoch]<=16'h0001;
   else begin
    if(seen[capture_epoch][capture_dim]||!seen[capture_epoch][capture_dim-1])fault<=1;
    seen[capture_epoch][capture_dim]<=1;
   end
  end
  if(drain_v)begin
   block_q<=drain_block;
   sector0<=drain_base_sector+16'(int'(drain_head)*64+int'(drain_block)*8);
   if(seen[drain_epoch]!=16'hffff||drain_base_sector[2:0]!=0||
     (capture_v&&capture_epoch==drain_epoch))fault<=1;
  end
 end
endmodule
`default_nettype wire
