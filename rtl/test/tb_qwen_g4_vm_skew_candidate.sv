`timescale 1ns/1ps
module tb_qwen_g4_vm_skew_candidate;
 reg clk=0,rst_n=0;
 reg [3:0] re=0,we=0;
 reg [63:0] raddr=0,wmask=0;
 reg [47:0] waddr=0;
 reg [2047:0] wdata=0;
 wire [3:0] rv;wire [127:0] rdata;wire fault;
 ot_qwen_g4_vm_skew_candidate dut(.*);
 task tick; begin #5;clk=1;#1;#4;clk=0;end endtask
 integer w,l,g,t,ntrace;
 reg [8*512-1:0] tracefile;
 reg [2359:0] trace_mem[0:6000];
 reg [127:0] trace_expected;
 reg [31:0] expected;
 initial begin
  tick;rst_n=1;
  // Every word/lane nonzero, full capacity verifies mapping and masked macro storage.
  for(w=0;w<4096;w=w+1) begin
   we=1;waddr=w;wmask=16'hffff;
   for(l=0;l<16;l=l+1)wdata[l*32 +:32]=32'h3f000000+w*16+l;
   tick;if(fault)$fatal(1,"write fault");
  end
  we=0;
  for(w=0;w<4096;w=w+1)begin
   re=15;
   for(g=0;g<4;g=g+1)raddr[g*16 +:16]=w*16+g*5;
   tick;
   for(g=0;g<4;g=g+1)begin
    expected=32'h3f000000+w*16+g*5;
    if(!rv[g]||rdata[g*32 +:32]!==expected)$fatal(1,"read word=%0d lane=%0d got=%h",w,g*5,rdata[g*32 +:32]);
   end
  end
  if($value$plusargs("TRACE=%s",tracefile) && $value$plusargs("NTRACE=%d",ntrace))begin
   $readmemh(tracefile,trace_mem,0,ntrace-1);
   for(t=0;t<ntrace;t=t+1)begin
    {re,we,raddr,waddr,wmask,wdata,trace_expected}=trace_mem[t];tick;
    if(fault||rv!==re)$fatal(1,"trace fault %0d",t);
    for(g=0;g<4;g=g+1)if(re[g]&&rdata[g*32 +:32]!==trace_expected[g*32 +:32])$fatal(1,"trace data %0d group%0d",t,g);
   end
   // Restore word0 for directed read-before-write check below.
   re=0;we=1;waddr=0;wmask=16'hffff;
   for(l=0;l<16;l=l+1)wdata[l*32 +:32]=32'h3f000000+l;
   tick;
   $display("PASS trace %0d accepted cycles",ntrace);
  end
  // Two disjoint masked writes to same word merge, read-before-write old value.
  re=1;raddr=0;we=3;waddr=0;wmask=64'h0000000000020001;
  wdata=0;wdata[31:0]=32'h12345678;wdata[512+32 +:32]=32'h87654321;
  tick;if(rdata[31:0]!==32'h3f000000||fault)$fatal(1,"read before write");
  we=0;re=3;raddr=64'h0000000000010000;tick;
  if(rdata[31:0]!==32'h12345678||rdata[63:32]!==32'h87654321)$fatal(1,"merge");
  // Overlap is atomic fail: neither write changes memory.
  re=0;we=3;waddr=0;wmask=64'h0000000000010001;wdata=0;tick;
  if(!fault)$fatal(1,"overlap accepted");
  rst_n=0;we=0;tick;rst_n=1;re=1;raddr=0;tick;
  if(rdata[31:0]!==32'h12345678)$fatal(1,"failed request wrote memory");
  // Distinct words mapping to same bank are rejected.
  re=3;raddr=0;raddr[31:16]=16'h0080; // word8 maps2; choose word2 also maps2
  raddr[15:0]=16'h0020;tick;
  if(!fault)$fatal(1,"conflicting reads accepted");
  $display("PASS G4 skew 4096 words,16384 lane reads, masked merge, read-before-write, conflict atomicity");$finish;
 end
endmodule
