// Default-off functional provider. clk is local control clock. Cross-clock/PHY
// transport and cold-reset generation are explicit EXTERNAL provider obligations.
module ot_hbm_credit_rx #(parameter integer ENABLE=0)(
 input wire clk,rst_n,cold_link_start,input wire [23:0] link_epoch,
 input wire final_retire, output wire final_retire_ready,
 output wire grant_valid,input wire grant_ready,output wire [71:0] grant_word,
 input wire ack_valid,output wire ack_ready,input wire [71:0] ack_word,
 output wire fault
);
 import ot_hbm_credit_secded_pkg::*;
 reg [71:0] control_q,account_q,message_q;
 reg [1:0] healthy_q;
 wire [65:0] c=decode64(control_q),a=decode64(account_q),m=decode64(message_q),k=decode64(ack_word);
 wire clean=!(c[65:64]!=0||a[65:64]!=0||m[65:64]!=0);
 wire active=c[0],busy=c[1],sent=c[2];
 wire [23:0] epoch=c[63:40],seq=c[39:16];
 wire [7:0] debt=a[7:0],pending=a[15:8];
 assign fault=healthy_q!=2'b01;
 assign final_retire_ready=ENABLE&&!fault&&clean&&active&&debt!=0;
 assign grant_valid=ENABLE&&!fault&&clean&&busy&&!sent;
 assign grant_word=message_q;
 assign ack_ready=ENABLE&&!fault&&clean&&active;
 reg [63:0] cn,an,mn;
 reg bad;
 always @* begin
  cn=c[63:0];an=a[63:0];mn=m[63:0];bad=0;
  if(cold_link_start)begin
   if(active)bad=1;
   else begin cn={link_epoch,24'b0,16'h0003};an=64'd64;mn={8'h47,link_epoch,24'b0,8'd64};end
  end else if(active)begin
   if(final_retire&&final_retire_ready)begin
    if(debt==0||pending==64)bad=1;
    else begin an[7:0]=debt-1'b1;an[15:8]=pending+1'b1;end
   end
   if(grant_valid&&grant_ready)cn[2]=1;
   if(ack_valid&&ack_ready)begin
    if(k[65])bad=1;
    else if(k[63:56]!=8'h41)bad=1;
    else if(k[55:32]!=epoch)begin end // stale generation discarded
    else if(k[31:8]<seq)begin end // old ACK does not mint tokens
    else if(k[31:8]!=seq||k[7:0]!=m[7:0])bad=1;
    else if(!busy)begin end
    else if(!sent)bad=1;
    else begin cn[1]=0;cn[2]=0;end
   end
   // A fresh message is scheduled only after the previous transaction completes.
   if(!busy&&an[15:8]!=0)begin
    if(seq==24'hffffff||({1'b0,an[7:0]}+{1'b0,an[15:8]})>64)bad=1;
    else begin
     cn[39:16]=seq+1'b1;cn[1]=1;cn[2]=0;
     mn={8'h47,epoch,seq+24'd1,an[15:8]};
     an[7:0]=an[7:0]+an[15:8];an[15:8]=0;
    end
   end
  end else if(final_retire||ack_valid)bad=1;
  if(c[15:3]!=0||a[63:16]!=0||debt>64||pending>64||({1'b0,debt}+{1'b0,pending})!= (active?64:0))bad=1;
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin control_q<=encode64(0);account_q<=encode64(0);message_q<=encode64(0);healthy_q<=2'b01;end
  else if(ENABLE&&!fault)begin
   if(c[65]||a[65]||m[65])healthy_q<=2'b10;
   else if(!clean)begin control_q<=encode64(c[63:0]);account_q<=encode64(a[63:0]);message_q<=encode64(m[63:0]);end
   else if(bad)healthy_q<=2'b10;
   else begin control_q<=encode64(cn);account_q<=encode64(an);message_q<=encode64(mn);end
  end
 end
endmodule
