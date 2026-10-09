`timescale 1ns/1ps
module tb_qfd_pc_head_owner;
 reg clk=0;always#5 clk=~clk;reg rst_n=0,in_v=0;reg[303:0]in_payload=0;
 reg[2:0]ack_v=0;reg[212:0]ack_data=0;
 wire head_v,credit_return,fault,ce;wire[303:0]head_payload;wire[63:0]head_id;
 ot_qfd_pc_head_owner #(.ENABLE(1)) dut(.*);
 integer credits=0,corrections=0;reg monitor=1;
 always@(posedge clk)if(rst_n&&monitor)begin
  if(fault)$fatal(1,"unexpected PC owner fault");
  if(credit_return)credits=credits+1;
  if(ce)corrections=corrections+1;
 end
 task step;begin @(posedge clk);#1;@(negedge clk);#1;end endtask
 task reset;begin monitor=0;rst_n=0;in_v=0;ack_v=0;ack_data=0;repeat(3)step;rst_n=1;credits=0;corrections=0;monitor=1;end endtask
 function[303:0]payload(input integer n);begin payload={2'b11,46'd0,256'hfedcba98765432100123456789abcdef314159265358979323846264338327950000|256'(n)};end endfunction
 task push(input integer n);begin in_payload=payload(n);in_v=1;step;in_v=0;end endtask
 task wait_head(input integer id);integer n;begin
  n=0;while(!head_v&&n<16)begin step;n=n+1;end
  if(!head_v||head_id!==64'(id)||head_payload!==payload(id))$fatal(1,"head identity/payload id%0d got%0d",id,head_id);
 end endtask
 task acknowledge(input integer id,input[1:0]mask);begin ack_v=1;ack_data={142'd0,64'(id),5'd0,mask};step;ack_v=0;ack_data=0;end endtask
 integer n,b;
 initial begin
  reset;for(n=1;n<=16;n=n+1)push(n);
  if(dut.count[0]!=16)$fatal(1,"finite16reservation");
  for(n=1;n<=16;n=n+1)begin
   wait_head(n);repeat(3)step;acknowledge(n,1);repeat(3)step;
   if(!head_v||head_id!=n||credits!=n-1)$fatal(1,"first V half released head/credit");
   acknowledge(n,2);repeat(2)step;
  end
  if(credits!=16||dut.count[0]!=0)$fatal(1,"actual retirement credits");
  $display("PASS pcowner finite16 full304payload ID64, independentVhalf delayedACK, actual16credits");
  for(b=0;b<432;b=b+1)begin
   reset;push(1);push(2);wait_head(1);
   dut.mem[1]=dut.mem[1]^(432'd1<<b);
   acknowledge(1,3);wait_head(2);
   if(corrections!=1)$fatal(1,"singlebit correction count bit%0d",b);
  end
  $display("PASS pcowner all432stored singlebit corrections, corrected payload+identity");
  reset;push(1);push(2);wait_head(1);dut.mem[1]=dut.mem[1]^432'd3;acknowledge(1,3);monitor=0;
  repeat(12)step;if(!fault||head_v||credit_return)$fatal(1,"UE failedclosed");
  reset;monitor=0;for(n=1;n<=17;n=n+1)push(n);if(!fault)$fatal(1,"overflow escaped");
  reset;push(1);wait_head(1);monitor=0;acknowledge(2,1);if(!fault||head_v)$fatal(1,"wrong ackID escaped");
  reset;push(1);wait_head(1);acknowledge(1,1);monitor=0;acknowledge(1,1);if(!fault)$fatal(1,"duplicatehalf ack escaped");
  reset;monitor=0;dut.ordinal[1]=5;step;if(!fault||head_v)$fatal(1,"owner mutableupset escaped");
  $display("PASS pcowner UE overflow wrongID duplicatehalf mutableowner failclosed");$finish;
 end
endmodule
