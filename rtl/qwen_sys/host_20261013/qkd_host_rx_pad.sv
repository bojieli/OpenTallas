`timescale 1ns/1ps
// Physical adapter W1024 -> host CDC W546 -> class word W528.
// Full1043 FDI flit is adapter's {valid,data1024,credit10,seq8}. Only DATA
// bits1023:528 are padding. They are checked after capture, never truncated
// silently. Outputs are FDI-clock registered pins to the host's own CDC.
module qkd_host_rx_pad #(parameter integer MUT=0)(
 input wire clk,rst_n,
 input wire in_v,input wire[1023:0]in_d,output reg in_cr,
 output reg out_v,output reg[545:0]out_d,input wire out_cr,
 output reg fault
);
 reg vq,crq;reg[1023:0]dq;
 always @(posedge clk)begin dq<=in_d;out_d<={18'd0,(MUT==1)?dq[527:0]^528'd1:dq[527:0]};end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin vq<=0;crq<=0;in_cr<=0;out_v<=0;fault<=0;end
  else begin
   vq<=in_v;crq<=out_cr;in_cr<=crq;out_v<=vq&&!fault&&dq[1023:528]==0;
   if(vq&&dq[1023:528]!=0)fault<=1;
  end
 end
endmodule
// Both sides use existing credit-bounded registered sources. CDC word546
// contains18 pad bits plus the complete class/header/payload528. These are
// exact constant extensions, not omitted unknown signal bits.
module qkd_host_tx_pad(input wire[545:0]cdc_data,output wire[1023:0]adapter_data);
 assign adapter_data={478'd0,cdc_data};
endmodule
