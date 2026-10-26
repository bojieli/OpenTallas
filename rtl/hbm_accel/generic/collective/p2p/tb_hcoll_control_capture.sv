`timescale 1ns/1ps
module tb_hcoll_control_capture;
 reg clk=0; reg [511:0] data=0; wire [511:0] pin_data;
 ot_hgi_coll_control256_capture dut(.*);
 reg [511:0] want; integer n,b; reg [31:0] prng=32'h39c41a5d;
 initial begin
  for(n=0;n<520;n=n+1)begin
   clk=0;
   for(b=0;b<16;b=b+1)begin
    prng=prng^(prng<<13); prng=prng^(prng>>17); prng=prng^(prng<<5);
    data[b*32+:32]=prng;
   end
   if(n<512)begin data=0;data[n]=1;end
   want=data; #0.2; clk=1; #0.1;
   if(pin_data!==want)$fatal(1,"CAPTURE mismatch vector=%0d",n);
   // Input changes after the edge must not leak through a registered face.
   data=~data; #0.2;
   if(pin_data!==want)$fatal(1,"CAPTURE combinational leak vector=%0d",n);
   clk=0; #0.333;
  end
  $display("PASS CONTROL_CAPTURE vectors=520 bit_checks=532480");$finish;
 end
endmodule
