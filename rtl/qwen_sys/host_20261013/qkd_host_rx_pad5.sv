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
 reg vq,crq;(* keep = 1 *) reg[1023:0]dq;
 reg[527:0]q[0:4];reg[2:0]wp,rp,count,credits;
 wire pop=!fault&&count!=0&&credits!=0;
 // Capture the padding predicate in parallel with the data, rather than put
 // a 496-bit reduction on the queue write-enable path. No extra data stage.
 reg [30:0] padding_zero_q;
 for(genvar g=0;g<31;g=g+1)begin: g_padding
  always @(posedge clk)padding_zero_q[g] <= in_d[528+16*g+:16]==0;
 end
 wire padding_ok=&padding_zero_q;
 // Registered per-bank pending enables predict the write pointer AFTER the
 // current take. This removes binary pointer decode from each 528-bit bank.
 reg [4:0] wp_hot,put_q;
 wire [4:0] wp_hot_next=take?{wp_hot[3:0],wp_hot[4]}:wp_hot;
 wire take=vq&&!fault&&padding_ok&&(count<5||pop);
 always @(posedge clk)begin
  dq<=in_d;
  for(integer k=0;k<5;k=k+1)
   if(put_q[k]&&!fault&&padding_ok&&(count<5||pop))q[k]<=dq[527:0];
  if(pop)out_d<={18'd0,q[rp]^((MUT==1)?528'd1:528'd0)};
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin wp_hot<=5'b00001;put_q<=0;end
  else begin wp_hot<=wp_hot_next;put_q<={5{in_v}}&wp_hot_next;end
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
