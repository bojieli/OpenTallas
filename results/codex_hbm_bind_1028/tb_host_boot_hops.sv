`timescale 1ns/1ps
`ifndef BOOT_HOPS
`define BOOT_HOPS 20
`endif
module tb;
 localparam integer N=`BOOT_HOPS;
`ifdef MUTANT_DELAY
 localparam integer M=N-1;
`else
 localparam integer M=N;
`endif
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg [319:0] d=0;
 wire [319:0] w[0:M];assign w[0]=d;
 for(genvar i=0;i<M;i=i+1)begin:g
  ot_hnx_host_boot_hop u(.clk(clk),.rst_n(rst_n),.d(w[i]),.q(w[i+1]));
 end
 reg[319:0] reference[0:N-1];reg[319:0] consumer,expected_consumer;
 integer checked=0;
 always @(posedge clk)begin
  reference[0]<=d;
  if(!rst_n)begin reference[0][319]<=0;reference[0][42]<=0;reference[0][0]<=0;end
  for(integer j=1;j<N;j=j+1)begin
   reference[j]<=reference[j-1];
   if(!rst_n)begin reference[j][319]<=0;reference[j][42]<=0;reference[j][0]<=0;end
  end
  consumer<=w[M];expected_consumer<=reference[N-1];
 end
 initial begin
  for(integer c=0;c<340;c=c+1)begin
   @(negedge clk);
   rst_n=(c>=3)&&!(c>=160&&c<164);
   for(integer k=0;k<10;k=k+1)d[k*32+:32]=$random;
   d[319]=(c%5==0);d[42]=(c%7==0);d[0]=(c%11==0);
   @(posedge clk);#1;
   if(c>N+1)begin
    if(w[M]!==reference[N-1])$fatal(1,"HOST_BOOT payload/valid alignment c=%0d",c);
    if(consumer!==expected_consumer)$fatal(1,"HOST_BOOT next-edge consumer c=%0d",c);
    checked=checked+1;
   end
  end
  $display("HOST_BOOT PASS hops=%0d consumer=%0d checks=%0d bits=320 reset_valid=3 token_cycles=0",N,N+1,checked);$finish;
 end
endmodule
