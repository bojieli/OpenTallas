`timescale 1ns/1ps
module tb_hbm_b2_xwrite_aperture;
 parameter integer MUT=0;
 reg clk=0;always #0.5 clk=~clk;reg rst_n=0,permit=1,mirror=0;reg [1:0] sid=0;
 reg [2239:0] old_q=0;wire [7:0] old_cr,old_done;wire [2247:0] wq;
 reg [7:0] wq_cr=0,wq_done=0;wire fault;
 ot_hbm_b2_xwrite_aperture #(.MUT(MUT)) u(.*);
 initial begin
  repeat(4)@(negedge clk);rst_n=1;
  for(integer q=0;q<4;q=q+1)for(integer m=0;m<2;m=m+1)for(integer w=0;w<512;w=w+1)begin
   sid=2'(q);mirror=1'(m);wq_cr=8'(w);wq_done=8'(w>>1);
   for(integer b=0;b<8;b=b+1)old_q[b*280+:280]={1'b1,15'(w*8+b),256'(w*8+b),8'(w+b)};
   #0.1;
   for(integer b=0;b<8;b=b+1)if(wq[b*281+:281]!={1'b1,1'(m),2'(m?0:q),13'(w*8+b),256'(w*8+b),8'(w+b)})$fatal(1,"write sec16/data/mask translation");
   if(old_cr!=wq_cr||old_done!=wq_done||fault)$fatal(1,"credit/done mapping");
   @(negedge clk);
  end
  mirror=1;old_q[279:0]={1'b1,15'd4096,264'b0};#0.1;
  if(wq[280])$fatal(1,"mirror write overflow issued");
  @(negedge clk);if(!fault)$fatal(1,"mirror overflow not refused");
  $display("PASS_WRITE_APERTURE mappings=32768 credit_done_distinct production_memory_gate=OPEN");$finish;
 end
endmodule
