`timescale 1ns/1ps
// QM returns a count of freed host-FIFO entries, sometimes several at once.
// Terminate that count in its OWN clk_h domain. The dedicated CDC output face
// promises four slots; exactly one reserved-slot credit can return per cycle.
// No binary count bus crosses clocks and capacity never means write commit.
module qkd_host_qm_credit_pacer #(parameter integer MUT=0)(
 input wire clk_h,rst_n,in_v,input wire[4:0]in_crn,
 output reg out_cr,output reg fault
);
 reg vq;reg[4:0]cq;reg[3:0]owed,pending;
 wire pulse=!fault&&pending!=0;
 wire[5:0]next_pending={2'd0,pending}+{1'b0,cq}-6'(pulse);
 wire[5:0]next_owed={2'd0,owed}+6'(vq)-{1'b0,cq};
 always @(posedge clk_h or negedge rst_n)begin
  if(!rst_n)begin vq<=0;cq<=0;owed<=0;pending<=0;out_cr<=0;fault<=0;end
  else begin
   vq<=in_v;cq<=in_crn;out_cr<=pulse;
   if((cq>{1'b0,owed}+5'(vq))||next_pending>4||next_owed>4)fault<=1;
   else begin owed<=next_owed[3:0];pending<=next_pending[3:0];end
   if(MUT==1)out_cr<=!fault&&cq!=0; // loses all but one of batched returns
  end
 end
endmodule
