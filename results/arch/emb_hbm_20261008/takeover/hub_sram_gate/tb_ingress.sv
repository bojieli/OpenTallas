`timescale 1ns/1ps
module tb_ingress;
 reg clk=0;always #0.416666667 clk=~clk;
 reg rst_n=0,iv=0,ready=0;reg [522:0] data=0;
 wire credit,fault,valid;wire [522:0] out;wire [31:0] ce;
`ifdef EARLY_MUT
 localparam EARLY=1;
`else
 localparam EARLY=0;
`endif
 ot_qfd_hub_sram_ingress #(.MUT_EARLY_CREDIT(EARLY)) dut(
 .clk(clk),.rst_n(rst_n),.i_v(iv),.i_d(data),.i_cr(credit),.fault(fault),.ce_count(ce),
 .af_valid(valid),.af_data(out),.af_ready(ready));
 function automatic [522:0] pattern(input integer n);
 integer k;begin
  for(k=0;k<523;k=k+1)pattern[k]=((n*17+k*13+k/7)>>(k%13))&1;
  pattern[31:0]=n;pattern[522:512]=11'(n^11'h55a);
 end endfunction
 integer mode,cycle=0,sent=0,got=0,credits=0,retired=0,last_retire=0;
 integer maxocc=0,maxpending=0,steady=0;reg monitor=0;
 always @(posedge clk)if(rst_n && monitor)begin
  cycle=cycle+1;
  if(iv)sent=sent+1;
  if(valid && ready)begin
   if(out!==pattern(got))$fatal(1,"golden payload/tag mismatch row%0d",got);
   got=got+1;retired=retired+1;
  end
  if(credit)credits=credits+1;
  if(credit!==1'(last_retire))$fatal(1,"early/missing credit cycle%0d accepted%0d credit%0d",cycle,last_retire,credit);
  last_retire=valid && ready;
  if(dut.occupied>maxocc)maxocc=dut.occupied;
  if(dut.pending>maxpending)maxpending=dut.pending;
  if(ready && valid)steady=steady+1;
 end
 task tick(input reg v,input integer n,input reg r);
 begin @(negedge clk);iv=v;data=pattern(n);ready=r;end endtask
 integer n,deadline;
 reg [71:0] corrupt;reg [522:0] changed;
 initial begin
  if(!$value$plusargs("MODE=%d",mode))mode=0;
  repeat(5)@(negedge clk);rst_n=1;monitor=1;
  // Hold SRAM reads until all128 writes commit so fault injection is deterministic.
  force dut.read_issue=0;
  for(n=0;n<128;n=n+1)tick(1,n,0);
  tick(0,0,0);repeat(5)tick(0,0,0);
  if(dut.occupied!=128 || credits!=0)$fatal(1,"capacity/inflight reservation mismatch");
  if(mode==0)begin
   // One stored error in the lane containing11tag bits; correction must precede publication.
   dut.g_bank[2].u_mem.arr[9][66]=~dut.g_bank[2].u_mem.arr[9][66];
  end
  if(mode==3)begin
   dut.g_bank[0].u_mem.arr[11][2]=~dut.g_bank[0].u_mem.arr[11][2];
   dut.g_bank[0].u_mem.arr[11][4]=~dut.g_bank[0].u_mem.arr[11][4];
  end
  if(mode==4)begin
   changed=pattern(0);corrupt=dut.enc64(changed[63:0]^64'h1);
   dut.g_bank[0].u_mem.arr[0][71:0]=corrupt;
  end
  if(mode==2)begin
   tick(1,128,0);tick(0,0,0);repeat(3)tick(0,0,0);
   if(!fault || credits!=0)$fatal(1,"129th uncredited word failed overflow guard");
   $display("PASS overflow128 credits0 occupied%0d",dut.occupied);$finish;
  end
  release dut.read_issue;
  repeat(10)tick(0,0,0);
  if(credits!=0 || maxocc!=128 || maxpending!=2)$fatal(1,"held full capacity/credit gate");
  deadline=cycle+2000;
  while(got<128 && !fault && cycle<deadline)tick(0,0,cycle%7!=1);
  tick(0,0,1);repeat(4)tick(0,0,1);
  if(mode==3)begin
   if(!fault || got!=11 || credits!=11 || valid)$fatal(1,"UE leaked/credited row got%0d credits%0d",got,credits);
   $display("PASS UE prefix11 sticky no publication/credit");$finish;
  end
  if(fault || got!=128 || credits!=128 || ce!=(mode==0?1:0))$fatal(1,"first drain count got%0d cr%0d ce%0d fault%0d",got,credits,ce,fault);
  // Wrap pointers twice with sustained II1 and periodic backpressure, respecting128credits.
  deadline=cycle+4000;
  n=128;
  while((got<512 || n<512) && cycle<deadline)begin
   if(n<512 && sent-credits<128)begin tick(1,n,cycle%11!=0);n=n+1;end
   else tick(0,0,cycle%11!=0);
  end
  tick(0,0,1);repeat(5)tick(0,0,1);
  if(fault || got!=512 || credits!=512 || dut.occupied!=0 || dut.pending!=0)$fatal(1,"wrap/stall drain failure got%0d cr%0d",got,credits);
  // Final tagged word represents ordered fence after all prior traffic.
  tick(1,512,0);tick(0,0,0);repeat(8)tick(0,0,0);
  if(got!=512 || credits!=512)$fatal(1,"fence credited before real accept");
  repeat(8)tick(0,0,1);
  if(got!=513 || credits!=513)$fatal(1,"fence order/drain failure");
  // Reset flush with occupied resident+pending slots. SRAM contents remain stale but invalid.
  for(n=513;n<533;n=n+1)tick(1,n,0);
  tick(0,0,0);@(negedge clk);rst_n=0;monitor=0;
  repeat(4)@(negedge clk);iv=0;ready=1;rst_n=1;
  repeat(8)@(negedge clk);
  if(fault || valid || credit || dut.occupied!=0 || dut.pending!=0)$fatal(1,"reset leaked stale word");
  $display("PASS ingress523 capacity128 peak_pending2 CE%0d words513 wrap/stalls/fence/reset cycles%0d",mode==0?1:0,cycle);
  $finish;
 end
endmodule
