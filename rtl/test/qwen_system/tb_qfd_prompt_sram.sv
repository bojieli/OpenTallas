`timescale 1ns/1ps
module tb_qfd_prompt_sram;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,we=0,re=0;reg [12:0] wa=0,ra=0;reg [17:0] wd=0;
 wire [17:0] q;wire fault;
 ot_qfd_prompt_sram #(.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.we(we),.re(re),.waddr(wa),.raddr(ra),.wdata(wd),.q(q),.fault(fault));
 reg [17:0] refmem[0:8191];reg [17:0] expectq=0;
 integer i,j,k,n,mismatches=0,checks=0,ecc_checks=0,ecc_bad=0;
 reg [23:0] enc,x;reg [18:0] dec;
 task cycle(input wr,input rr,input [12:0] aw,input [12:0] ar,input [17:0] data);
 begin
  @(negedge clk);we=wr;re=rr;wa=aw;ra=ar;wd=data;
  if(rr) expectq=refmem[ar];
  @(posedge clk);#1;
  if(rr) begin checks=checks+1;if(q!==expectq || fault) mismatches=mismatches+1;end
  if(wr) refmem[aw]=data;
 end endtask
 initial begin
  repeat(3) @(negedge clk);rst_n=1;
  for(i=0;i<8192;i=i+1) cycle(1,0,i,0,(i*73)^18'h2bb23);
  for(i=0;i<8192;i=i+1) cycle(0,1,0,i,0);
  // Same-row writes at every slot, simultaneous reads (including read-before-write collision).
  for(i=0;i<4096;i=i+1) cycle(1,1,(i*23)%8192,(i%3==0)?(i*23)%8192:((i*23)%8192)^3,i^18'h33456);
  for(i=0;i<8192;i=i+1) cycle(0,1,0,i,0);
  cycle(0,0,0,0,0);cycle(0,0,0,0,0);
  for(n=0;n<8;n=n+1) begin
   enc=dut.encode(18'((n*19873)^18'h255ad));
   for(j=0;j<24;j=j+1) begin
    x=enc^(24'b1<<j);dec=dut.decode(x);ecc_checks=ecc_checks+1;
    if(dec!=={1'b0,18'((n*19873)^18'h255ad)}) ecc_bad=ecc_bad+1;
   end
   for(j=0;j<24;j=j+1) for(k=j+1;k<24;k=k+1) begin
    dec=dut.decode(enc^(24'b1<<j)^(24'b1<<k));ecc_checks=ecc_checks+1;
    if(dec[18]!==1 || dec[17:0]!==0) ecc_bad=ecc_bad+1;
   end
  end
  if(mismatches==0 && ecc_bad==0) $display("PROMPT_SRAM_PASS reads=%0d ecc=%0d",checks,ecc_checks);
  else $display("PROMPT_SRAM_FAIL mismatches=%0d ecc_bad=%0d reads=%0d ecc=%0d",mismatches,ecc_bad,checks,ecc_checks);
  $finish;
 end
endmodule
