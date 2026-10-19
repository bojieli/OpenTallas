`timescale 1ns/1ps
module tb_ring;
 reg ck=0,rst=0;always #5 ck=~ck;
 reg[31:0] d=32'h1;
 wire[31:0] q3,q6,q9,q12;
 qfd_dv_ring_delay #(.D(3)) u3(ck,rst,d,q3);
 qfd_dv_ring_delay #(.D(6)) u6(ck,rst,d,q6);
 qfd_dv_ring_delay #(.D(9)) u9(ck,rst,d,q9);
 qfd_dv_ring_delay #(.D(12)) u12(ck,rst,d,q12);
 reg[31:0] h[0:11];integer age=0,cycle=0;
 always @(negedge ck) begin
  d=(d^(d<<13));d=(d^(d>>17));d=(d^(d<<5));
  rst=!(cycle<6||(cycle>=700&&cycle<706));
 end
 always @(posedge ck) begin
  cycle=cycle+1;
  if(!rst) age=0;else age=age+1;
  for(integer i=11;i>0;i=i-1) h[i]<=h[i-1];h[0]<=d;
  #1;
  if(age>=64) begin
   if(q3!==h[2]||q6!==h[5]||q9!==h[8]||q12!==h[11])
    $fatal(1,"RING_DELAY_MISMATCH cycle%0d got%h/%h/%h/%h expected%h/%h/%h/%h",cycle,q3,q6,q9,q12,h[2],h[5],h[8],h[11]);
  end
  if(cycle==1500) begin $display("SAFE_RING_DELAY PASS D3/6/9/12 W32 cycles1500 resets2");$finish;end
 end
endmodule
