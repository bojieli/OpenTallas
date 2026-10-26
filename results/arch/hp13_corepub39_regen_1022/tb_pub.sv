`timescale 1ns/1ps
module tb_pub;
 parameter integer STAGES=1;
 parameter integer MUT=0;
 reg ck_core=0,ck_hr=0,rst_core=0;
 initial begin #21;rst_core=1;end
 always #5 ck_core=~ck_core;
 initial begin #3;forever #7 ck_hr=~ck_hr;end
 reg[38:0]src_d=0;
 wire[38:0]out;
 hp13_pub_component #(.MUT(MUT)) dut(.*);
 reg[38:0] expected[0:3];
 integer cycle=0,k;
 initial begin for(k=0;k<4;k=k+1)expected[k]=0;end
 always @(negedge ck_core) begin
   cycle=cycle+1;
   if(cycle<42) src_d=39'b1 << (cycle%39);
   else src_d={7'(cycle),16'(cycle*31+7),16'(cycle*119+3)};
 end
 always @(posedge ck_core) begin
   for(k=3;k>0;k=k-1)expected[k]=expected[k-1];
   expected[0]=src_d;
   #1;
   if(cycle>8 && out!==expected[STAGES])$fatal(1,"PUB_FAIL stage=%0d cycle=%0d out=%h expected=%h",STAGES,cycle,out,expected[STAGES]);
   if(cycle==600)begin $display("PUB_PASS stages=%0d tuples=596 bits=39 independent_HR_phase=3_period14 core_period10",STAGES);$finish;end
 end
endmodule
