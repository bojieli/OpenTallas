// Stable encoded epoch mailbox, held request, one protected pulse per local reset.
// Epoch must settle before request (session RELEASE precedes START).
module ot_hbm_link_start_adapter(
 input wire clk,rst_n,input wire request,input wire [71:0] epoch_word,
 output wire cold_start,output wire [23:0] epoch,output wire seen,output wire fault
);
 import ot_hbm_credit_secded_pkg::*;
 (* ASYNC_REG="TRUE" *) reg[1:0] req1,req2;
 reg[1:0] seen_q,pulse_q;reg[71:0] epoch_q;
 wire[65:0] incoming=decode64(epoch_word),stored=decode64(epoch_q);
 assign fault=(seen_q!=2'b01&&seen_q!=2'b10)||(pulse_q!=2'b01&&pulse_q!=2'b10)||stored[65];
 assign cold_start=pulse_q==2'b10&&!fault&&stored[65:64]==0;
 assign epoch=stored[23:0];assign seen=seen_q==2'b10&&!fault;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin req1<=1;req2<=1;seen_q<=1;pulse_q<=1;epoch_q<=encode64(0);end
  else begin
   req1<={request,!request};req2<=req1;
   if(!fault)begin
    pulse_q<=1;
    if(stored[64])epoch_q<=encode64(stored[63:0]);
    else if(req2==2'b10&&seen_q==2'b01)begin
     if(!incoming[65]&&incoming[63:24]==0)begin
      epoch_q<=encode64(incoming[63:0]);seen_q<=2;pulse_q<=2;
     end
    end
   end
  end
 end
endmodule
