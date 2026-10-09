`timescale 1ns/1ps
// Minimum physical-memory read/ECC/fault mechanism. Inject at real macro output,
// including all lane-select positions; does not simulate an array or whole die.
module tb_qfd_prompt_sram_fault;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,we=0,re=0;reg [12:0] wa=0,ra=0;reg [17:0] wd=0;
 wire [17:0] q;wire fault;
 ot_qfd_prompt_sram #(.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.we(we),.re(re),.waddr(wa),.raddr(ra),.wdata(wd),.q(q),.fault(fault));
 reg [255:0] inject;reg [23:0] code;
 integer lane,i,j,checks=0,bad=0,reset_checks=0;
 task startcase(input integer l);
 begin
  @(negedge clk);re=0;rst_n=0;
  @(negedge clk);rst_n=1;re=1;ra=l;
  if(fault!==0) bad=bad+1;reset_checks=reset_checks+1;
 end endtask
 task sampled(input bit ue);
 begin
  @(posedge clk);#1;
  checks=checks+1;
  if(ue) begin if(q!==0 || fault!==1) bad=bad+1;end
  else begin if(q!==18'h2b123 || fault!==0) bad=bad+1;end
 end endtask
 initial begin
  repeat(3) @(negedge clk);rst_n=1;wd=18'h2b123;
  for(lane=0;lane<8;lane=lane+1) begin
   @(negedge clk);we=1;wa=lane;
  end
  @(negedge clk);we=0;
  code=dut.encode(18'h2b123);
  for(lane=0;lane<8;lane=lane+1) begin
   for(i=0;i<24;i=i+1) begin
    startcase(lane);
    inject=0;inject[lane*32+:24]=code^(24'b1<<i);
    force dut.rd=inject;
    sampled(0);
    sampled(0);
    release dut.rd;
   end
   for(i=0;i<24;i=i+1) for(j=i+1;j<24;j=j+1) begin
    startcase(lane);
    inject=0;inject[lane*32+:24]=code^(24'b1<<i)^(24'b1<<j);
    force dut.rd=inject;
    // UE appears immediately on q; sticky fault captures on following edge.
    @(posedge clk);#1;if(q!==0) bad=bad+1;
    sampled(1);
    release dut.rd;
    @(negedge clk);re=0;
    @(posedge clk);#1;if(fault!==1) bad=bad+1;
   end
  end
  if(bad==0) $display("PROMPT_FAULT_PASS checks=%0d resets=%0d",checks,reset_checks);
  else $display("PROMPT_FAULT_FAIL bad=%0d checks=%0d resets=%0d",bad,checks,reset_checks);
  $finish;
 end
endmodule
