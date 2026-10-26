`timescale 1ns/1ps
`default_nettype none
// Six-cycle request-to-bank-capture pipeline: five serializer edges then the
// actual bank capture edge. Retirement waits its real additional three edges.
module ot_hbm_attn_pv_native_output_quad_local #(
 parameter integer ACTIVE_HEADS=16
)(
 input wire clk,rst_n,input wire[127:0]quad_clk,
 input wire[31:0]select_clk,input wire[7:0]gather_clk,
 input wire capture_v,capture_epoch,input wire[3:0]capture_dim,
 input wire[16383:0]capture_data,input wire[511:0]capture_flags,
 input wire drain_v,drain_epoch,input wire[3:0]drain_head,
 input wire[2:0]drain_block,input wire[15:0]drain_base_sector,drain_tag,
 output wire[2247:0]wq,output wire record_done,record_fault,
 output wire[15:0]record_tag,output wire fault
);
 localparam integer COMMITS=ACTIVE_HEADS*8;
 localparam integer CW=$clog2(COMMITS);
 wire sv,sf;wire[2047:0]sd;wire[63:0]flags;wire[15:0]sector;
 ot_hbm_attn_pv_serializer_quad_local u_store(.clk(clk),.quad_clk(quad_clk),
  .select_clk(select_clk),.gather_clk(gather_clk),.rst_n(rst_n),
  .capture_v(capture_v),.capture_epoch(capture_epoch),.capture_dim(capture_dim),
  .capture_data(capture_data),.capture_flags(capture_flags),
  .drain_v(drain_v),.drain_epoch(drain_epoch),.drain_head(drain_head),.drain_block(drain_block),
  .drain_base_sector(drain_base_sector),.write_v(sv),.write_data(sd),
  .write_flags(flags),.write_base_sector(sector),.fault(sf));
 genvar b;
 generate for(b=0;b<8;b=b+1)begin:g_wq
  assign wq[b*281+:281]={sv,16'(sector+b),sd[b*256+:256],8'hff};
 end endgenerate
 reg sticky;reg[CW-1:0]count;reg[15:0]base;
 reg[15:0]tag_pipe[0:5];reg[3:0]retire;reg[15:0]tags[0:3];integer j;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  sticky<=0;count<=0;base<=0;retire<=0;
  for(j=0;j<6;j=j+1)tag_pipe[j]<=0;
  for(j=0;j<4;j=j+1)tags[j]<=0;
 end else begin
  retire<={retire[2:0],sv&&count==CW'(COMMITS-1)};
  if(drain_v)tag_pipe[0]<=drain_tag;
  for(j=1;j<6;j=j+1)tag_pipe[j]<=tag_pipe[j-1];
  tags[0]<=tag_pipe[5];for(j=1;j<4;j=j+1)tags[j]<=tags[j-1];
  if(sf||(sv&&|flags)||(drain_v&&int'(drain_head)>=ACTIVE_HEADS))sticky<=1;
  if(sv)begin
   if(count==0)begin
    base<=sector;
    if(sector[2:0]!=0||sector[12:0]>13'(8192-COMMITS*8))sticky<=1;
   end else if(sector!=base+16'(int'(count)*8))sticky<=1;
   count<=count+1'b1;
  end
 end
 assign fault=sticky|sf;
 assign record_done=retire[3]&&!fault;
 assign record_fault=retire[3]&&fault;
 assign record_tag=tags[3];
endmodule
`default_nettype wire
