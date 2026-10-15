`timescale 1ns/1fs
// One physical branch register, no scheduling/flow-control decisions. Each
// instance has its own measured clock entry. Reset deassertion takes one local
// edge; the compiler starts traffic after the declared reset guard.
module qkd_static_kv_hop #(parameter integer W=38,MUT=0)(
 input wire ck,rst_n,input wire [W-1:0] a,output reg [W-1:0] b);
 (* keep *) reg rn;
 always @(posedge ck or negedge rst_n)if(!rst_n)rn<=0;else rn<=1;
 always @(posedge ck or negedge rn)
  if(!rn)b<=0;
  else b<=MUT!=0 ? a^{{(W-2){1'b0}},2'b10} : a;
endmodule
module qkd_static_kv_hop38 #(parameter integer MUT=0)(
 input wire ck,rst_n,input wire[37:0]a,output wire[37:0]b);
 qkd_static_kv_hop #(.W(38),.MUT(MUT))u(.*);
endmodule
module qkd_static_kv_hop295 #(parameter integer MUT=0)(
 input wire ck,rst_n,input wire[294:0]a,output wire[294:0]b);
 qkd_static_kv_hop #(.W(295),.MUT(MUT))u(.*);
endmodule
