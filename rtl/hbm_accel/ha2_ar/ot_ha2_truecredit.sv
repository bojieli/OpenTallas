`timescale 1ns/1ps
// Additive INTERNAL TU successor; no production endpoint selects this yet.
// Reset must be common to both endpoints and discard every in-flight frame.
// Slots are reserved before the unstallable hub flight, not at its far end.
module ot_ha2_truecredit_sender #(
 parameter integer W=544, INJ=2, AW=6, TAGW=16, MUTANT=0,
 // REG (hbm-blocks 2026-10-07, default 0): arrival / return land in pin registers (+1 cycle each; arrivals only follow
 // reservations and late returns only hold a slot longer, so the credit contract is unchanged), issue_ready and the
 // reserved > sent compare are registers computed from the next state (same values, 0 cycles): tx cal650 4071ff1d8
 // arrival_v -> next_send / send_data enable -385.58 ps (input-port enable fanning out to 1,088 data flops)
 parameter integer REG=0
)(input wire clk,rst_n,
 input wire[INJ-1:0] issue_v,arrival_v,return_v,
 input wire[INJ*W-1:0] arrival_data,
 input wire[INJ*TAGW-1:0] return_tag,
 output wire[INJ-1:0] issue_ready,
 output reg[INJ-1:0] send_v,
 output reg[INJ*W-1:0] send_data,
 output reg[INJ*TAGW-1:0] send_tag,
 output wire quiet,fault);
 localparam integer DEPTH=1<<AW;
 initial if(TAGW<=AW)$fatal(1,"HA2 truecredit tags must exceed slot address width");
 wire[INJ-1:0] bads,idle;
 wire[INJ-1:0] av,rvv; wire[INJ*W-1:0] ad; wire[INJ*TAGW-1:0] rtg;
 generate if(REG!=0)begin:g_land
  reg[INJ-1:0] av_r,rv_r; reg[INJ*W-1:0] ad_r; reg[INJ*TAGW-1:0] rt_r;
  always @(posedge clk or negedge rst_n) if(!rst_n)begin av_r<=0;rv_r<=0;end else begin av_r<=arrival_v;rv_r<=return_v;end
  always @(posedge clk)begin ad_r<=arrival_data;rt_r<=return_tag;end
  assign av=av_r;assign rvv=rv_r;assign ad=ad_r;assign rtg=rt_r;
 end else begin:g_direct
  assign av=arrival_v;assign rvv=return_v;assign ad=arrival_data;assign rtg=return_tag;
 end endgenerate
 for(genvar i=0;i<INJ;i=i+1)begin:g_lane
  reg[AW:0] reserved,sent;
  reg[TAGW-1:0] next_send,next_return;
  reg bad;
  wire rv=rvv[i];
  wire ret_ok=rv && rtg[i*TAGW+:TAGW]==next_return && sent!=0;
  wire gt;
  wire arr_ok=av[i] && gt;
  wire ird;
  assign issue_ready[i]=ird;
  assign bads[i]=bad;
  assign idle[i]=(reserved==0)&&(sent==0)&&!send_v[i];
  // next state (as the original always block computes it)
  wire iss=issue_v[i]&&ird;
  wire bad_n=bad | (issue_v[i]&&!ird) | (rv&&!ret_ok) | (av[i]&&!arr_ok) | (reserved>DEPTH) | (sent>reserved);
  wire[AW:0] res_n=(iss&&!ret_ok)?reserved+1'b1:(!iss&&ret_ok)?reserved-1'b1:reserved;
  wire[AW:0] sent_n=(arr_ok&&!ret_ok)?sent+1'b1:(!arr_ok&&ret_ok)?sent-1'b1:sent;
  if(REG!=0)begin:g_rr
   reg ird_r,gt_r;
   always @(posedge clk or negedge rst_n)
    if(!rst_n)begin ird_r<=1'b1;gt_r<=1'b0;end
    else begin ird_r<=!bad_n && ((MUTANT==1)||res_n<DEPTH);gt_r<=res_n>sent_n;end
   assign ird=ird_r;assign gt=gt_r;
  end else begin:g_rc
   assign ird=!bad && ((MUTANT==1)||reserved<DEPTH);
   assign gt=reserved>sent;
  end
  always @(posedge clk or negedge rst_n)
   if(!rst_n)begin
    reserved<=0;sent<=0;next_send<=0;next_return<=0;bad<=0;send_v[i]<=0;
    send_tag[i*TAGW+:TAGW]<=0;
   end else begin
    send_v[i]<=arr_ok&&!bad;
    bad<=bad_n;
    reserved<=res_n;
    sent<=sent_n;
    if(arr_ok)begin send_tag[i*TAGW+:TAGW]<=next_send;next_send<=next_send+1'b1;end
    if(ret_ok)next_return<=next_return+1'b1;
   end
  always @(posedge clk)if(arr_ok)send_data[i*W+:W]<=ad[i*W+:W];
 end
 assign quiet=&idle;assign fault=|bads;
endmodule

// Receiver-local output launch preserves the original half-shell ready margin.
// A credit is returned only on a real queue retirement; relays may delay it.
module ot_ha2_truecredit_receiver #(
 parameter integer W=544, INJ=2, AW=6, TAGW=16, MUTANT=0
)(input wire clk,rst_n,
 input wire[INJ-1:0] arrival_v,receiver_ready,
 input wire[INJ*W-1:0] arrival_data,
 input wire[INJ*TAGW-1:0] arrival_tag,
 output reg[INJ-1:0] send_v,return_v,
 output reg[INJ*W-1:0] send_data,
 output reg[INJ*TAGW-1:0] return_tag,
 output wire quiet,fault);
 initial if(TAGW<=AW)$fatal(1,"HA2 truecredit tags must exceed slot address width");
 wire[INJ-1:0] bads,idle;
 for(genvar i=0;i<INJ;i=i+1)begin:g_lane
  reg[TAGW-1:0] expect_arrival,expect_retire;
  reg bad;
  wire empty,ovf;
  wire[AW:0] count;
  wire[W+TAGW-1:0] head;
  wire valid_arrival=arrival_v[i] && arrival_tag[i*TAGW+:TAGW]==expect_arrival && !bad;
  wire pop=!empty&&receiver_ready[i]&&!bad;
  wire[TAGW-1:0] head_tag=head[W+:TAGW];
  ot_ha2_fifo #(.W(W+TAGW),.AW(AW)) u_queue
   (.clk(clk),.rst_n(rst_n),.push(valid_arrival),
    .din({arrival_tag[i*TAGW+:TAGW],arrival_data[i*W+:W]}),
    .pop(pop),.empty(empty),.dout(head),.ovf(ovf),.count(count));
  assign bads[i]=bad||ovf;
  assign idle[i]=empty&&!send_v[i]&&!return_v[i];
  always @(posedge clk or negedge rst_n)
   if(!rst_n)begin
    expect_arrival<=0;expect_retire<=0;bad<=0;send_v[i]<=0;return_v[i]<=0;
    return_tag[i*TAGW+:TAGW]<=0;
   end else begin
    send_v[i]<=pop;return_v[i]<=pop;
    if(arrival_v[i]&&!valid_arrival)bad<=1;
    if(valid_arrival)expect_arrival<=expect_arrival+1'b1;
    if(pop)begin
     if(head_tag!=expect_retire)bad<=1;
     return_tag[i*TAGW+:TAGW]<=head_tag ^ ((MUTANT==2)?TAGW'(1):TAGW'(0));
     expect_retire<=expect_retire+1'b1;
    end
   end
  always @(posedge clk)if(pop)send_data[i*W+:W]<=head[W-1:0];
 end
 assign quiet=&idle;assign fault=|bads;
endmodule
