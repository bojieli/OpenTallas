`timescale 1ns/1ps
// Opt-in raw-row candidate, one pair owns 128 canonical c residues.
// Rows are n-major, c-minor, preserving each c's serial FP32 addition order.
// Readout occurs after drain; retained SRAM supplies stable backpressured leaves.
module ot_qwen_tp8_pv256_pair #(parameter integer PAIR=0, parameter integer TREE=0,
 parameter integer STATIC_SCHEDULE=0, parameter integer FIRST_INPUT_AGE=146)(
 input wire clk,rst_n,start,input wire[31:0] slice_clk,input wire[13:0] context_len,input wire[15:0] epoch,
 input wire in_valid,output wire in_ready,input wire[1023:0] in_v,input wire[63:0] in_e,
 input wire[6:0] in_c,input wire[13:0] in_t,input wire[15:0] in_epoch,
 input wire in_first,in_last,
 output wire out_valid,input wire out_ready,output wire[16383:0] out_leaf,
 output wire[6:0] out_c,output wire[15:0] out_epoch,
 output reg fault,output wire busy,output reg[31:0] accepted,committed,
 output reg[7:0] peak_inflight
);
 localparam IDLE=0,FEED=1,DRAIN=2,READ=3,WAIT=4,OUT=5,BAD=6,TRA=7,TRB=8,TRADD=9,TRDRAIN=10,INIT=11;
 reg[3:0] state;reg[7:0] nodes;reg[6:0] ti;wire[16383:0] raw_leaf,tree_sum;reg[13:0] lim,next_t;reg[15:0] ep;
 reg[6:0] init_c;reg[127:0] pending;reg[6:0] rc;reg[7:0] inflight;
 reg[15:0] age,rows_expected,rows_issued;
 reg[3:0] drain_left,reduce_left;
 reg[10:0] feed_commit_slots;
 reg[6:0] tree_commit_slots;
 wire[31:0] sf,cv;wire[6:0] cc[0:31];
 wire good=in_epoch==ep && in_t==next_t && in_c==next_t[6:0]
  && in_first==(next_t<256) && in_last==(next_t+256>=lim);
 wire feed_slot=state==FEED && age+1>=FIRST_INPUT_AGE && rows_issued<rows_expected;
 assign in_ready=(STATIC_SCHEDULE?feed_slot:(state==FEED&&!pending[in_c]))&&!fault;
 wire take=in_valid&&in_ready&&good;
 wire expected_commit=feed_commit_slots[10]||tree_commit_slots[6];
 wire static_bad=STATIC_SCHEDULE && state!=IDLE && state!=BAD &&
   ((in_valid!=feed_slot) || (feed_slot&&(!good||pending[in_c])) ||
    (cv!={32{expected_commit}}) || (state==OUT&&!out_ready));
 assign out_leaf=TREE?tree_sum:raw_leaf;
 assign out_valid=state==OUT;assign out_c=rc;assign out_epoch=ep;
 assign busy=state!=IDLE;
 genvar h,b;
 generate for(h=0;h<4;h=h+1)begin:gh
  for(b=0;b<8;b=b+1)begin:gb
   localparam S=h*8+b;
   ot_qwen_tp8_pv256_slice u_slice(.clk(slice_clk[S]),.rst_n(rst_n),.take(take),.c(in_c),.first(in_first),.init_zero(state==INIT),.init_c(init_c),
    .v(in_v[128*b+:128]),.e(in_e[16*h+:16]),.read_leaf(state==READ||state==TRA||state==TRB),.leaf_c((state==TRA||state==TRB)?((ti<<1)+(state==TRB)):rc),
    .reduce_issue(state==TRADD),.reduce_capture(state==TRB),.reduce_last(nodes==2),.reduce_dst(ti),.tree_sum(tree_sum[512*S+:512]),
    .leaf(raw_leaf[512*S+:512]),.commit(cv[S]),.commit_c(cc[S]),.fault(sf[S]));
  end
 end endgenerate
 wire retire=cv[0];
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin state<=IDLE;fault<=0;pending<=0;rc<=0;inflight<=0;
   accepted<=0;committed<=0;peak_inflight<=0;next_t<=0;lim<=0;ep<=0;
   age<=0;rows_expected<=0;rows_issued<=0;drain_left<=0;reduce_left<=0;
   feed_commit_slots<=0;tree_commit_slots<=0;end
  else if((start&&state!=IDLE)||(|sf)||(in_valid&&in_ready&&!good)||static_bad)begin
   state<=BAD;fault<=1;
  end else begin
   if(state!=IDLE)age<=age+1;
   feed_commit_slots<={feed_commit_slots[9:0],take};
   tree_commit_slots<={tree_commit_slots[5:0],state==TRADD};
   if(take)rows_issued<=rows_issued+1;
   if(take)begin pending[in_c]<=1;accepted<=accepted+1;end
   if(retire&&(state==FEED||state==DRAIN))begin pending[cc[0]]<=0;committed<=committed+1;end
   case({take,retire&&(state==FEED||state==DRAIN)}) 2'b10:inflight<=inflight+1;2'b01:inflight<=inflight-1;default:;endcase
   if(inflight>peak_inflight)peak_inflight<=inflight;
   case(state)
    IDLE:if(start)begin
     ep<=epoch;lim<=context_len;init_c<=0;next_t<=PAIR*128;rc<=0;accepted<=0;committed<=0;
     peak_inflight<=0;pending<=0;inflight<=0;
     age<=0;rows_issued<=0;feed_commit_slots<=0;tree_commit_slots<=0;
     rows_expected<=(context_len/256)*128+
       ((context_len%256<=PAIR*128)?0:
        ((context_len%256>=PAIR*128+128)?128:context_len%256-PAIR*128));
     drain_left<=0;reduce_left<=0;
     // Initialize every canonical residue, including absent rows and empty pairs.
     if(context_len==0||context_len>8192)begin state<=BAD;fault<=1;end
     else state<=INIT;
    end
    INIT:if(init_c==127)state<=(lim<=PAIR*128)?DRAIN:FEED;else init_c<=init_c+1;
    FEED:if(take)begin
     drain_left<=12;
     if(in_c==127)begin
      if(next_t+129>=lim)state<=DRAIN;
      else next_t<=next_t+129;
     end else if(next_t+1>=lim)state<=DRAIN;
     else next_t<=next_t+1;
    end
    DRAIN:begin
     if(STATIC_SCHEDULE && drain_left!=0)drain_left<=drain_left-1;
     if(STATIC_SCHEDULE?(drain_left<=1):(inflight==0))begin
      if(STATIC_SCHEDULE && inflight!=0)begin state<=BAD;fault<=1;end
      else if(TREE)begin nodes<=128;ti<=0;rc<=0;state<=TRA;end else state<=READ;
     end
    end
    READ:state<=WAIT;
    WAIT:state<=OUT;
    TRA:state<=TRB;
    TRB:state<=TRADD;
    TRADD:begin reduce_left<=7;if(ti+1==nodes/2)state<=TRDRAIN;else begin ti<=ti+1;state<=TRA;end end
    TRDRAIN:begin
     if(STATIC_SCHEDULE && reduce_left!=0)reduce_left<=reduce_left-1;
     if(STATIC_SCHEDULE?(reduce_left==1):(retire&&cc[0]+1==nodes/2))begin
      if(STATIC_SCHEDULE&&(!retire||cc[0]+1!=nodes/2))begin state<=BAD;fault<=1;end
      else if(nodes==2)state<=OUT;else begin nodes<=nodes/2;ti<=0;state<=TRA;end
     end
    end
    OUT:if(STATIC_SCHEDULE||out_ready)begin if(TREE||rc==127)state<=IDLE;else begin rc<=rc+1;state<=READ;end end
    default:;
   endcase
  end
 end
endmodule
