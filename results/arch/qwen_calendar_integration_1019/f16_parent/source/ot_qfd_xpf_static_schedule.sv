`timescale 1ns/1ps
// Static-cycle production control: never gates or delays either producer.
// Load source-bound records before stage start, seal, then launch each arm
// at its compiled cycle. An incomplete table, wrong issue PC/cycle, missed
// arm, or overlapping start faults. cfg record188 LSB:
// {xpf72,producer_pc12,unit2,stage6,arm_cycle32,issue_cycle32,first_write_cycle32}.
// arm_cycle0 is the first active edge AFTER start is accepted; xpf leaves
// registered pins on that edge. ARM_TRANSPORT_EDGES is the assigned die
// pipeline from those pins to the tap. No credits, ready or issue permission.
module ot_qfd_xpf_static_schedule #(
 parameter integer N=8, ARM_TRANSPORT_EDGES=0, MUT_LATE=0,
 parameter integer IW=(N<2)?1:$clog2(N)
)(
 input wire clk,rst_n,
 input wire cfg_v,input wire [IW-1:0] cfg_index,input wire [187:0] cfg_data,
 input wire cfg_clear,cfg_seal,input wire [IW:0] cfg_count,
 input wire start,stop,input wire [5:0] stage,
 input wire me_issue,input wire [11:0] me_pc,
 input wire su_issue,input wire [11:0] su_pc,
 input wire cp_issue,input wire [11:0] cp_pc,
 output wire image_ready,output reg [71:0] xpf,output reg fault,output reg active,output reg [31:0] cycle
);
 reg [187:0] records[0:N-1];reg [N-1:0] loaded,armed,issued;
 assign image_ready=sealed&&!fault;
 reg sealed;reg [IW:0] count;reg [5:0] stage_r;
 reg good,have_arm;reg [IW-1:0] arm_pick;integer i,j;
 always @* begin
  good=cfg_count!=0&&cfg_count<=N;
  for(i=0;i<N;i=i+1)if(i<cfg_count)begin
   if(!loaded[i]||records[i][187:156]<records[i][123:92]+ARM_TRANSPORT_EDGES+3)good=0;
   for(j=0;j<i;j=j+1)
    if(records[i][91:72]==records[j][91:72]||
       (records[i][91:86]==records[j][91:86]&&records[i][123:92]==records[j][123:92]))good=0;
  end
  have_arm=0;arm_pick=0;
  for(i=N-1;i>=0;i=i-1)
   if(active&&i<count&&records[i][91:86]==stage_r&&
      cycle==records[i][123:92]+(MUT_LATE!=0?32'd4:32'd0))begin have_arm=1;arm_pick=i;end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin loaded<=0;armed<=0;issued<=0;sealed<=0;active<=0;count<=0;cycle<=0;stage_r<=0;xpf<=0;fault<=0;end
  else begin
   xpf[0]<=0;
   if(cfg_v||cfg_clear||cfg_seal)begin
    if(active)fault<=1;
    else if(cfg_clear)begin loaded<=0;sealed<=0;count<=0;end
    else if(cfg_v)begin
     if(sealed||cfg_index>=N||!cfg_data[0]||cfg_data[85:84]==0)fault<=1;
     else begin records[cfg_index]<=cfg_data;loaded[cfg_index]<=1;end
    end else if(!good||sealed)fault<=1;
    else begin sealed<=1;count<=cfg_count;end
   end
   if(start)begin
    if(active||!sealed||records[0][91:86]!=stage)fault<=1;
    else begin active<=1;cycle<=0;stage_r<=stage;armed<=0;issued<=0;end
   end
   if(active)begin
    cycle<=cycle+1'b1;
    if(have_arm)begin xpf<=records[arm_pick][71:0];armed[arm_pick]<=1;end
    for(i=0;i<N;i=i+1)if(i<count&&records[i][91:86]==stage_r)begin
     if(cycle>records[i][123:92]&&!armed[i])fault<=1;
     if(cycle==records[i][155:124])begin
      if((records[i][85:84]==1&&(!me_issue||me_pc!=records[i][83:72]))||
         (records[i][85:84]==2&&(!su_issue||su_pc!=records[i][83:72]))||
         (records[i][85:84]==3&&(!cp_issue||cp_pc!=records[i][83:72])))fault<=1;
      else issued[i]<=1;
     end
     if(cycle==records[i][187:156]&&!armed[i])fault<=1;
    end
   end
   // Any monitored producer PC issued at a different cycle is a defect.
   if(me_issue||su_issue||cp_issue)begin
    if(!active)fault<=1;
    for(i=0;i<N;i=i+1)if(i<count&&records[i][91:86]==stage_r&&
       ((me_issue&&records[i][85:84]==1&&me_pc==records[i][83:72])||
        (su_issue&&records[i][85:84]==2&&su_pc==records[i][83:72])||
        (cp_issue&&records[i][85:84]==3&&cp_pc==records[i][83:72])))begin
     if(cycle!=records[i][155:124]||issued[i])fault<=1;
    end
   end
   if(stop)begin
    if(!active)fault<=1;
    for(i=0;i<N;i=i+1)if(i<count&&records[i][91:86]==stage_r&&(!armed[i]||!issued[i]))fault<=1;
    active<=0;
   end
  end
 end
endmodule
