`timescale 1ns/1ps
`default_nettype none
module dsfd_vm_xio_serial(
 input wire ck,rst_n,input wire qo_v,qf,gf,input wire[2:0]qSWs,output reg fault
);
 reg[1:0]rq;reg[2:0]qs_q;
 always @(posedge ck or negedge rst_n)if(!rst_n)rq<=0;else rq<={rq[0],1'b1};
 always @(posedge ck)begin
  qs_q<=qSWs;
  if(!rq[1])fault<=0;else if((qo_v&&!(qs_q[0]&&qs_q[1]))||qf||gf)fault<=1;
 end
endmodule
`default_nettype wire
