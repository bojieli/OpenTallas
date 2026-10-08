`timescale 1ns/1ps
// One-PC request/completion owner. ROLE=0 core-service, ROLE=1 strip ledger.
// Cold reset only; epoch_fence is an explicit externally coordinated discard
// of canceled ownership after both transports and the real ledger have drained.
// CRC does not harden the mutable state or native hub credit engine.
module ot_qwen_kvc_write_link_bridge #(
 parameter integer ENABLE=0, ROLE=0,
 parameter [6:0] PC=0,
 parameter [1:0] DEST=0, EXPECT_SOURCE=0,
 parameter [7:0] BOOT_EPOCH=0
)(
 input wire rst_n,local_clk,hub_clk,hub_fault,
 input wire stop, epoch_fence,global_quiescent,
 input wire [7:0] next_epoch,
 input wire w_v, input wire [23:0] w_sec,input wire [255:0] w_data,input wire [8:0] w_tag,
 output wire w_room,output reg wd_v,output reg [8:0] wd_tag,
 output reg ledger_w_v,output reg [23:0] ledger_w_sec,output reg [255:0] ledger_w_data,output reg [8:0] ledger_w_tag,
 input wire ledger_w_room,ledger_wd_v,input wire [8:0] ledger_wd_tag,
 output wire [3:0] outstanding, output reg [3:0] canceled_at_fence,
 output wire upstream_quiescent,output wire transport_quiet,output reg fault,
 output wire x3_v,output wire [511:0] x3_d,output wire [10:0] x3_tag,input wire x3_cr,
 input wire ar_v,input wire [511:0] ar_d,input wire [10:0] ar_tag,input wire [1:0] ar_source,output wire ar_cr
);
 reg [7:0] epoch;
 reg [15:0] next_seq;
 reg exhausted;
 reg [7:0] live,handed;
 reg [15:0] seqs[0:7];reg [8:0] tags[0:7];
 reg room1,room2;
 integer k,free_slot,match_slot,tag_slot,count;
 always @* begin
  free_slot=-1;match_slot=-1;tag_slot=-1;count=0;
  for(integer j=0;j<8;j=j+1)begin
   if(live[j])begin
    count=count+1;
    if(ROLE==0 && seqs[j]==dec_seq && tags[j]==dec_tag)match_slot=j;
    if(ROLE==1 && tags[j]==ledger_wd_tag && handed[j])match_slot=j;
    if(tags[j]==(ROLE==0?w_tag:dec_tag))tag_slot=j;
   end else if(free_slot==-1)free_slot=j;
  end
 end
 assign outstanding=count;
 assign w_room=ENABLE && ROLE==0 && !stop && !fault && !exhausted && count<=5;
 wire shim_fault,shim_quiet,tx_ready,rx_v;
 wire [509:0] rx_packet,enc_packet;
 wire [10:0] rx_tag;
 wire [1:0] rx_source;
 wire enc_v,enc_bad,dec_v,dec_bad;
 wire [3:0] dec_op;wire [7:0] dec_epoch;wire [6:0] dec_pc;wire [15:0] dec_seq;
 wire [8:0] dec_tag;wire [23:0] dec_sec;wire [255:0] dec_data;
 reg [10:0] identity_tag;reg [1:0] identity_source;
 wire rx_take=ENABLE && !fault && (ROLE==0 || stop || ledger_w_room); // abort drains requests into retained canceled ownership
 wire source_accept=ENABLE && ROLE==0 && w_v && (room1||room2) && free_slot>=0 && tag_slot<0 && !fault && !shim_fault && !dec_bad && !enc_bad && !exhausted;
 wire done_accept=ENABLE && ROLE==1 && ledger_wd_v && match_slot>=0 && !fault && !shim_fault && !dec_bad && !enc_bad;
 wire enc_i_v=source_accept||done_accept;
 wire [15:0] enc_seq=ROLE==0?next_seq:(match_slot>=0?seqs[match_slot]:16'd0);
 ot_qwen_kvc_packet_encode_parallel #(.ENABLE(ENABLE)) enc(
  .clk(local_clk),.rst_n(rst_n),.i_v(enc_i_v),.i_op(ROLE==0?4'd1:4'd2),.i_epoch(epoch),.i_pc(PC),
  .i_seq(enc_seq),.i_tag(ROLE==0?w_tag:ledger_wd_tag),.i_sec(ROLE==0?w_sec:24'd0),.i_data(ROLE==0?w_data:256'd0),
  .o_v(enc_v),.o_bad(enc_bad),.o_packet(enc_packet));
 ot_qwen_kvc_packet_decode_parallel #(.ENABLE(ENABLE)) dec(
  .clk(local_clk),.rst_n(rst_n),.i_v(rx_v&&rx_take),.i_packet(rx_packet),
  .o_v(dec_v),.o_bad(dec_bad),.o_packet(),.o_op(dec_op),.o_epoch(dec_epoch),.o_pc(dec_pc),
  .o_seq(dec_seq),.o_tag(dec_tag),.o_sec(dec_sec),.o_data(dec_data));
 ot_qwen_kvc_hub_cdc #(.ENABLE(ENABLE),.DEST(DEST)) transport(
  .rst_n(rst_n),.local_clk(local_clk),.hub_clk(hub_clk),.native_hub_fault(hub_fault),.tx_v(enc_v),.tx_packet(enc_packet),.tx_ready(tx_ready),
  .rx_v(rx_v),.rx_packet(rx_packet),.rx_tag(rx_tag),.rx_source(rx_source),.rx_take(rx_take),
  .local_quiet(shim_quiet),.fault(shim_fault),.x3_v(x3_v),.x3_d(x3_d),.x3_tag(x3_tag),.x3_cr(x3_cr),
  .ar_v(ar_v),.ar_d(ar_d),.ar_tag(ar_tag),.ar_source(ar_source),.ar_cr(ar_cr));
 assign transport_quiet=shim_quiet&&!enc_v&&!dec_v&&!dec_bad&&!ledger_w_v&&!w_v&&!ledger_wd_v&&(ROLE==1||(!room1&&!room2));
 assign upstream_quiescent=stop&&transport_quiet;
 wire identity_ok=dec_epoch==epoch && dec_pc==PC && identity_tag==dec_seq[10:0] && identity_source==EXPECT_SOURCE;
 always @(posedge local_clk or negedge rst_n) begin
  if(!rst_n)begin
   epoch<=BOOT_EPOCH;next_seq<=0;exhausted<=0;live<=0;handed<=0;room1<=0;room2<=0;
   wd_v<=0;wd_tag<=0;ledger_w_v<=0;ledger_w_sec<=0;ledger_w_data<=0;ledger_w_tag<=0;
   fault<=0;canceled_at_fence<=0;identity_tag<=0;identity_source<=0;
   for(k=0;k<8;k=k+1)begin seqs[k]<=0;tags[k]<=0;end
  end else begin
   room1<=w_room;room2<=room1;wd_v<=0;ledger_w_v<=0;
   if(rx_v&&rx_take)begin identity_tag<=rx_tag;identity_source<=rx_source;end
   if(ENABLE)begin
    if(shim_fault||enc_bad||dec_bad||(enc_v&&!tx_ready))fault<=1;
    if(ROLE==0)begin
     if(w_v&&!source_accept)fault<=1;
     if(source_accept)begin
      live[free_slot]<=1;handed[free_slot]<=1;tags[free_slot]<=w_tag;seqs[free_slot]<=next_seq;
      if(next_seq==16'hffff)exhausted<=1;else next_seq<=next_seq+1'b1;
     end
     if(dec_v&&!fault&&!shim_fault&&!enc_bad)begin
      if(!identity_ok||dec_op!=2||match_slot<0)fault<=1;
      else begin live[match_slot]<=0;handed[match_slot]<=0;wd_v<=1;wd_tag<=dec_tag;end
     end
    end else begin
     if(ledger_wd_v&&!done_accept)fault<=1;
     if(done_accept)begin live[match_slot]<=0;handed[match_slot]<=0;end
     if(dec_v&&!fault&&!shim_fault&&!enc_bad)begin
      if(!identity_ok||dec_op!=1||dec_seq!=next_seq||exhausted||free_slot<0||tag_slot>=0)fault<=1;
      else begin
       live[free_slot]<=1;tags[free_slot]<=dec_tag;seqs[free_slot]<=dec_seq;
       if(next_seq==16'hffff)exhausted<=1;else next_seq<=next_seq+1'b1;
       if(!stop)begin
        begin ledger_w_v<=1;ledger_w_sec<=dec_sec;ledger_w_data<=dec_data;ledger_w_tag<=dec_tag;handed[free_slot]<=1;end
       end else handed[free_slot]<=0;
      end
     end
    end
    if(epoch_fence)begin
     if(!stop||!global_quiescent||!transport_quiet||fault||shim_fault||next_epoch==epoch)fault<=1;
     else begin canceled_at_fence<=count;live<=0;handed<=0;epoch<=next_epoch;next_seq<=0;exhausted<=0;room1<=0;room2<=0;end
    end
   end
  end
 end
endmodule
