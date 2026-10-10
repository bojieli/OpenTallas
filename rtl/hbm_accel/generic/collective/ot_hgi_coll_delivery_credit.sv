`timescale 1ns/1ps
`default_nettype none
// Publisher credits are reserved at endpoint selection, before the HUBW wire.
// A return denotes either a filtered padded slot or an acknowledged sink write.
// FIFO storage and acknowledgement routing belong to the publisher, not here.
module ot_hgi_coll_delivery_credit #(
 parameter integer ENABLE=0, DEL=4, CAP=128, MUT=0
)(
 input wire clk,rst_n,
 input wire [DEL-1:0] reserve,credit_return,
 output wire [DEL-1:0] permit,
 output reg fault,
 output wire [DEL*8-1:0] credits
);
 reg [7:0] count[0:DEL-1], inverse[0:DEL-1];
 wire [DEL-1:0] corrupt;
 for(genvar l=0;l<DEL;l=l+1)begin: g_lane
  assign corrupt[l]=((count[l]^inverse[l])!=8'hff)||count[l]>CAP;
  assign permit[l]=ENABLE!=0&&!fault&&!(|corrupt)&&(MUT==1||count[l]!=0);
  assign credits[l*8+:8]=count[l];
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   fault<=0;
   for(integer l=0;l<DEL;l=l+1)begin count[l]<=8'(CAP);inverse[l]<=~8'(CAP);end
  end else if(ENABLE!=0)begin
   if(|corrupt)fault<=1;
   for(integer l=0;l<DEL;l=l+1)begin
    if(reserve[l]&&!permit[l])fault<=1;
    if(credit_return[l]&&count[l]==CAP&&!reserve[l])fault<=1;
    if(!fault&&!corrupt[l])begin
     case({reserve[l],credit_return[l]})
      2'b10:if(count[l]!=0)begin count[l]<=count[l]-8'd1;inverse[l]<=~(count[l]-8'd1);end
      2'b01:if(count[l]<CAP)begin count[l]<=count[l]+8'd1;inverse[l]<=~(count[l]+8'd1);end
      default:;
     endcase
    end
   end
  end
 end
`ifndef SYNTHESIS
 initial if(CAP<1||CAP>255)$fatal(1,"delivery credit CAP range1..255");
`endif
endmodule
`default_nettype wire
