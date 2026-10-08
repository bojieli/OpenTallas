`timescale 1ns/1ps
// Ordered in-band epoch fence. No trusted external global-quiescent bit and
// no warm reset of hub credits or CDC queues. Mutable-state protection and
// the native controller's readiness/refresh/read-quarantine binding remain
// separate physical/reliability qualification obligations.
module ot_qwen_kvc_write_link_bridge_fenced #(
 parameter integer ENABLE=0, ROLE=0,
 parameter [6:0] PC=0,
 parameter [1:0] DEST=0, EXPECT_SOURCE=0,
 parameter [7:0] BOOT_EPOCH=0
)(
 input wire rst_n,local_clk,hub_clk,hub_fault,
 input wire stop,fence_req,input wire [7:0] next_epoch,
 input wire ledger_epoch_ready,
 output wire fence_busy,output reg fence_done,output wire [7:0] active_epoch,
 input wire w_v,input wire [23:0] w_sec,input wire [255:0] w_data,input wire [8:0] w_tag,
 output wire w_room,output reg wd_v,output reg [8:0] wd_tag,
 output reg ledger_w_v,output reg [23:0] ledger_w_sec,output reg [255:0] ledger_w_data,output reg [8:0] ledger_w_tag,
 input wire ledger_w_room,ledger_wd_v,input wire [8:0] ledger_wd_tag,
 input wire ledger_cancel_v,input wire [8:0] ledger_cancel_tag,output wire ledger_cancel_take,
 output wire [3:0] outstanding,output reg [3:0] canceled_at_fence,
 output wire upstream_quiescent,transport_quiet,output reg fault,
 output wire x3_v,output wire [511:0] x3_d,output wire [10:0] x3_tag,input wire x3_cr,
 input wire ar_v,input wire [511:0] ar_d,input wire [10:0] ar_tag,input wire [1:0] ar_source,output wire ar_cr
);
 reg [7:0] epoch;
 reg [15:0] next_seq;
 reg exhausted;
 reg [7:0] live,handed;
 reg [15:0] seqs[0:7];reg [8:0] tags[0:7];
 reg room1,room2;
 // State0 idle,1 ordered drain/wait,2 encoded control awaiting queue,3 ACK wait.
 reg [1:0] fstate;
 reg [7:0] target_epoch;
 reg [15:0] boundary_seq;
 reg boundary_exhausted,request_seen;
 wire shim_fault,shim_quiet,tx_ready,rx_v;
 wire [509:0] rx_packet,enc_packet;
 wire [10:0] rx_tag;wire [1:0] rx_source;
 wire enc_v,enc_bad,dec_v,dec_bad;
 wire [3:0] dec_op;wire [7:0] dec_epoch;wire [6:0] dec_pc;wire [15:0] dec_seq;
 wire [8:0] dec_tag;wire [23:0] dec_sec;wire [255:0] dec_data;
 reg [10:0] identity_tag;reg [1:0] identity_source;
 integer k,free_slot,match_slot,tag_slot,cancel_slot,count;
 reg [255:0] cancel_set;
 reg ack_set_good,frame_bad;
 integer ack_hits;
 always @* begin
  free_slot=-1;match_slot=-1;tag_slot=-1;cancel_slot=-1;count=0;cancel_set=0;
  for(integer j=0;j<8;j=j+1)begin
   if(live[j])begin
    count=count+1;
    if(ROLE==0 && seqs[j]==dec_seq && tags[j]==dec_tag)match_slot=j;
    if(ROLE==1 && tags[j]==ledger_wd_tag && handed[j])match_slot=j;
    if(tags[j]==(ROLE==0?w_tag:dec_tag))tag_slot=j;
    if(ROLE==1 && handed[j] && tags[j]==ledger_cancel_tag)cancel_slot=j;
    if(!handed[j])begin cancel_set[j]=1;cancel_set[8+25*j+:25]={seqs[j],tags[j]};end
   end else if(free_slot==-1)free_slot=j;
  end
  // Exact set equality, including duplicate and foreign-entry rejection.
  ack_set_good=1;ack_hits=0;
  for(integer a=0;a<8;a=a+1)begin
   if(dec_data[a])begin
    ack_hits=0;
    for(integer b=0;b<8;b=b+1)
     if(live[b] && dec_data[8+25*a+:25]=={seqs[b],tags[b]})ack_hits=ack_hits+1;
    if(ack_hits!=1)ack_set_good=0;
   end
  end
  for(integer b=0;b<8;b=b+1)begin
   if(live[b])begin
    ack_hits=0;
    for(integer a=0;a<8;a=a+1)
     if(dec_data[a] && dec_data[8+25*a+:25]=={seqs[b],tags[b]})ack_hits=ack_hits+1;
    if(ack_hits!=1)ack_set_good=0;
   end
  end
 end
 assign outstanding=count;
 assign active_epoch=epoch;
 assign fence_busy=ENABLE && fstate!=0;
 // Respect FIFO reset rendezvous before advertising a native reservation.
 assign w_room=ENABLE && ROLE==0 && !stop && !fault && !exhausted && fstate==0 && tx_ready && count<=5;
 wire source_candidate=ENABLE && ROLE==0 && w_v && (room1||room2) && free_slot>=0 && tag_slot<0 && !exhausted;
 wire cancel_collision=ledger_cancel_v&&ledger_wd_v&&ledger_cancel_tag==ledger_wd_tag;
 wire done_candidate=ENABLE && ROLE==1 && ledger_wd_v && match_slot>=0 && !cancel_collision;
 wire cancel_candidate=ENABLE && ROLE==1 && stop && ledger_cancel_v && cancel_slot>=0 && !cancel_collision;
 wire request_event=ROLE==0 && fence_req && !request_seen;
 wire bad_request=request_event && (fstate!=0 || !stop || next_epoch==epoch);
 wire identity_ok=dec_epoch==epoch && dec_pc==PC && identity_tag==dec_seq[10:0] && identity_source==EXPECT_SOURCE;
 always @* begin
  frame_bad=0;
  if(dec_v)begin
   if(!identity_ok)frame_bad=1;
   else if(ROLE==0)begin
    case(dec_op)
     2:if(match_slot<0)frame_bad=1;
     4:if(fstate!=3 || !stop || dec_seq!=boundary_seq || dec_tag!={8'b0,boundary_exhausted} || dec_sec!={16'b0,target_epoch} || !ack_set_good)frame_bad=1;
     default:frame_bad=1;
    endcase
   end else begin
    case(dec_op)
     1:if(fstate!=0 || dec_seq!=next_seq || exhausted || free_slot<0 || tag_slot>=0)frame_bad=1;
     3:if(fstate!=0 || !stop || dec_seq!=next_seq || dec_tag!={8'b0,exhausted} || dec_sec[7:0]==epoch)frame_bad=1;
     default:frame_bad=1;
    endcase
   end
  end
 end
 wire fatal_now=shim_fault||enc_bad||dec_bad||(enc_v&&!tx_ready)||frame_bad||bad_request||
  (fstate!=0&&!stop)||(ROLE==1&&fstate==2&&enc_v&&(!ledger_epoch_ready||handed!=0))||
  (ROLE==0&&w_v&&!source_candidate)||
  (ROLE==1&&ledger_wd_v&&!done_candidate)||(ROLE==1&&ledger_cancel_v&&!cancel_candidate);
 wire safe=ENABLE&&!fault&&!fatal_now;
 wire source_accept=source_candidate&&safe;
 wire done_accept=done_candidate&&safe;
 assign ledger_cancel_take=cancel_candidate&&safe;
 wire send_fence=safe&&ROLE==0&&fstate==1&&!room1&&!room2&&!w_v&&!enc_v&&tx_ready;
 wire send_ack=safe&&ROLE==1&&fstate==1&&ledger_epoch_ready&&handed==0&&
  !ledger_wd_v&&!ledger_cancel_v&&!enc_v&&!dec_v&&!rx_v&&tx_ready;
 wire enc_i_v=source_accept||done_accept||send_fence||send_ack;
 wire [3:0] enc_op=source_accept?4'd1:done_accept?4'd2:send_fence?4'd3:4'd4;
 wire [15:0] enc_seq=source_accept?next_seq:done_accept?(match_slot>=0?seqs[match_slot]:16'd0):send_fence?next_seq:boundary_seq;
 wire [8:0] enc_tag=source_accept?w_tag:done_accept?ledger_wd_tag:{8'b0,(send_fence?exhausted:boundary_exhausted)};
 wire [23:0] enc_sec=source_accept?w_sec:done_accept?24'd0:{16'd0,target_epoch};
 wire [255:0] enc_data=source_accept?w_data:send_ack?cancel_set:256'd0;
 ot_qwen_kvc_packet_encode_fence #(.ENABLE(ENABLE)) enc(
  .clk(local_clk),.rst_n(rst_n),.i_v(enc_i_v),.i_op(enc_op),.i_epoch(epoch),.i_pc(PC),.i_seq(enc_seq),.i_tag(enc_tag),.i_sec(enc_sec),.i_data(enc_data),
  .o_v(enc_v),.o_bad(enc_bad),.o_packet(enc_packet));
 wire rx_take=ENABLE&&!fault&&(ROLE==0||stop||ledger_w_room);
 ot_qwen_kvc_packet_decode_fence #(.ENABLE(ENABLE)) dec(
  .clk(local_clk),.rst_n(rst_n),.i_v(rx_v&&rx_take),.i_packet(rx_packet),
  .o_v(dec_v),.o_bad(dec_bad),.o_packet(),.o_op(dec_op),.o_epoch(dec_epoch),.o_pc(dec_pc),.o_seq(dec_seq),.o_tag(dec_tag),.o_sec(dec_sec),.o_data(dec_data));
 // A same-edge new fault must also veto the irrevocable ACK queue write.
 wire tx_fire=enc_v&&tx_ready&&safe;
 ot_qwen_kvc_hub_cdc #(.ENABLE(ENABLE),.DEST(DEST)) transport(
  .rst_n(rst_n),.local_clk(local_clk),.hub_clk(hub_clk),.native_hub_fault(hub_fault),
  .tx_v(enc_v&&safe),.tx_packet(enc_packet),.tx_ready(tx_ready),
  .rx_v(rx_v),.rx_packet(rx_packet),.rx_tag(rx_tag),.rx_source(rx_source),.rx_take(rx_take),
  .local_quiet(shim_quiet),.fault(shim_fault),.x3_v(x3_v),.x3_d(x3_d),.x3_tag(x3_tag),.x3_cr(x3_cr),
  .ar_v(ar_v),.ar_d(ar_d),.ar_tag(ar_tag),.ar_source(ar_source),.ar_cr(ar_cr));
 assign transport_quiet=shim_quiet&&!enc_v&&!dec_v&&!dec_bad&&!ledger_w_v&&!w_v&&!ledger_wd_v&&(ROLE==1||(!room1&&!room2));
 assign upstream_quiescent=stop&&transport_quiet;
 always @(posedge local_clk or negedge rst_n)begin
  if(!rst_n)begin
   epoch<=BOOT_EPOCH;next_seq<=0;exhausted<=0;live<=0;handed<=0;room1<=0;room2<=0;
   fstate<=0;target_epoch<=0;boundary_seq<=0;boundary_exhausted<=0;request_seen<=0;fence_done<=0;
   wd_v<=0;wd_tag<=0;ledger_w_v<=0;ledger_w_sec<=0;ledger_w_data<=0;ledger_w_tag<=0;
   fault<=0;canceled_at_fence<=0;identity_tag<=0;identity_source<=0;
   for(k=0;k<8;k=k+1)begin seqs[k]<=0;tags[k]<=0;end
  end else begin
   room1<=w_room;room2<=room1;request_seen<=fence_req;fence_done<=0;wd_v<=0;ledger_w_v<=0;
   if(rx_v&&rx_take)begin identity_tag<=rx_tag;identity_source<=rx_source;end
   if(ENABLE)begin
    if(fatal_now)fault<=1;
    if(safe)begin
     if(ROLE==0)begin
      if(request_event)begin target_epoch<=next_epoch;fstate<=1;end
      if(source_accept)begin
       live[free_slot]<=1;handed[free_slot]<=1;tags[free_slot]<=w_tag;seqs[free_slot]<=next_seq;
       if(next_seq==16'hffff)exhausted<=1;else next_seq<=next_seq+1'b1;
      end
      if(send_fence)begin boundary_seq<=next_seq;boundary_exhausted<=exhausted;fstate<=2;end
      if(fstate==2&&tx_fire)fstate<=3;
      if(dec_v&&dec_op==2)begin live[match_slot]<=0;handed[match_slot]<=0;wd_v<=1;wd_tag<=dec_tag;end
      if(dec_v&&dec_op==4)begin
       canceled_at_fence<=count;live<=0;handed<=0;epoch<=target_epoch;next_seq<=0;exhausted<=0;
       room1<=0;room2<=0;fstate<=0;fence_done<=1;
      end
     end else begin
      if(ledger_cancel_take)handed[cancel_slot]<=0;
      if(done_accept)begin live[match_slot]<=0;handed[match_slot]<=0;end
      if(dec_v&&dec_op==1)begin
       live[free_slot]<=1;tags[free_slot]<=dec_tag;seqs[free_slot]<=dec_seq;
       if(next_seq==16'hffff)exhausted<=1;else next_seq<=next_seq+1'b1;
       if(!stop)begin
        ledger_w_v<=1;ledger_w_sec<=dec_sec;ledger_w_data<=dec_data;ledger_w_tag<=dec_tag;handed[free_slot]<=1;
       end else handed[free_slot]<=0;
      end
      if(dec_v&&dec_op==3)begin
       target_epoch<=dec_sec[7:0];boundary_seq<=dec_seq;boundary_exhausted<=dec_tag[0];fstate<=1;
      end
      if(send_ack)fstate<=2;
      if(fstate==2&&tx_fire)begin
       canceled_at_fence<=count;live<=0;handed<=0;epoch<=target_epoch;next_seq<=0;exhausted<=0;
       fstate<=0;fence_done<=1;
      end
     end
    end
   end
  end
 end
endmodule
