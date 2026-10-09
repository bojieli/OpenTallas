`timescale 1ns/1ps
module tb_qfd_kv_row_endpoint;
 reg clk=0;always#5 clk=~clk;reg rst_n=0;reg[6:0]rr=0;
 reg[31:0]h_v=0,h_isk=0,h_tail=0,tile_credit_return=0;
 reg[63:0]h_need=0,h_sel0=0,h_sel1=0;reg[2047:0]h_id=0;
 reg[8191:0]h_data=0;reg[351:0]h_tile0=0,h_tile1=0;
 reg[223:0]h_loc0=0,h_loc1=0;reg[127:0]h_tail_lanes=0;
 wire[2:0]row_v,ack_v;wire[842:0]row_data;wire[212:0]ack_data;wire fault;
 ot_qfd_kv_row_endpoint #(.ENABLE(1)) dut(.*);
 reg[31:0]observed=0;integer ackcount=0,wordcount=0,cycle=0,slot,pc;
 reg[31:0]credit_pipe[0:23];reg[31:0]pending_credit;reg monitor=1;reg[63:0]want_id=1;
 always @(posedge clk)if(rst_n&&monitor)begin
  if(fault)$fatal(1,"unexpected endpoint fault");
  pending_credit=0;
  for(slot=0;slot<3;slot=slot+1)begin
   if(row_v[slot])begin
    pending_credit[row_data[slot*281+276+:5]]=1;wordcount=wordcount+1;
    if(row_data[slot*281+:128]!==128'h31415926535897932384626433832795)$fatal(1,"row payload changed");
   end
   if(ack_v[slot])begin
    pc=ack_data[slot*71+2+:5];
    if(ack_data[slot*71+7+:64]!==want_id||ack_data[slot*71+:2]!==2'b01)$fatal(1,"ack identity/mask");
    if(observed[pc])$fatal(1,"duplicate head consumption while reverse ack in flight");
    observed[pc]=1;ackcount=ackcount+1;
   end
  end
  for(integer k=23;k>0;k=k-1)credit_pipe[k]=credit_pipe[k-1];
  credit_pipe[0]=pending_credit;cycle=cycle+1;
 end
 always@(negedge clk)if(monitor)tile_credit_return=credit_pipe[23];
 task step;begin @(posedge clk);#1;@(negedge clk);#1;end endtask
 integer p;
 initial begin
  for(p=0;p<24;p=p+1)credit_pipe[p]=0;
  repeat(2)step;rst_n=1;h_v='1;
  for(p=0;p<32;p=p+1)begin
   h_need[p*2+:2]=1;h_id[p*64+:64]=1;h_data[p*256+:256]={128'hfedcba98765432100123456789abcdef,128'h31415926535897932384626433832795};
  end
  // All32 heads stay visible well beyond reverse-link latency. Exactly one
  // launch and ID-tagged ack perPC despite each head remaining asserted.
  repeat(220)step;
  if(observed!==32'hffffffff||ackcount!=32||wordcount!=32)$fatal(1,"full32PC heldheads missing ack%0d words%0d",ackcount,wordcount);
  observed=0;want_id=2;
  for(p=0;p<32;p=p+1)h_id[p*64+:64]=2;
  repeat(220)step;
  if(observed!==32'hffffffff||ackcount!=64||wordcount!=64)$fatal(1,"next ordinal failed");
  $display("PASS rowendpoint full32PC heldhead cycles%0d ack64 exactID64+PC5+half2, delayed24edgecredits, no duplicate grants",cycle);
  monitor=0;h_id[0+:64]=1;#1;if(!fault||row_v||ack_v)$fatal(1,"stale reverse head ID escaped");
  step;if(!fault)$fatal(1,"stale ID fault not held");
  rst_n=0;repeat(2)step;h_v=0;rst_n=1;step;
  dut.done[1][0]=2'b01;#1;if(!fault||row_v||ack_v)$fatal(1,"mutable row cache disagreement escaped");
  step;if(!fault)$fatal(1,"cache fault not held");
  $display("PASS rowendpoint staleID and mutablecache fault failclosed");$finish;
 end
endmodule
