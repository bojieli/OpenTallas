`timescale 1ns/1ps
module tb_control_channel;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,sv=0,mr=0;wire sr,mv,fault;reg[55:0]sd=0;wire[55:0]md;
 integer sent=0,got=0,cycle=0;
 ot_hbrom_control_channel #(.W(56),.P(2),.DEPTH(7)) dut(.clk(clk),.rst_n(rst_n),.s_valid(sv),.s_ready(sr),.s_data(sd),.m_valid(mv),.m_ready(mr),.m_data(md),.fault(fault));
 initial begin
  repeat(4)@(negedge clk);rst_n=1;
  while(got<32)begin
   @(negedge clk);sv=(sent<32);sd=sent;mr=(cycle%5!=0);cycle=cycle+1;
   @(posedge clk);
   if(fault)$fatal(1,"clean stream fault");
   if(sv&&sr)sent=sent+1;
   if(mv&&mr)begin if(md!==got)$fatal(1,"order/payload mismatch");got=got+1;end
   if(cycle>500)$fatal(1,"finite fixture deadlock");
  end
  @(negedge clk);sv=0;mr=1;
  repeat(8)@(negedge clk);
  force dut.primary.cred=0;
  #1;if(!fault||sr||mv)$fatal(1,"credit upset not fail-stop");
  @(negedge clk);release dut.primary.cred;
  repeat(3)@(negedge clk);
  if(!fault||sr||mv)$fatal(1,"fault not sticky");
  $display("PASS channel clean32/stalls + primary credit upset fail-stop");$finish;
 end
endmodule
