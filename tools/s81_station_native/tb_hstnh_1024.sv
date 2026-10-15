`timescale 1ns/1ps
module tb;
 reg ck=0;always #5 ck=~ck;
 reg [1023:0] di=0;wire [1023:0] dq;
 dsfd_hstnh_1024 dut(.ck(ck),.di(di),.dq(dq));
 integer n,j; reg [31:0] rng=32'h12345678;reg [1023:0] previous;reg valid=0;
 initial begin
  for(n=0;n<20000;n=n+1)begin
   @(negedge ck);#1;
   for(j=0;j<32;j=j+1)begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);di[j*32+:32]=rng;end
   if(n<1024)di=1024'd1<<n;
   #1;if(valid && dq!==previous)$fatal(1,"STATION FAIL captured wrong clock edge n=%0d",n);
   @(posedge ck);#1;
   if(dq!==di)$fatal(1,"STATION FAIL payload n=%0d",n);
   previous=di;valid=1;
  end
  $display("STATION PASS 20000 words 20480000 bits top_posedge");$finish;
 end
endmodule
