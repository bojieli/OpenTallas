`timescale 1ns/1ps
// One outstanding beat station for the actual host endpoint (not a generic
// arbitrary AXI fabric). Receiver must capture a held request exactly once.
// External inputs are sampled before channel logic; outputs are pin flops.
// WAIT_DROP prevents delayed ready from causing the same request to recapture.
module qkd_host_pin_channel #(parameter W=1, IN_PIN=1, OUT_PIN=1)(
 input wire ck,rst_n,input wire in_v,input wire[W-1:0]in_d,output reg in_r,
 output reg out_v,output reg[W-1:0]out_d,input wire out_r
);
 reg iv_q,or_q;reg[W-1:0]id_q;reg[1:0]state;
 wire iv=IN_PIN?iv_q:in_v;
 wire[W-1:0]id=IN_PIN?id_q:in_d;
 wire ack=OUT_PIN?or_q:out_r;
 always @(posedge ck or negedge rst_n)if(!rst_n)begin iv_q<=0;or_q<=0;id_q<=0;end
 else begin iv_q<=in_v;id_q<=in_d;or_q<=out_r;end
 always @(posedge ck or negedge rst_n)if(!rst_n)begin state<=0;in_r<=0;out_v<=0;out_d<=0;end
 else begin
  in_r<=0;
  case(state)
   0:if(iv)begin out_v<=1;out_d<=id;state<=1;end
   1:if(ack)begin out_v<=0;in_r<=1;state<=2;end
   2:if(!iv)state<=0;
   default:state<=0;
  endcase
 end
endmodule
