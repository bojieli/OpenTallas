`timescale 1ns/1ps
module tb_hbm_b2_xread_aperture;
 parameter integer MUT=0;
 reg clk=0;always #0.5 clk=~clk;reg rst_n=0,permit=1,mirror=0;reg [1:0] sid=0;
 reg [511:0] old_q=0;wire [31:0] old_cr;wire [8223:0] old_rsp;wire [135:0] rq;
 reg [7:0] rq_cr=0;reg [2055:0] rr=0;wire fault;
 ot_hbm_b2_xread_aperture #(.MUT(MUT)) u(.*);
 initial begin
  repeat(4)@(negedge clk);rst_n=1;
  for(integer q=0;q<4;q=q+1)for(integer m=0;m<2;m=m+1)for(integer w=0;w<512;w=w+1)begin
   sid=2'(q);mirror=1'(m);rq_cr=8'(w);
   for(integer b=0;b<8;b=b+1)begin old_q[b*16+:16]={1'b1,15'(w*8+b)};rr[b*257+:257]={1'b1,256'(w*8+b)};end
   #0.1;
   for(integer b=0;b<8;b=b+1)if(rq[b*17+:17]!={1'b1,1'(m),2'(m?0:q),13'(w*8+b)}||old_rsp[b*257+:257]!=rr[b*257+:257]||old_cr[b]!=rq_cr[b])$fatal(1,"mirror/sid/lane/credit translation");
   if(old_cr[31:8]!=0||old_rsp[8223:2056]!=0||fault)$fatal(1,"inactive upper lanes");
   @(negedge clk);
  end
  mirror=1;old_q[15:0]={1'b1,15'd4096};#0.1;
  if(rq[16])$fatal(1,"mirror boundary overflow issued");
  @(negedge clk);if(!fault)$fatal(1,"mirror overflow not refused");
  $display("PASS_APERTURE mappings=32768 mirror_boundary_refused production_memory_gate=OPEN");$finish;
 end
endmodule
