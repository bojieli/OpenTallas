`timescale 1ns/1ps
// S81 dedicated MIX endpoint, one command computes all four residual copies.
// arg[23:14]=0,arg[13:0]=descriptor VM row. Descriptor words:
// 0 H base (640 packed BF16 rows); 1 K base (1280); 2 W=qw*kw base (1280);
// 3 shared V base (320); 4 output H base (640 packed BF16); 5 eps; 6 scale.
// H may overwrite in place: every copy is fully read before its add replay.
// Five independent row readers are statically reserved for the entire job.
// Their fixed-latency, in-order replies MUST return each issued beat together;
// a partial reply faults rather than silently combining different beats.
// VM accepts each packed BF16 output in its reserved write slot; no credit stall
// is introduced. f_inp means all producer rows and reservation are present.
// Pins are registered. This new master needs a die slot and phase-R clocks;
// it does not replace the closed lookup master or claim routing qualification.
module dsfd_engram_mix_c #(parameter integer MUT=0, VM_LAT=1, WRITE_COMMIT_LAT=1, ISSUE_PERIOD=1)(
 input wire [32:0] ck,input wire [0:0] rst,input wire [84:0] c_cmd,
 output wire [8:0] c_done,output wire [1:0] c_st,input wire [0:0] f_inp,
 output wire [4:0] rq_v,output wire [69:0] rq_row,
 input wire [4:0] rs_v,input wire [2559:0] rs_d,
 output wire [0:0] wq_v,output wire [13:0] wq_row,
 output wire [15:0] wq_mask,output wire [511:0] wq_d);
 wire go,iv,phase;wire [1:0] copy,gc,oc;
 wire [1023:0] h,kv,w,result;wire [31:0] eps,scale,gate,hh,kk,dd;wire gv,ov,mf;
 ot_s81_engram_endpoint_ctl #(.MUT(MUT),.VM_LAT(VM_LAT),.WRITE_COMMIT_LAT(WRITE_COMMIT_LAT),.ISSUE_PERIOD(ISSUE_PERIOD)) control(
  ck[0],rst,c_cmd,c_done,c_st,f_inp,rq_v,rq_row,rs_v,rs_d,wq_v,wq_row,wq_mask,wq_d,
  go,iv,phase,copy,h,kv,w,eps,scale,gv,ov,mf,oc,result);
 ot_s81_engram_mix #(.MUT(MUT)) mix(ck[1],rst[0],go,phase,iv,copy,h,kv,w,kv,eps,scale,
  gv,gc,gate,hh,kk,dd,ov,oc,result,mf,ck[32:2]);
endmodule

module ot_s81_engram_endpoint_ctl #(parameter integer MUT=0, VM_LAT=1, WRITE_COMMIT_LAT=1, ISSUE_PERIOD=1)(
 input wire [0:0] ck,input wire [0:0] rst,input wire [84:0] c_cmd,
 output wire [8:0] c_done,output wire [1:0] c_st,input wire [0:0] f_inp,
 output reg [4:0] rq_v,output reg [69:0] rq_row,
 input wire [4:0] rs_v,input wire [2559:0] rs_d,
 output reg [0:0] wq_v,output reg [13:0] wq_row,
 output reg [15:0] wq_mask,output reg [511:0] wq_d,
 output reg go,iv,phase,output reg [1:0] copy,
 output reg [1023:0] h,kv,w,output wire [31:0] eps,scale,
 input wire gv,ov,mf,input wire [1:0] oc,input wire [1023:0] result);

 reg [1:0] reset_sync;
 always @(posedge ck[0] or negedge rst[0])if(!rst[0])reset_sync<=0;else reset_sync<={reset_sync[0],1'b1};
 wire rn=reset_sync[1];
 wire jv,jnew,epf;wire [83:0] jd,jnd;reg done;reg fault;
 reg [0:0] inp_q;
 always @(posedge ck[0] or negedge rn)if(!rn)inp_q<=0;else inp_q<=f_inp;
 ot_s81_slab_ep ep(.c_clk(ck[0]),.c_rst_n(rn),.c_cmd(c_cmd),.c_done(c_done),.c_st(c_st),
 .e_clk(ck[0]),.e_rst_n(rn),.j_v(jv),.j_d(jd),.j_new(jnew),.j_new_d(jnd),.j_present(1'b1),.j_done(done),.slab_fault(fault),.ep_fault(epf));
 reg [2:0] state;localparam IDLE=0,DESC=1,BEGIN=2,REDUCE=3,GATE=4,ADD=5,DRAIN=6,FINISH=7;
 reg [511:0] desc;reg [8:0] req,received,written;reg [15:0] commit_left;reg [$clog2(ISSUE_PERIOD+1)-1:0] issue_tick;
 // Registered VM reservation pipeline checks the published latency exactly.
 // Lost/extra/late replies are a transport fault, never an operand wait.
 reg [4:0] expected[0:VM_LAT];integer delay_stage;
 initial if(ISSUE_PERIOD<1 || VM_LAT<1 || WRITE_COMMIT_LAT<1 || WRITE_COMMIT_LAT>65535)$fatal(1,"VM latency must be at least one cycle");
 always @(posedge ck[0] or negedge rn)if(!rn)begin
  for(delay_stage=0;delay_stage<=VM_LAT;delay_stage=delay_stage+1)expected[delay_stage]<=0;
 end else begin
  expected[0]<=rq_v;
  for(delay_stage=1;delay_stage<=VM_LAT;delay_stage=delay_stage+1)expected[delay_stage]<=expected[delay_stage-1];
 end
 reg [4:0] rvq;reg [2559:0] rdq;
 always @(posedge ck[0] or negedge rn)if(!rn)rvq<=0;else rvq<=rs_v;
 always @(posedge ck[0])rdq<=rs_d;
 assign eps=desc[160+:32];assign scale=desc[192+:32];
 wire [13:0] hb=desc[0+:14],kb=desc[32+:14],wb=desc[64+:14],vb=desc[96+:14],ob=desc[128+:14];
 integer lane;
 always @(posedge ck[0] or negedge rn)if(!rn)begin
  state<=IDLE;rq_v<=0;wq_v<=0;done<=0;fault<=0;go<=0;iv<=0;phase<=0;copy<=0;req<=0;received<=0;written<=0;commit_left<=0;issue_tick<=0;
 end else begin
  rq_v<=0;wq_v<=0;done<=0;go<=0;iv<=0;
  if(mf||epf||rvq!=expected[VM_LAT])fault<=1;
  case(state)
  IDLE:if(jv&&!fault)begin
   if(!inp_q||jd[30:21]!=0)fault<=1;
   else begin rq_v<=5'b00001;rq_row[0+:14]<=jd[7+:14];state<=DESC;end
  end
  DESC:if(rvq[0])begin
   desc<=rdq[0+:512];copy<=0;state<=BEGIN;
   // No address wrapping or descriptor truncation: full shape must fit VM.
   if(rdq[0+:32]>15744||rdq[32+:32]>15104||rdq[64+:32]>15104||rdq[96+:32]>16064||rdq[128+:32]>15744)fault<=1;
   // Overwriting H in place is legal; partial H alias or writes into key,
   // layer weights, or shared value would corrupt unread copies.
   if((rdq[128+:32]!=rdq[0+:32] && rdq[128+:32]<rdq[0+:32]+640 && rdq[0+:32]<rdq[128+:32]+640) ||
      (rdq[128+:32]<rdq[32+:32]+1280 && rdq[32+:32]<rdq[128+:32]+640) ||
      (rdq[128+:32]<rdq[64+:32]+1280 && rdq[64+:32]<rdq[128+:32]+640) ||
      (rdq[128+:32]<rdq[96+:32]+320 && rdq[96+:32]<rdq[128+:32]+640))fault<=1;
   if(rdq[191] || rdq[183+:8]==255 || rdq[160+:31]==0 || rdq[223] || rdq[215+:8]==255 || rdq[192+:31]==0)fault<=1;
  end
  BEGIN:begin go<=1;phase<=0;req<=0;received<=0;written<=0;issue_tick<=0;state<=REDUCE;end
  REDUCE:begin
   if(issue_tick!=0)issue_tick<=issue_tick-1;
   if(req<160&&issue_tick==0)begin
    issue_tick<=ISSUE_PERIOD-1;
    rq_v<=5'b11111;
    rq_row[0+:14]<=hb+160*copy+req;
    for(lane=0;lane<2;lane=lane+1)begin
     rq_row[14*(lane+1)+:14]<=kb+320*copy+2*req+lane;
     rq_row[14*(lane+3)+:14]<=wb+320*copy+2*req+lane;
    end
    req<=req+1;
   end
   if(|rvq)begin
    if(rvq!=5'b11111||received>=160)fault<=1;
    else begin for(lane=0;lane<32;lane=lane+1)h[32*lane+:32]<={rdq[16*lane+:16],16'd0};kv<=rdq[512+:1024];w<=rdq[1536+:1024];iv<=1;received<=received+1;if(received==159)state<=GATE;end
   end
  end
  GATE:if(gv)begin phase<=1;req<=0;received<=0;issue_tick<=0;state<=ADD;end
  ADD:begin
   if(issue_tick!=0)issue_tick<=issue_tick-1;
   if(req<160&&issue_tick==0)begin
    issue_tick<=ISSUE_PERIOD-1;
    rq_v<=5'b00111;
    rq_row[0+:14]<=hb+160*copy+req;
    for(lane=0;lane<2;lane=lane+1)begin
     rq_row[14*(lane+1)+:14]<=vb+2*req+lane;
    end
    req<=req+1;
   end
   if(|rvq)begin
    if(rvq!=5'b00111||received>=160)fault<=1;
    else begin for(lane=0;lane<32;lane=lane+1)h[32*lane+:32]<={rdq[16*lane+:16],16'd0};kv<=rdq[512+:1024];iv<=1;received<=received+1;if(received==159)state<=DRAIN;end
   end
  end
  DRAIN:;
  FINISH:begin
   if(commit_left!=0)commit_left<=commit_left-1;
   else if(done)state<=IDLE;else done<=!fault&&!mf&&!epf;
  end
  default:fault<=1;
  endcase
  if(ov)begin
   if((state!=ADD&&state!=DRAIN)||oc!=copy||written>=160)fault<=1;
   wq_v<=1'b1;wq_mask<=16'hffff;
   for(lane=0;lane<32;lane=lane+1)wq_d[16*lane+:16]<=result[32*lane+16+:16];
   wq_row[0+:14]<=ob+160*copy+written;
   written<=written+1;
   if(written==159)begin if(copy==3)begin state<=FINISH;commit_left<=WRITE_COMMIT_LAT;end else begin copy<=copy+1;state<=BEGIN;end end
  end
 end
endmodule
