`timescale 1ns/1ps
`default_nettype none
// Six dated descriptors through the existing F20 configuration protocol.
// Dates are sampled engine-start edges relative to local edge zero. Release is
// exclusive. All bank clients are reserved throughout active; no request arbiter.
module ot_hbm_su_indexed_scalar_f20 #(
 parameter integer READ_SAMPLE=11,WRITE_COMMIT=8,MUT_PHASE=0,
 parameter [7:0] TARGET=8'd180
)(input wire clk,rst_n,
 input wire cfg_v,input wire[7:0]cfg_target,input wire[11:0]cfg_addr,
 input wire[255:0]cfg_data,input wire desc_v,input wire[11:0]desc_base,
 input wire[12:0]desc_limit,input wire[15:0]desc_loops,input wire launch_v,
 input wire[32*257-1:0]rr,
 output wire[32*17-1:0]rq,output wire[32*281-1:0]wq,
 output reg active,done,program_fault,output wire configured,target_fault,engine_fault,
 output reg[15:0]edge_index,output wire engine_busy,engine_done,
 output wire engine_start,output wire[119:0]descriptor
);
 wire we,sv;wire[7:0]wa,sb;wire[8:0]sl;wire[15:0]loops;wire[255:0]wd;
 ot_static_program_target #(.TARGET(TARGET),.PCW(8)) target(
  .clk(clk),.clk_cap(clk),.rst_n(rst_n),.tgt(TARGET),
  .cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
  .program_active(active),.program_cfg_we(we),.program_cfg_addr(wa),.program_cfg_data(wd),
  .program_start_v(sv),.program_start_base(sb),.program_start_limit(sl),.program_start_loops(loops),
  .configured(configured),.fault(target_fault));
 reg[151:0]rows[0:5];reg[2:0]pc;reg[3:0]last;
 wire[151:0]row=rows[pc];
 assign descriptor=row[119:0];
 assign engine_start=active && edge_index==row[135:120];
 localparam integer MIN_RELEASE=2*READ_SAMPLE+WRITE_COMMIT+7;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active<=0;done<=0;program_fault<=0;edge_index<=0;pc<=0;last<=0;end
  else begin
   done<=0;
   if(we)begin
    if(active || wa>=6 || wd[223:152]!=0 || wd[151:136]<{1'b0,wd[135:120]}+MIN_RELEASE)
     program_fault<=1;
    else rows[wa]<=wd[151:0];
   end
   if(sv)begin
    if(active || sb>=6 || sl>6 || sl<=sb || loops!=1)program_fault<=1;
    else begin active<=1;edge_index<=0;pc<=sb[2:0];last<=sl[3:0];end
   end
   if(active)begin
    edge_index<=edge_index+1'b1;
    if(engine_start && engine_busy)program_fault<=1;
    if(edge_index==row[151:136]-1'b1)begin
     if(engine_busy && !engine_done)program_fault<=1;
     if({1'b0,pc}+1'b1==last)begin active<=0;done<=1;end
     else begin
      pc<=pc+1'b1;
      // No hidden wait: overlapping or backwards dates are a programme fault.
      if(rows[pc+1'b1][135:120]<=edge_index)program_fault<=1;
     end
    end
    if(edge_index==16'hffff)begin active<=0;program_fault<=1;end
   end
  end
 end
 ot_hbm_su_indexed_scalar #(.READ_SAMPLE(READ_SAMPLE),.WRITE_COMMIT(WRITE_COMMIT),.MUT_PHASE(MUT_PHASE)) engine(
  .clk(clk),.rst_n(rst_n),.start(engine_start),
  .index_word(descriptor[23:0]),.score_base(descriptor[47:24]),.score_limit(descriptor[71:48]),
  .dest_word(descriptor[95:72]),.dyn_mul(descriptor[119:96]),.rr(rr),.rq(rq),.wq(wq),
  .busy(engine_busy),.done(engine_done),.fault(engine_fault));
endmodule

// One physical bank-client selector. reserve is a scheduled programme signal;
// it never depends on requests, busy, response valid, or memory contents.
module ot_hbm_su_indexed_scalar_bank_select(
 input wire clk,rst_n,reserve,
 input wire[16:0]normal_rq,gather_rq,input wire[280:0]normal_wq,gather_wq,
 input wire[256:0]bank_rr,input wire bank_done,
 output wire[16:0]bank_rq,output wire[280:0]bank_wq,
 output wire[256:0]normal_rr,gather_rr,output wire normal_done,
 output reg fault
);
 assign bank_rq=reserve?gather_rq:normal_rq;
 assign bank_wq=reserve?gather_wq:normal_wq;
 assign normal_rr=reserve?257'd0:bank_rr;
 assign normal_done=!reserve&&bank_done;
 assign gather_rr=reserve?bank_rr:257'd0;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)fault<=0;
  else if(reserve&&(normal_rq[16]||normal_wq[280]))fault<=1;
endmodule
`default_nettype wire
