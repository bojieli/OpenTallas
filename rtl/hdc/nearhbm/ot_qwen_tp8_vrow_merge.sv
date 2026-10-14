`timescale 1ns/1ps
// Opt-in native row front end. No precomputed products: data is FP8 V plus BF16 e.
// Preserve physical K/Z ownership; native PV owners PAIR=0/1 request both physical
// stacks PAIR and PAIR+2. Eight finite slots accept out-of-order addressed returns
// and emit them in issue order. Canonical chains require t=c+256n, enforced here.
// This is transport/control only; the existing head arithmetic remains downstream.
module ot_qwen_tp8_vrow_merge #(parameter integer PAIR=0) (
 input wire clk,rst_n,start,
 input wire [13:0] context_len,
 input wire [15:0] epoch,
 input wire want_valid, output wire want_ready, input wire [13:0] want_t,
 output wire lo_req_valid,hi_req_valid,
 input wire lo_req_ready,hi_req_ready,
 output wire [2:0] req_slot,output wire [13:0] req_t,output wire [15:0] req_epoch,
 input wire lo_rsp_valid,hi_rsp_valid,
 output wire lo_rsp_ready,hi_rsp_ready,
 input wire [2:0] lo_rsp_slot,hi_rsp_slot,
 input wire [13:0] lo_rsp_t,hi_rsp_t,
 input wire [15:0] lo_rsp_epoch,hi_rsp_epoch,
 input wire [1023:0] lo_vrow,hi_vrow,
 input wire [63:0] lo_exp,hi_exp,
 output wire out_valid,input wire out_ready,
 output wire [1023:0] out_vrow,output wire [63:0] out_exp,
 output wire [13:0] out_t,output wire [15:0] out_epoch,
 output wire out_first,out_last,
 output reg done,fault
);
 reg active;
 reg [13:0] limit,next_t[0:127];
 reg [15:0] ep;
 reg [7:0] allocated,sent,returned;
 reg [2:0] wp,sp,rp;
 reg [13:0] qt[0:7];
 reg [1087:0] data[0:7];
 reg [13:0] remaining;
 wire want_bad=want_t>=limit || want_t[7]!=1'(PAIR) || want_t!=next_t[want_t[6:0]];
 assign want_ready=active&&!fault&&!allocated[wp];
 assign lo_req_valid=active&&!fault&&allocated[sp]&&!sent[sp]&&!qt[sp][8];
 assign hi_req_valid=active&&!fault&&allocated[sp]&&!sent[sp]&&qt[sp][8];
 assign req_slot=sp;
 assign req_t=qt[sp];
 assign req_epoch=ep;
 assign lo_rsp_ready=active&&!fault;
 assign hi_rsp_ready=active&&!fault;
 wire lo_good=allocated[lo_rsp_slot]&&sent[lo_rsp_slot]&&!returned[lo_rsp_slot]&&
              !qt[lo_rsp_slot][8]&&lo_rsp_t==qt[lo_rsp_slot]&&lo_rsp_epoch==ep;
 wire hi_good=allocated[hi_rsp_slot]&&sent[hi_rsp_slot]&&!returned[hi_rsp_slot]&&
              qt[hi_rsp_slot][8]&&hi_rsp_t==qt[hi_rsp_slot]&&hi_rsp_epoch==ep;
 assign out_valid=active&&!fault&&allocated[rp]&&returned[rp];
 assign out_vrow=data[rp][1023:0];
 assign out_exp=data[rp][1087:1024];
 assign out_t=qt[rp];
 assign out_epoch=ep;
 assign out_first=qt[rp]<256;
 assign out_last=qt[rp]+14'd256>=limit;
 wire issue=(lo_req_valid&&lo_req_ready)||(hi_req_valid&&hi_req_ready);
 wire take_out=out_valid&&out_ready;
 integer i;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n)begin
   active<=0;limit<=0;ep<=0;allocated<=0;sent<=0;returned<=0;
   wp<=0;sp<=0;rp<=0;remaining<=0;done<=0;fault<=0;
   for(i=0;i<128;i=i+1)next_t[i]<=0;
   for(i=0;i<8;i=i+1)begin qt[i]<=0;data[i]<=0;end
  end else begin
   done<=0;
   if(start)begin
    if(active||fault||context_len>8192)fault<=1;
    else begin
     ep<=epoch;limit<=context_len;allocated<=0;sent<=0;returned<=0;wp<=0;sp<=0;rp<=0;
     for(i=0;i<128;i=i+1)next_t[i]<=14'(PAIR*128+i);
     // Number of native residue-pair rows, including the partial256-position group.
     remaining<={context_len[13:8],7'd0}+
        ((context_len[7:0]>PAIR*128)?((context_len[7:0]-PAIR*128>128)?14'd128:14'(context_len[7:0]-PAIR*128)):14'd0);
     if(context_len==0 || (context_len<=128&&PAIR==1))begin active<=0;done<=1;end
     else active<=1;
    end
   end else if(active&&!fault)begin
    if(want_valid&&want_ready)begin
     if(want_bad)fault<=1;
     else begin
      allocated[wp]<=1;sent[wp]<=0;returned[wp]<=0;qt[wp]<=want_t;wp<=wp+1'b1;
      next_t[want_t[6:0]]<=want_t+14'd256;
     end
    end
    if(issue)begin sent[sp]<=1;sp<=sp+1'b1;end
    if(lo_rsp_valid)begin
     if(!lo_good)fault<=1;
     else begin data[lo_rsp_slot]<={lo_exp,lo_vrow};returned[lo_rsp_slot]<=1;end
    end
    if(hi_rsp_valid)begin
     if(!hi_good || (lo_rsp_valid&&lo_rsp_slot==hi_rsp_slot))fault<=1;
     else begin data[hi_rsp_slot]<={hi_exp,hi_vrow};returned[hi_rsp_slot]<=1;end
    end
    if(take_out)begin
     allocated[rp]<=0;sent[rp]<=0;returned[rp]<=0;rp<=rp+1'b1;
     remaining<=remaining-1'b1;
     if(remaining==1)begin active<=0;done<=1;end
    end
   end
  end
 end
endmodule
