`timescale 1ns/1ps
module queue_service_case #(parameter integer DEPTH=2,QUERY=0,STALL=0)(input wire clk,rst_n,output reg done=0);
 localparam integer WORDS=128;
 reg step=0,ready=1,nv=0,qtoggle=0;reg [511:0] word_q=0;reg [47:0] identity=0;reg [87:0] qtuple=0;
 wire credit,cv,ch,fault,ack;wire [511:0] cw;wire [87:0] cm;
 integer sent=0,received=0,cycle=0,first_produce=-1,last_produce=-1,first_consume=-1,last_consume=-1,peak=0;
 function automatic [511:0] packet(input integer index);
  for(integer z=0;z<16;z=z+1)packet[32*z+:32]=32'hc1230400^(32'(index)*32'd7919)^32'(z*1234567);
 endfunction
 function automatic [47:0] tag(input integer index);tag={16'(index^16'h2345),32'(32'hc1230400+index)};endfunction
 ot_qwen_numeric_output_queue #(.ENABLE(1),.DEPTH(DEPTH)) dut(.base_clk(clk),.rst_n(rst_n),.core_output_step(step),.numeric_v(nv),.numeric_word(word_q),.numeric_identity(identity),.query_output_toggle(qtoggle),.query_output_tuple(qtuple),.query_output_ack_toggle(ack),.core_credit(credit),.consume_ready(ready),.consume_v(cv),.consume_word(cw),.consume_has_query(ch),.consume_query_tuple(cm),.fault(fault));
 always @(negedge clk)begin step<=rst_n&&credit&&sent<WORDS;ready<=!STALL||cycle%19<11;end
 always @(posedge clk)begin
  if(!rst_n)begin sent=0;received=0;cycle=0;nv<=0;qtoggle<=0;done<=0;end
  else begin
   cycle=cycle+1;
   if(step)begin
    if(first_produce<0)first_produce=cycle;last_produce=cycle;
    word_q<=packet(sent);identity<=tag(sent);nv<=1;
    if(QUERY)begin qtoggle<=!qtoggle;qtuple<={tag(sent),40'(sent)};end
    sent=sent+1;
   end
   if(cv&&ready)begin
    if(cw!==packet(received)||ch!==1'(QUERY)||cm[87:40]!==tag(received)||cm[39:0]!==40'(QUERY?received:0))$fatal(1,"numeric service word/tag mismatch depth%0d query%0d stall%0d",DEPTH,QUERY,STALL);
    if(first_consume<0)first_consume=cycle;last_consume=cycle;received=received+1;
   end
   #1;if(fault)$fatal(1,"numeric service reservation fault");if(dut.count>peak)peak=dut.count;
   if(received==WORDS&&!done)begin
    if(!QUERY&&!STALL&&DEPTH==8&&last_produce-first_produce!=WORDS-1)$fatal(1,"deep FIFO lost unit service rate");
    done=1;$display("QUEUE_SERVICE depth=%0d query=%0d stall=%0d words=%0d first_produce=%0d last_produce=%0d first_consume=%0d last_consume=%0d produce_interval=%0d earliest_post_pop_latency=%0d peak=%0d",DEPTH,QUERY,STALL,received,first_produce,last_produce,first_consume,last_consume,last_produce-first_produce,first_consume-first_produce,peak);
   end
  end
 end
endmodule
module tb_qwen_numeric_queue_service;
 reg clk=0;always #5 clk=~clk;reg rst_n=0;wire [5:0] done;
 queue_service_case #(.DEPTH(2)) a(clk,rst_n,done[0]);queue_service_case #(.DEPTH(8)) b(clk,rst_n,done[1]);
 queue_service_case #(.DEPTH(2),.QUERY(1)) c(clk,rst_n,done[2]);queue_service_case #(.DEPTH(8),.QUERY(1)) d(clk,rst_n,done[3]);
 queue_service_case #(.DEPTH(2),.STALL(1)) e(clk,rst_n,done[4]);queue_service_case #(.DEPTH(8),.STALL(1)) f(clk,rst_n,done[5]);
 initial begin repeat(4)@(negedge clk);rst_n=1;wait(&done);$display("PASS source-bound queue service six scenes");$finish;end
 initial begin #200000;$fatal(1,"service timeout");end
endmodule
