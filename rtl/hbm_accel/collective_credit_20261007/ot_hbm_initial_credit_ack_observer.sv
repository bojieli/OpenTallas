// Actual ACK handshake observation, in that endpoint's ACK clock domain.
// Reset with that credit endpoint. All ports in a session must report seen.
module ot_hbm_initial_credit_ack_observer #(parameter integer ENABLE=0)(
 input wire clk,rst_n,input wire[23:0]epoch,
 input wire ack_valid,ack_ready,input wire[71:0]ack_word,
 output wire seen,output wire fault
);
 import ot_hbm_credit_secded_pkg::*;
 reg[71:0] state_q;reg[1:0]healthy_q;
 wire[65:0]s=decode64(state_q),a=decode64(ack_word);
 assign fault=healthy_q!=2'b01||s[65];
 assign seen=ENABLE!=0&&!fault&&s[65:64]==0&&s[0];
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin state_q<=encode64(0);healthy_q<=1;end
  else if(ENABLE!=0&&healthy_q==2'b01)begin
   if(s[65])healthy_q<=2;
   else if(s[63:1]!=0)healthy_q<=2;
   else if(s[64])state_q<=encode64(s[63:0]);
   // CE scrub coincident with event cannot lose the only initial ACK.
   if(!s[65]&&ack_valid&&ack_ready)begin
    if(a[65])healthy_q<=2;
    else if(a[63:0]=={8'h41,epoch,24'd0,8'd64})state_q<=encode64(64'd1);
   end
  end
 end
endmodule
