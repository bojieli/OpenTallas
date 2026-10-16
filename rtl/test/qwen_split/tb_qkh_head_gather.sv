`timescale 1ns/1ps
module tb_qkh_head_gather;
 parameter integer MUT=0;
 reg ck=0;always #0.5 ck=~ck;
 reg[1558:0] a=0;reg[15:0] e=0;
 wire[1558:0] b;wire[15:0] f;
 reg[1574:0] expected=0;
 integer cycle,bitno,checks=0;
 qkh_head_gather_stage #(.MUT(MUT)) dut(ck,a,e,b,f);
 always @(posedge ck)expected<={e,a};
 initial begin
  for(cycle=0;cycle<1800;cycle=cycle+1)begin
   @(negedge ck);
   // Check after input has changed, so a bypass cannot hide at the clock edge.
   a=0;e=0;
   if(cycle%1575<1559)a[cycle%1575]=1;
   else e[cycle%1575-1559]=1;
   for(bitno=0;bitno<1559;bitno=bitno+1)
    if((bitno+cycle*7)%67==0)a[bitno]=~a[bitno];
   e=e^16'(cycle*19);
   #0.1;
   if(cycle>1)begin
    checks=checks+1;
    if({f,b}!==expected)begin
     $display("GATHER_FAIL mutant=%0d cycle=%0d",MUT,cycle);$fatal(1);
    end
   end
  end
  $display("GATHER_PASS bits=1575 latency=1 checks=%0d mutant=%0d",checks,MUT);$finish;
 end
endmodule
