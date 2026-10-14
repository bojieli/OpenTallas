`timescale 1ns/1ps
// Opt-in raw-row candidate, one pair owns 128 canonical c residues.
// Rows are n-major, c-minor, preserving each c's serial FP32 addition order.
// Readout occurs after drain; retained SRAM supplies stable backpressured leaves.
module ot_qwen_tp8_pv256_pair #(parameter integer PAIR=0)(
 input wire clk,rst_n,start,input wire[13:0] context_len,input wire[15:0] epoch,
 input wire in_valid,output wire in_ready,input wire[1023:0] in_v,input wire[63:0] in_e,
 input wire[6:0] in_c,input wire[13:0] in_t,input wire[15:0] in_epoch,
 input wire in_first,in_last,
 output wire out_valid,input wire out_ready,output wire[16383:0] out_leaf,
 output wire[6:0] out_c,output wire[15:0] out_epoch,
 output reg fault,output wire busy,output reg[31:0] accepted,committed,
 output reg[7:0] peak_inflight
);
 localparam IDLE=0,FEED=1,DRAIN=2,READ=3,WAIT=4,OUT=5,BAD=6;
 reg[2:0] state;reg[13:0] lim,next_t;reg[15:0] ep;
 reg[127:0] pending;reg[6:0] rc;reg[7:0] inflight;
 wire[31:0] sf,cv;wire[6:0] cc[0:31];
 wire good=in_epoch==ep && in_t==next_t && in_c==next_t[6:0]
  && in_first==(next_t<256) && in_last==(next_t+256>=lim);
 assign in_ready=state==FEED&&!pending[in_c]&&!fault;
 wire take=in_valid&&in_ready&&good;
 assign out_valid=state==OUT;assign out_c=rc;assign out_epoch=ep;
 assign busy=state!=IDLE;
 genvar h,b;
 generate for(h=0;h<4;h=h+1)begin:gh
  for(b=0;b<8;b=b+1)begin:gb
   localparam S=h*8+b;
   ot_qwen_tp8_pv256_slice u_slice(.clk(clk),.rst_n(rst_n),.take(take),.c(in_c),.first(in_first),
    .v(in_v[128*b+:128]),.e(in_e[16*h+:16]),.read_leaf(state==READ),.leaf_c(rc),
    .leaf(out_leaf[512*S+:512]),.commit(cv[S]),.commit_c(cc[S]),.fault(sf[S]));
  end
 end endgenerate
 wire retire=cv[0];
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin state<=IDLE;fault<=0;pending<=0;rc<=0;inflight<=0;
   accepted<=0;committed<=0;peak_inflight<=0;next_t<=0;lim<=0;ep<=0;end
  else if((start&&state!=IDLE)||(|sf)||(in_valid&&in_ready&&!good))begin
   state<=BAD;fault<=1;
  end else begin
   if(take)begin pending[in_c]<=1;accepted<=accepted+1;end
   if(retire)begin pending[cc[0]]<=0;committed<=committed+1;end
   case({take,retire}) 2'b10:inflight<=inflight+1;2'b01:inflight<=inflight-1;default:;endcase
   if(inflight>peak_inflight)peak_inflight<=inflight;
   case(state)
    IDLE:if(start)begin
     ep<=epoch;lim<=context_len;next_t<=PAIR*128;rc<=0;accepted<=0;committed<=0;
     peak_inflight<=0;pending<=0;inflight<=0;
     // Current full-shape candidate requires all 128 owned residues present.
     if(context_len<=PAIR*128+127||context_len>8192)begin state<=BAD;fault<=1;end
     else state<=FEED;
    end
    FEED:if(take)begin
     if(in_c==127)begin
      if(next_t+129>=lim)state<=DRAIN;
      else next_t<=next_t+129;
     end else if(next_t+1>=lim)state<=DRAIN;
     else next_t<=next_t+1;
    end
    DRAIN:if(inflight==0)state<=READ;
    READ:state<=WAIT;
    WAIT:state<=OUT;
    OUT:if(out_ready)begin if(rc==127)state<=IDLE;else begin rc<=rc+1;state<=READ;end end
    default:;
   endcase
  end
 end
endmodule
