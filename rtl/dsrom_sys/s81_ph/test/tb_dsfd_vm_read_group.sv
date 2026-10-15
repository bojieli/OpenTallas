`timescale 1ns/1ps
module tb_dsfd_vm_read_group;
 parameter integer NR=16, MUT_EARLY=0;
 reg ck=0; always #0.4165 ck=~ck;
 reg rst_n=0;
 reg [NR-1:0] rq_v=0; reg [NR*14-1:0] rq_row=0;
 wire [NR-1:0] rq_credit, rs_v, b_rq_v; wire [NR*14-1:0] b_rq_row;
 wire [NR*512-1:0] rs_d; wire fault;
 reg [NR-1:0] b_rq_credit=0,b_rs_v=0; reg [NR*512-1:0] b_rs_d=0;
 dsfd_vm_read_group #(.NR(NR),.MUT_EARLY(MUT_EARLY)) dut(.*);
 reg [NR-1:0] tokens=0,wanted=0;
 integer bad=0, groups=0, replies=0, batch=0;
 always @(negedge ck) if(rst_n) begin
  tokens=tokens|rq_credit;
  if(|rs_v) begin
   replies=replies+1;
   if(rs_v!==wanted) begin bad=bad+1; $display("GROUP_BAD got%h wanted%h",rs_v,wanted); end
   for(integer s=0;s<NR;s=s+1) if(rs_v[s])
    for(integer w=0;w<16;w=w+1) if(rs_d[512*s+32*w+:32]!==32'(batch*97+s*19+w)) bad=bad+1;
   groups=groups+1;
  end
 end
 initial begin
  repeat(8)@(negedge ck); rst_n=1;
  // staggered backend initialization must produce exactly one full token set.
  for(integer s=0;s<NR;s=s+1) begin @(negedge ck); b_rq_credit=NR'(1)<<s; end
  @(negedge ck); b_rq_credit=0;
  wait(&tokens);
  for(batch=0;batch<128;batch=batch+1) begin : each
   integer n,nprev;
   n=1+((batch*7)%NR); wanted=(NR'(1)<<n)-1;
   wait((tokens&wanted)==wanted);
   @(posedge ck); tokens=tokens&~wanted; rq_v=wanted;
   for(integer s=0;s<n;s=s+1) rq_row[14*s+:14]=batch*NR+s;
   @(posedge ck); rq_v=0;
   wait(b_rq_v==wanted); @(negedge ck);
   nprev=groups;
   // Return members in reverse order and with variable delay.
   for(integer s=n-1;s>=0;s=s-1) begin
    repeat(1+((batch+s)%3))@(posedge ck);
    b_rs_v=NR'(1)<<s; b_rq_credit=b_rs_v;
    for(integer w=0;w<16;w=w+1) b_rs_d[512*s+32*w+:32]=batch*97+s*19+w;
    @(posedge ck); b_rs_v=0; b_rq_credit=0;
   end
   wait(groups>nprev); wait((tokens&wanted)==wanted); repeat(3)@(negedge ck);
  end
  repeat(4)@(negedge ck);
  $display("RESULT NR%0d groups%0d replies%0d bad%0d fault%0b",NR,groups,replies,bad,fault);
  if(!bad&&!fault&&groups==128) $display("PASS"); else $display("FAIL");
  $finish;
 end
 initial begin #100000; $display("FAIL TIMEOUT"); $finish; end
endmodule
