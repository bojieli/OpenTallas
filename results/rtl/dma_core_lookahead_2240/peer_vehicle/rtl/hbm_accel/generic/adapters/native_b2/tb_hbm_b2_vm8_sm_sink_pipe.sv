`timescale 1ns/1ps
module tb_hbm_b2_vm8_sm_sink_pipe;
 parameter integer MUT=0;
 reg clk=0;always #0.5 clk=~clk;reg rst_n=0,permit=1;
 reg [191:0] expected_owner=192'hab123def;reg [7:0] sm_mask=8'hff;
 reg tap_v=0;wire tap_ready;reg [2062:0] tap_data=0;
 reg [191:0] tap_owner=192'hab123def;reg [15:0] tap_ticket=0;
 wire tap_ACK_v;wire [191:0] tap_ACK_owner;wire [15:0] tap_ACK_ticket;
 wire [7:0] xw_en;wire [55:0] xw_addr,xw_grp;wire [16383:0] xw_data;wire fault,drained;
 ot_hbm_b2_vm8_sm_sink #(.MUT(MUT),.PIPE(1)) u(.*);
 integer accepts=0,samples=0,acks=0,cycles=0;
 reg [2062:0] expected[0:1663];reg [15:0] tickets[0:1663];integer accepted_edge[0:1663];
 always @(posedge clk)if(rst_n)begin
  cycles=cycles+1;
  // Observe old ACK before current sampling: ACK must already have a prior sample.
  if(tap_ACK_v)begin
   if(acks>=samples||tap_ACK_owner!=expected_owner||tap_ACK_ticket!=tickets[acks]||cycles!=accepted_edge[acks]+2)$fatal(1,"ACK identity/order/early edge mismatch");
   acks=acks+1;
  end
  if(|xw_en)begin
   if(samples>=accepts)$fatal(1,"SM sample without accepted beat");
   for(integer s=0;s<8;s=s+1)if(xw_en[s]&&(xw_addr[s*7+:7]!=expected[samples][2061:2055]||xw_grp[s*7+:7]!=expected[samples][2054:2048]||xw_data[s*2048+:2048]!=expected[samples][2047:0]))$fatal(1,"SM pipelined sample mismatch");
   if(cycles!=accepted_edge[samples]+1)$fatal(1,"SM sampling latency mismatch");
   samples=samples+1;
  end
  if(tap_v&&tap_ready)begin
   expected[accepts]=tap_data;tickets[accepts]=tap_ticket;accepted_edge[accepts]=cycles;accepts=accepts+1;
  end
 end
 initial begin
  repeat(4)@(negedge clk);rst_n=1;
  for(integer n=0;n<1664;n=n+1)begin
   if(!tap_ready||fault)$fatal(1,"not one beat per edge");
   tap_v=1;tap_ticket={11'(n/32),1'(n%2),4'((n/2)%16)}; // all owner192 identical; dedicated tickets differ
   tap_data={1'b1,7'(n/13),7'(n%13),2048'b0};
   for(integer b=0;b<64;b=b+1)tap_data[b*32+:32]=32'hab312701+n*67+b;
   if(n%13==12)tap_data[2047:640]=0;
   @(negedge clk);
  end
  tap_v=0;repeat(3)@(negedge clk);
  if(accepts!=1664||samples!=1664||acks!=1664||fault||!drained)$fatal(1,"pipeline count/drain mismatch");
  // Lost lease never launches another SM pulse or ACK.
  permit=0;tap_v=1;@(negedge clk);tap_v=0;
  if(!fault||xw_en!=0||tap_ACK_v)$fatal(1,"missing reservation admitted");
  $display("PASS_PIPE_SINK beats=1664 consecutive_accepts=1664 samples=1664 ACKs=1664 input_to_ACK_edges=2 distinct_tickets_same_owner production_gate=OPEN");$finish;
 end
endmodule
