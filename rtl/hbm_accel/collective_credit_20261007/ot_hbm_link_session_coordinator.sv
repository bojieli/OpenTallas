// Always-on source controller. Management channels must survive data resets.
module ot_hbm_link_session_coordinator #(parameter integer ENABLE=0)(
 input wire clk,por,input wire restart_valid,output wire restart_ready,
 output wire [1:0] command_valid,input wire [1:0] command_ready,
 output wire [71:0] command_word,
 input wire [1:0] ack_valid,output wire [1:0] ack_ready,
 input wire [143:0] ack_word,
 output wire running,output wire fault
);
 import ot_hbm_credit_secded_pkg::*;
 reg [71:0] state_q;reg [1:0] healthy_q;
 wire[65:0] s=decode64(state_q),a0=decode64(ack_word[71:0]),a1=decode64(ack_word[143:72]);
 wire[23:0] epoch=s[63:40],seq=s[39:16];wire[7:0] phase=s[15:8];
 wire clean=s[65:64]==0;
 assign fault=healthy_q!=2'b01;
 wire live=(ENABLE!=0)&&!fault&&clean;
 assign running=live&&phase==5&&s[3:0]==15;
 assign restart_ready=running;
 assign command_valid={2{live}}&~s[1:0];
 assign command_word=encode64({phase,epoch,seq,8'hc3});
 assign ack_ready={2{live}}&s[1:0]&~s[3:2];
 reg[63:0] n;reg bad;integer k;reg[65:0] a;
 always @*begin
  n=s[63:0];bad=0;a=0;
  for(k=0;k<2;k=k+1)begin
   if(command_valid[k]&&command_ready[k])n[k]=1;
   a=k==0?a0:a1;
   if(ack_valid[k]&&ack_ready[k])begin
    if(a[65]||a[63:0]!={phase|8'h80,epoch,seq,8'hac})bad=1;
    else n[k+2]=1;
   end
  end
  if(s[3:0]==15&&(phase!=5||restart_valid))begin
   if(seq==24'hffffff||(phase==2&&epoch==24'hffffff))bad=1;
   else begin
    n[39:16]=seq+1'b1;n[7:0]=0;
    n[15:8]=phase==5?8'd1:phase+8'd1;
    if(phase==2)n[63:40]=epoch+1'b1;
   end
  end
  if(s[7:4]!=0||phase<1||phase>5)bad=1;
 end
 always @(posedge clk or posedge por)begin
  if(por)begin state_q<=encode64(64'h0000000000000100);healthy_q<=2'b01;end
  else if(ENABLE!=0&&!fault)begin
   if(s[65])healthy_q<=2'b10;
   else if(s[64])state_q<=encode64(s[63:0]);
   else if(bad)healthy_q<=2'b10;
   else state_q<=encode64(n);
  end
 end
endmodule
