`timescale 1ns/1ps
// Actual cmd32 adapter. DESC/GO pulse storage and native FIFO reservations
// precede command launch. A retired read window is insufficient alone: old
// writes and transport must also be quiet before replacing its descriptor.
module ot_qfd_native_cmd_provider #(parameter integer ENABLE=0)(
 input wire clk,rst_n,
 input wire desc_v,input wire [18:0] desc_row,input wire [10:0] desc_n,
 input wire go_v,input wire wr_v,input wire [4:0] wr_bank,wr_col,
 input wire window_retired,write_quiet,transport_quiet,
 input wire cmd_credit_return,input wire [2:0] read_release,
 output wire desc_take,go_take,wr_take,
 output wire cmd_v,output wire [31:0] cmd,output wire [2:0] read_credit,
 output reg fault
);
 (* keep *) reg [29:0] dp[0:2];
 (* keep *) reg dv[0:2],gp[0:2];
 (* keep *) reg [3:0] credits[0:2];
 // {go issued, window retired, context live}
 (* keep *) reg [2:0] phase[0:2];
 (* keep *) reg [31:0] cq[0:2];
 (* keep *) reg cv[0:2];
 (* keep *) reg [2:0] rc[0:2];
 wire disagree=(dp[0]!=dp[1])||(dp[0]!=dp[2])||(dv[0]!=dv[1])||(dv[0]!=dv[2])||
   (gp[0]!=gp[1])||(gp[0]!=gp[2])||(credits[0]!=credits[1])||(credits[0]!=credits[2])||
   (phase[0]!=phase[1])||(phase[0]!=phase[2])||(cq[0]!=cq[1])||(cq[0]!=cq[2])||
   (cv[0]!=cv[1])||(cv[0]!=cv[2])||(rc[0]!=rc[1])||(rc[0]!=rc[2]);
 wire context_room=!phase[0][0]||(phase[0][1]&&write_quiet&&transport_quiet&&!wr_v);
 wire desc_bad=desc_v&&(desc_n==0||desc_n>1024);
 wire retire_bad=window_retired&&(!phase[0][0]||!phase[0][2]);
 reg choose;reg [31:0] packet;reg [1:0] kind;
 always @*begin
  choose=0;packet=0;kind=0;
  if(credits[0]!=0)begin
   if(dv[0])begin choose=1;packet={2'd0,dp[0]};kind=0;end
   else if(gp[0])begin choose=1;packet=32'h40000000;kind=1;end
   else if(wr_v&&phase[0][0]&&phase[0][2])begin choose=1;packet={2'd2,20'd0,wr_col,wr_bank};kind=2;end
  end
 end
 wire credit_bad=cmd_credit_return&&credits[0]==8&&!choose;
 wire pre_safe=ENABLE&&!fault&&!disagree&&!desc_bad&&!retire_bad&&!credit_bad;
 wire take_desc=pre_safe&&desc_v&&!dv[0]&&!gp[0]&&context_room;
 wire go_bad=go_v&&(gp[0]||phase[0][2]||(!phase[0][0]&&!take_desc));
 wire safe=pre_safe&&!go_bad;
 assign desc_take=safe&&take_desc;
 assign go_take=safe&&go_v;
 assign wr_take=safe&&choose&&kind==2;
 assign cmd_v=safe&&cv[0];
 assign cmd=cq[0];
 assign read_credit=safe?rc[0]:3'd0;
 reg [2:0] next_phase;reg next_dv,next_gp;integer j;
 always @*begin
  next_phase=phase[0];next_dv=dv[0];next_gp=gp[0];
  if(window_retired)next_phase[1]=1;
  if(choose&&kind==0)next_dv=0;
  if(choose&&kind==1)begin next_gp=0;next_phase[2]=1;end
  if(desc_take)begin next_dv=1;next_phase=3'b001;end
  if(go_take)next_gp=1;
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   fault<=0;
   for(j=0;j<3;j=j+1)begin dp[j]<=0;dv[j]<=0;gp[j]<=0;credits[j]<=8;phase[j]<=0;cq[j]<=0;cv[j]<=0;rc[j]<=0;end
  end else begin
   fault<=fault||(ENABLE&&(disagree||desc_bad||retire_bad||credit_bad||go_bad));
   for(j=0;j<3;j=j+1)begin
    cv[j]<=safe&&choose;rc[j]<=safe?read_release:3'd0;
    if(safe)begin
     if(desc_take)dp[j]<={desc_n,desc_row};
     dv[j]<=next_dv;gp[j]<=next_gp;phase[j]<=next_phase;
     if(choose)cq[j]<=packet;
     case({cmd_credit_return,choose})
      2'b01:credits[j]<=credits[0]-1'b1;
      2'b10:credits[j]<=credits[0]+1'b1;
      default:credits[j]<=credits[0];
     endcase
    end
   end
  end
 end
endmodule
