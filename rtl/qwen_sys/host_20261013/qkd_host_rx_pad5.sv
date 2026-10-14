`timescale 1ns/1ps
// Actual PINREG1 adapter starts with FIVE receive credits. A five-word elastic
// queue backs that promise independently of downstream W546 CDC IBUF4.
// Full1024 capture precedes padding validation; all528 class/payload bits remain.
// A source credit returns when a queued word reserves one of four CDC slots.
// Queue capacity credits are distinct from HBM commit/completion.
module qkd_host_rx_pad5 #(parameter integer MUT=0)(
 input wire clk,rst_n,input wire in_v,input wire[1023:0]in_d,output reg in_cr,
 output reg out_v,output reg[545:0]out_d,input wire out_cr,output reg fault
);
 reg vq,crq;reg[1023:0]dq;
 reg[527:0]q[0:4];reg[2:0]wp,rp,count,credits;
 wire pop=!fault&&count!=0&&credits!=0;
 wire padding_ok=dq[1023:528]==0;
 wire take=vq&&!fault&&padding_ok&&(count<5||pop);
 always @(posedge clk)begin
  dq<=in_d;
  if(take)q[wp]<=dq[527:0];
  if(pop)out_d<={18'd0,q[rp]^((MUT==1)?528'd1:528'd0)};
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin vq<=0;crq<=0;wp<=0;rp<=0;count<=0;credits<=4;in_cr<=0;out_v<=0;fault<=0;end
  else begin
   vq<=in_v;crq<=out_cr;in_cr<=pop;out_v<=pop;
   if(vq&&(!padding_ok||(count==5&&!pop)))fault<=1;
   if(crq&&credits==4&&!pop)fault<=1;
   else credits<=credits+3'(crq)-3'(pop);
   if(take)wp<=wp==4?3'd0:wp+1'b1;
   if(pop)rp<=rp==4?3'd0:rp+1'b1;
   case({take,pop})2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:;endcase
  end
 end
endmodule
