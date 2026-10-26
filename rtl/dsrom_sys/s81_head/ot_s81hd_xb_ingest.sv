`timescale 1ns/1ps
// One real TP4 head group: actual HSF0 P1/P2 XB landing and indexed x store.
// Load admission, public GO issue and actual token retirement are LIVE caller
// authorities. No HBC context, START date, host source or extra draft topology
// is fabricated. Invalid overlap/identity/address events fault and never stall
// the die ring. job_active lasts through matching token retirement, not replay.
module ot_s81hd_xb_ingest #(
 parameter integer SK=11,
 parameter integer MUT_MODE=0 //1=write-index,2=tag-user,3=retire-on-replay-end
)(
 input wire ck,rst_pin_n,rst_meta_n,rst_job_n,rst_replay_n,
 input wire[1103:0] stage_i,input wire[31:0] stage_tag_i,
 input wire[20:0] untagged_position_i,
 input wire admit_load_i,issue_i,
 input wire retire_i,input wire[30:0] retire_identity_i,
 output wire load_valid_o,output wire[6:0] load_index_o,
 output wire[1023:0] load_data_o,output wire[31:0] load_tag_o,
 output reg forward_valid_o,output reg[1103:0] forward_stage2_o,
 output reg[31:0] message_tag_o,
 output wire loaded_ready,output reg job_active,
 output wire go,xv,replay_busy,replay_done,
 output wire[255:0] xa,xb,
 output wire fault,output reg[7:0] fault_events
);
 reg ri_v;
 reg[1103:1] ri_q;
 reg[31:0] rt_q;
 wire[2:0] rtv_c;
 ot_s81hd_kf u_rtv0(.ck(ck),.d(stage_tag_i[31]),.q(rtv_c[0]));
 ot_s81hd_kf u_rtv1(.ck(ck),.d(stage_tag_i[31]),.q(rtv_c[1]));
 ot_s81hd_kf u_rtv2(.ck(ck),.d(stage_tag_i[31]),.q(rtv_c[2]));
 always@(posedge ck)begin ri_q<=stage_i[1103:1];rt_q<=stage_tag_i;end
 always@(posedge ck or negedge rst_pin_n)if(!rst_pin_n)ri_v<=0;else ri_v<=stage_i[0];
 reg[31:0] p1_tag;
 integer i;
 always@(*)begin
  p1_tag[31]=rt_q[31];
  for(i=0;i<21;i=i+1)p1_tag[i]=rtv_c[i/11]?rt_q[i]:untagged_position_i[i];
  p1_tag[30:21]=rt_q[30:21]&{10{rtv_c[2]}};
 end
 wire p1_xb=ri_v&&ri_q[3:1]==3'd2;
 wire[7:0] p1_index=ri_q[20:13];
 reg wv2;
 reg[6:0] wa2;
 reg[1023:0] wd2;
 reg[31:0] t2;
 always@(posedge ck)begin
  wa2<=p1_index[6:0];wd2<=ri_q[1044:21];t2<=p1_tag;
  forward_stage2_o<={ri_q,ri_v};
 end
 always@(posedge ck or negedge rst_pin_n)
  if(!rst_pin_n)begin wv2<=0;forward_valid_o<=0;end
  else begin wv2<=p1_xb&&p1_index<80;forward_valid_o<=ri_v&&!p1_xb;end
 assign load_valid_o=wv2;
 assign load_index_o=wa2;
 assign load_data_o=wd2;
 assign load_tag_o=t2;
 reg[79:0] seen;
 reg[6:0] count;
 reg filled;
 wire duplicate=wa2<80&&seen[wa2];
 wire tag_bad=count!=0&&t2!=message_tag_o;
 wire start_load=p1_xb&&p1_index<80&&count==0&&!wv2&&admit_load_i&&!job_active&&!fault;
 wire accept_word=wv2&&admit_load_i&&!job_active&&wa2<80&&!duplicate&&!tag_bad&&!fault;
 assign loaded_ready=filled&&!job_active&&!fault;
 wire accept_issue=issue_i&&loaded_ready&&admit_load_i&&!wv2&&!start_load;
 wire retire_match=retire_identity_i=={message_tag_o[20:0],message_tag_o[30:21]};
 wire accept_retire=retire_i&&job_active&&retire_match&&!replay_busy;
 always@(posedge ck or negedge rst_meta_n)begin
  if(!rst_meta_n)begin count<=0;seen<=0;filled<=0;message_tag_o<=0;end
  else begin
   if(start_load)begin count<=0;seen<=0;filled<=0;end
   if(accept_word)begin
    seen[wa2]<=1'b1;count<=count+1'b1;
    if(count==0)message_tag_o<=t2^(MUT_MODE==2 ? (32'd1<<30):32'd0);
    if(count==79)filled<=1;
   end
   if(accept_issue)filled<=0;
   if(accept_retire)begin count<=0;seen<=0;filled<=0;end
  end
 end
 always@(posedge ck or negedge rst_job_n)
  if(!rst_job_n)job_active<=0;
  else begin
   if(accept_issue)job_active<=1;
   if(accept_retire)job_active<=0;
   if(MUT_MODE==3&&job_active&&!replay_busy)job_active<=0;
  end
 wire store_fault;
 wire[7:0] store_index={1'b0,wa2}^(MUT_MODE==1?8'd1:8'd0);
 ot_s81hd_xstore_replay #(.SK(SK),.LOAD_W(1024),.LOAD_INDEXED(1))u_store(
  .ck(ck),.rst_n(rst_replay_n),.load_begin(start_load),.load_v(accept_word),
  .load_d(wd2),.load_index(store_index),.issue(accept_issue),
  .go(go),.xv(xv),.busy(replay_busy),.done(replay_done),.fault(store_fault),.xa(xa),.xb(xb));
 always@(posedge ck or negedge rst_meta_n)begin
  if(!rst_meta_n)fault_events<=0;
  else begin
   if(store_fault)fault_events[0]<=1;
   if(p1_xb&&p1_index>=80)fault_events[1]<=1;
   if(wv2&&tag_bad)fault_events[2]<=1;
   if(wv2&&duplicate)fault_events[3]<=1;
   if(wv2&&(!admit_load_i||job_active))fault_events[4]<=1;
   if(issue_i&&!accept_issue)fault_events[5]<=1;
   if(retire_i&&(!job_active||!retire_match))fault_events[6]<=1;
   if(retire_i&&job_active&&retire_match&&replay_busy)fault_events[7]<=1;
  end
 end
 assign fault=store_fault||(|fault_events);
endmodule
