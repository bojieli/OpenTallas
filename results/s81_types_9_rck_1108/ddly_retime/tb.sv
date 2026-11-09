`timescale 1ns/1ps
module tb;
reg clk=0;always #0.4165 clk=~clk;
reg rst=0;reg [543:0] d=0;wire [543:0] a,b;
ot_s81_kp4_ddly #(.DD(58),.RQ(0)) old(clk,rst,d,a);
ot_s81_kp4_ddly_new #(.DD(58),.RQ(1)) newform(clk,rst,d,b);
integer c,j,checks=0,err=0;
initial begin
for(c=0;c<2500;c=c+1)begin
 @(negedge clk);rst=(c%233>=7);for(j=0;j<17;j=j+1)d[j*32+:32]=$urandom;
 @(posedge clk);#0.001;
 if(c%233>75)begin checks++;if(a!==b)err++;end
end
$display("DDLY_RQ checks=%0d errors=%0d",checks,err);if(err)$fatal(1,"DDLY_RQ FAILED");$finish;
end
endmodule
