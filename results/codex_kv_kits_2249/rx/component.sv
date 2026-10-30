`timescale 1ns/1ps
// Actual RX retime form: deferred = (|hn) || (|in_count), both async-zero counters.
// D buses are arbitrary, so this covers every actual queue/counter next-state.
module tb;
 reg ck=0,rn=0; always #1 ck=~ck;
 reg [63:0] d=0; reg [511:0] payload=0;
 reg [63:0] oldq=0,newq=0; reg face=0;
 reg [511:0] oldpayload=0,portpayload=0;
 integer i,errors=0,checks=0,mut;
 initial if (!$value$plusargs("MUT=%d",mut)) mut=0;
 always @(posedge ck or negedge rn) if(!rn) oldq<=0; else oldq<=d;
 always @(posedge ck or negedge rn) if(!rn) newq<=0; else newq<=d;
 always @(posedge ck or negedge rn) if(!rn) face<=0; else face<=(|d[31:0]) || (|d[63:32]);
 always @(posedge ck) begin oldpayload<=payload; portpayload<=payload ^ (mut?512'h1:512'h0); end
 initial begin
  repeat(3) @(negedge ck);rn=1;
  for(i=0;i<2048;i=i+1)begin
   @(negedge ck);d={$random,$random}; if(i%7==0)d=0;
   for(integer j=0;j<16;j=j+1)payload[32*j+:32]=$random;
   if(i==1000)rn=0; if(i==1003)rn=1;
   @(posedge ck);#0.1;checks=checks+1;
   if(face!==((|oldq[31:0]) || (|oldq[63:32])) || newq!==oldq || oldpayload!==portpayload)errors=errors+1;
  end
  if(!mut && errors)$fatal(1,"RX_FACE_COMPONENT_FAIL checks%0d errors%0d",checks,errors);
  if(mut && !errors)$fatal(1,"RX_FACE_MUTANT_NOT_CAUGHT");
  $display("RX_FACE_COMPONENT_PASS checks%0d errors%0d mut%0d",checks,errors,mut);$finish;
 end
endmodule
