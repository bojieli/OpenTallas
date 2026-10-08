// External source counterpart: reservation must precede physical data launch.
// No context/operation rearm input. Provider resets BOTH ends and all transport.
module ot_hbm_credit_source #(parameter integer ENABLE=0)(
 input wire clk,rst_n,cold_link_start,input wire [23:0] link_epoch,
 input wire reserve_valid,output wire reserve_ready,
 input wire grant_valid,output wire grant_ready,input wire [71:0] grant_word,
 output wire ack_valid,input wire ack_ready,output wire [71:0] ack_word,
 output wire fault
);
 import ot_hbm_credit_secded_pkg::*;
 reg [71:0] control_q,account_q,message_q;
 reg [1:0] healthy_q;
 wire [65:0] c=decode64(control_q),a=decode64(account_q),m=decode64(message_q),g=decode64(grant_word);
 wire clean=!(c[65:64]!=0||a[65:64]!=0||m[65:64]!=0);
 wire active=c[0],busy=c[1],seen=c[2],armed=c[3];
 wire [23:0] epoch=c[63:40],seq=c[39:16];
 wire [7:0] available=a[7:0];
 assign fault=healthy_q!=2'b01;
 assign grant_ready=ENABLE&&!fault&&clean&&active&&!busy;
 assign ack_valid=ENABLE&&!fault&&clean&&busy;
 assign ack_word=message_q;
 // No combinational grant-to-launch path, and initial ACK must leave first.
 assign reserve_ready=ENABLE&&!fault&&clean&&active&&armed&&available!=0;
 reg [63:0] cn,an,mn;
 reg bad;
 always @* begin
  cn=c[63:0];an=a[63:0];mn=m[63:0];bad=0;
  if(cold_link_start)begin
   if(active)bad=1;
   else begin cn={link_epoch,24'b0,16'h0001};an=0;mn=0;end
  end else if(active)begin
   if(reserve_valid&&reserve_ready)an[7:0]=available-1'b1;
   if(ack_valid&&ack_ready)begin cn[1]=0;cn[3]=1;end
   if(grant_valid&&grant_ready)begin
    if(g[65]||g[63:56]!=8'h47)bad=1;
    else if(g[55:32]!=epoch)begin end
    else if(seen&&g[31:8]==seq)begin
     if(g[7:0]!=m[7:0])bad=1; // full previous tuple required
     else cn[1]=1; // duplicate reACK, never add credit
    end else if(seen&&g[31:8]<seq)begin end
    else if((!seen&&(g[31:8]!=0||g[7:0]!=64)) ||
      (seen&&(seq==24'hffffff||g[31:8]!=seq+24'd1)) ||
      g[7:0]==0||g[7:0]>64||({1'b0,an[7:0]}+{1'b0,g[7:0]})>64)bad=1;
    else begin
     an[7:0]=an[7:0]+g[7:0];cn[39:16]=g[31:8];cn[1]=1;cn[2]=1;
     mn={8'h41,epoch,g[31:8],g[7:0]};
    end
   end
  end
  if(c[15:4]!=0||a[63:8]!=0||available>64)bad=1;
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
