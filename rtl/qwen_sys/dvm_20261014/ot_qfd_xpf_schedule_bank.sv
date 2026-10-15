`timescale 1ns/1ps
// Explicit compiler sideband bank for one producer stage. Load every record
// while both controllers are stopped, then seal; unsealed blocks ALL issues.
// Re-load for the next stage only after producer candidates and the current
// arm transaction have drained. Data92 LSB {xpf72,producer_pc12,unit2,stage6}.
// The stage may carry an arm for a consumer in the NEXT stage: e.g. final
// residual writes X for next-layer QKV, or initial embedding writes X.
// Compiler must reject live-in operands without that preceding-stage record.
module ot_qfd_xpf_schedule_bank #(
 parameter integer N=8, ARM_TO_WRITE_EDGES=3, MUT_EARLY=0,
 parameter integer IW=(N<2)?1:$clog2(N)
)(
 input wire clk,rst_n,
 input wire cfg_v,input wire [IW-1:0] cfg_index,input wire [91:0] cfg_data,
 input wire cfg_clear,cfg_seal,input wire [IW:0] cfg_count,
 output wire cfg_ready,
 input wire [5:0] stage,
 input wire me_v,input wire [11:0] me_pc,input wire me_issue,
 input wire su_v,input wire [11:0] su_pc,input wire su_issue,
 output wire me_allow,su_allow,output wire [71:0] xpf,
 output wire fault
);
 reg [91:0] records[0:N-1];reg [N-1:0] loaded,used;
 reg sealed;reg [IW:0] count;reg local_fault;
 wire arm_ready,guard_allow,guard_fault,released;
 reg found,me_required,su_required;reg [IW-1:0] pick;
 integer i,j;
 always @* begin
  found=0;pick=0;me_required=0;su_required=0;
  for(i=N-1;i>=0;i=i-1)begin
   if(sealed&&i<count&&!used[i]&&records[i][91:86]==stage)begin
    if(records[i][85:84]==1&&me_v&&records[i][83:72]==me_pc)begin found=1;pick=i;me_required=1;end
    if(records[i][85:84]==2&&su_v&&records[i][83:72]==su_pc)begin found=1;pick=i;su_required=1;end
   end
  end
 end
 reg [IW-1:0] selected;reg [1:0] selected_unit;reg busy;
 wire arm=sealed&&found&&!busy&&arm_ready&&!local_fault;
 wire pv=(selected_unit==1)?me_v:su_v;
 wire [11:0] pc=(selected_unit==1)?me_pc:su_pc;
 wire issued=(selected_unit==1)?me_issue:su_issue;
 assign me_allow=sealed&&!local_fault&&!guard_fault&&
                 ((!me_required&&(!busy||selected_unit!=1))||(busy&&selected_unit==1&&guard_allow));
 assign su_allow=sealed&&!local_fault&&!guard_fault&&
                 ((!su_required&&(!busy||selected_unit!=2))||(busy&&selected_unit==2&&guard_allow));
 assign cfg_ready=!busy&&!me_v&&!su_v;
 assign fault=local_fault|guard_fault;
 ot_qfd_xpf_release_guard #(.ARM_TO_WRITE_EDGES(ARM_TO_WRITE_EDGES),.MUT_EARLY(MUT_EARLY)) guard
 (.clk(clk),.rst_n(rst_n),.arm_v(arm),.arm_descriptor(records[pick][71:0]),
  .arm_pc(records[pick][83:72]),.arm_unit(records[pick][85:84]),.arm_ready(arm_ready),
  .producer_v(pv),.producer_pc(pc),.producer_unit(selected_unit),.producer_issue(busy&&issued),
  .producer_requires_arm(busy),.producer_allow(guard_allow),.xpf(xpf),.released(released),.fault(guard_fault));
 reg seal_good;
 always @* begin
  seal_good=cfg_count!=0&&cfg_count<=N;
  for(i=0;i<N;i=i+1)if(i<cfg_count&&!loaded[i])seal_good=0;
  // One producer issue cannot release two distinct operand epochs. Such a
  // reuse needs an explicitly retained epoch or replay, not a second arm.
  for(i=0;i<N;i=i+1)for(j=0;j<i;j=j+1)
   if(i<cfg_count&&records[i][91:72]==records[j][91:72])seal_good=0;
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin loaded<=0;used<=0;sealed<=0;count<=0;local_fault<=0;busy<=0;selected<=0;selected_unit<=0;end
  else begin
   if(cfg_clear||cfg_v||cfg_seal)begin
    if(!cfg_ready)local_fault<=1;
    else if(cfg_clear)begin loaded<=0;used<=0;sealed<=0;count<=0;end
    else if(cfg_v)begin
     if(cfg_index>=N||!cfg_data[0]||cfg_data[85:84]==0||cfg_data[85:84]==3||sealed)local_fault<=1;
     else begin records[cfg_index]<=cfg_data;loaded[cfg_index]<=1;end
    end else if(cfg_seal)begin
     if(!seal_good||sealed)local_fault<=1;
     else begin sealed<=1;count<=cfg_count;end
    end
   end
   if(arm)begin busy<=1;selected<=pick;selected_unit<=records[pick][85:84];end
   if(busy&&issued&&guard_allow)begin busy<=0;used[selected]<=1;end
   if((me_issue&&!me_allow)||(su_issue&&!su_allow))local_fault<=1;
  end
 end
endmodule
