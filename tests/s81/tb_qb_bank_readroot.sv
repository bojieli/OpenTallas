`timescale 1ns/1ps
module tb_qb_bank_readroot;
 reg clk=0;always #0.416666667 clk=~clk;
 reg stop=0;
 wire clk_rd=clk&&!stop;
 reg rst_n=0;reg[6:0]wr0=0,wr1=0;reg wq0=0,wq1=0;
 reg[511:0]aq_q=0;reg[15:0]i0=0,i1=0;reg rq0=0,rq1=0;
 wire[255:0]a,b;
 ot_s81_pq_qb_bankp_native flat(.clk(clk),.rst_n(rst_n),.wr0(wr0),.wr1(wr1),.wq0(wq0),.wq1(wq1),.aq_q(aq_q),.i0(i0),.i1(i1),.rq0(rq0),.rq1(rq1),.rd(a));
 ot_s81_pq_qb_bankp_readroot split(.clk(clk),.clk_rd(clk_rd),.rst_n(rst_n),.wr0(wr0),.wr1(wr1),.wq0(wq0),.wq1(wq1),.aq_q(aq_q),.i0(i0),.i1(i1),.rq0(rq0),.rq1(rq1),.rd(b));
 integer row,k,t,checks=0;reg compare=0;
 always @(negedge clk)if(compare)begin
  if(a!==b)begin $display("QB_READROOT FAIL check%0d",checks);$fatal(1,"root partition mismatch");end
  checks=checks+1;
 end
 function[15:0]idx(input integer r);idx={7'b0,5'(r>>2),1'b0,2'(r),1'b0};endfunction
 initial begin
  repeat(8)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
  // All128 physical words, both write selectors, full256bits reconstructed.
  for(row=0;row<128;row=row+1)begin
   wr0=row;wr1=row;wq0=!row[0];wq1=row[0];
   for(k=0;k<16;k=k+1)aq_q[32*k+:32]=32'h9e37f4a1 ^ (row*12391+k*317);
   @(negedge clk);
  end
  wq0=0;wq1=0;repeat(5)@(negedge clk);compare=1;
  for(t=0;t<1024;t=t+1)begin
   row=(t*37)%128;i0=idx(row);i1=idx((row+19)%128);rq0=!t[0];rq1=t[0];
`ifdef OT_QB_READROOT_MUT_STOP
   if(t==512)stop=1;
`endif
   @(negedge clk);
  end
  rq0=0;rq1=0;repeat(5)@(negedge clk);
  if(checks<1024)$fatal(1,"coverage");
  $display("QB_READROOT PASS checks%0d physicalrows128 bits256 cycles_added0",checks);$finish;
 end
endmodule
