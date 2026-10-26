`timescale 1ns/1ps
module tb_bank;
 reg clk=0; always #5 clk=~clk;
 reg [1:0] s; reg[2:0] g; reg[17:0] t; reg[15:0] e;
 wire[17:0] a,b; wire[15:0] c,d;
 kv_pc_r8_position_bank dut(clk,s,g,t,e,a,c);
 kv_pc_r8_position_bank #(.MUT(1)) mutant(clk,s,g,t,e,b,d);
 reg[17:0] r1,r2; reg[15:0] er;
 integer i,j,k,bad=0,mut=0,total=0;
 initial begin
  s=0;g=0;t=0;e=0;r1=0;r2=0;er=0;
  for(i=0;i<4;i=i+1) for(j=0;j<8;j=j+1) begin
   @(negedge clk);s=2'(i);g=3'(j);
   for(k=0;k<100;k=k+1) begin
    t=18'($urandom);e=16'($urandom);
    @(posedge clk);r2=r1;r1=t;er=e;
    #1;
    if(k>2) begin
     total=total+1;
     if(a !== ((i==3 && (j==2||j==3||j==4||j==6))?r2:t) || c !== ((i==2&&j==1)?er:e)) bad=bad+1;
     if(a !== b || c !== d) mut=mut+1;
    end
    @(negedge clk);
   end
  end
  $display("BANK exact compared=%0d differences=%0d mutant_caught=%0d",total,bad,mut);
  if(bad || !mut) $fatal(1,"bank proof failed");
  $finish;
 end
endmodule
