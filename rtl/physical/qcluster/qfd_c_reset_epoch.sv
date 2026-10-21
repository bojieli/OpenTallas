`timescale 1ns/1ps
`default_nettype none
// Unbound SAFE-QW-CB16 reset-padding candidate. Static release epoch, no delay
// array, no functional-data masking. RELEASE is the total source-pin->release
// capture count including the two face stages. Assertion cancels the epoch
// within3 clocks; its timing intentionally differs from a long shift register.
// Adoption requires the parent's canceled-reset contract and MUT8 replay.
module qfd_c_reset_epoch #(
 parameter integer RELEASE=36,
 parameter integer MUT=0,
 parameter integer N=RELEASE+MUT,
 parameter integer CW=(N<=3)?1:$clog2(N-2)
)(input wire ck,rst_n,output wire rst_o);
 (* keep = 1 *) reg rst_l0,rst_l1;
 always@(posedge ck)begin rst_l0<=rst_n;rst_l1<=rst_l0;end
 generate if(N==2)begin:g_two
  assign rst_o=rst_l1;
 end else begin:g_count
  reg[CW-1:0]age;
  reg released;
  always@(posedge ck)begin
   if(!rst_l1)begin age<=0;released<=0;end
   else if(!released)begin
    if(age==N-3)released<=1;
    else age<=age+1'b1;
   end
  end
  assign rst_o=released;
 end endgenerate
`ifndef SYNTHESIS
 initial if(RELEASE<2||N<2)$fatal(1,"reset epoch requires two face stages");
`endif
endmodule
`default_nettype wire
