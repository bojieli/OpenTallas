`timescale 1ns/1ps
// Static return-boundary phase schedule. No output-dependent issue or credit.
module tb;
 reg ck=0,rst_n=0;always #3 ck=~ck;
 reg[2:0]v=0;reg[5:0]lane=0;reg[3:0]ev=0;reg[2047:0]ed=0;reg[10:0]xgo=0;
 wire[512:0]crs;wire qv,gv,fault;wire[511:0]qd;wire[510:0]gd;
 dsfd_vm_xio_return dut(ck,rst_n,v,lane,ev,ed,xgo,crs,qv,qd,gv,gd,fault);
 task idle(input integer n);repeat(n)@(negedge ck);endtask
 task reset;begin rst_n=0;v=0;ev=0;xgo=0;idle(4);rst_n=1;idle(8);end endtask
 task pushes(input integer n);integer i;begin
  for(i=0;i<n;i=i+1)begin v=4;ev=1;ed=0;ed[58:49]=10'(21+i);idle(1);end
  v=0;ev=0;idle(5);
 end endtask
 task pops(input integer n,input bit bad);integer i;begin
  for(i=0;i<n;i=i+1)begin xgo={1'b1,10'(21+i+(bad?1:0))};idle(1);end
  xgo=0;idle(4);
 end endtask
 initial begin
  reset();pushes(4);pops(4,0);if(fault)$fatal(1,"LEGAL FOUR PHASE FIFO fault");
  reset();pushes(1);pops(1,1);if(!fault)$fatal(1,"BAD PHASE not observed");
  reset();pops(1,0);if(!fault)$fatal(1,"UNDERFLOW not observed");
  reset();pushes(5);if(!fault)$fatal(1,"OVERFLOW not observed");
  reset();pushes(2);pops(2,0);if(fault)$fatal(1,"WARM PHASE FIFO fault");
  $display("XIO_RETURN_PHASE PASS legal4 badphase underflow overflow warm2");$finish;
 end
 initial begin #3000;$fatal(1,"timeout");end
endmodule
