`timescale 1ns/1ps
module stream_case #(parameter integer DEPTH=8,STALL=0)(input wire clk,rst_n,output reg done=0);
 localparam integer WORDS=192;
 reg step=0,ready=0,nv=0,hq=0;reg [511:0] word_q=0;reg [47:0] identity=0;reg [39:0] seq=0;
 wire credit,cv,ch,fault;wire [511:0] cw;wire [87:0] cm;
 integer sent=0,received=0,cycle=0,first_produce=-1,last_produce=-1,first_pop=-1,last_pop=-1,peak=0,paused=0,posts=0,typed_retire=0,nonquery_count=0;
 function automatic [511:0] packet(input integer index);
  for(integer z=0;z<16;z=z+1)packet[32*z+:32]=32'hc1230400^(32'(index)*32'd7919)^32'(z*1234567);
 endfunction
 function automatic [47:0] tag(input integer index);tag={16'(index^16'h2345),32'(32'hc1230400+index)};endfunction
 function automatic [39:0] qseq(input integer index);qseq=40'h8100000000+40'(index);endfunction
 function automatic bit queried(input integer index);queried=index%3!=0;endfunction
 ot_qwen_numeric_stream_queue #(.ENABLE(1),.DEPTH(DEPTH)) dut(.base_clk(clk),.rst_n(rst_n),.core_output_step(step),.numeric_v(nv),.numeric_word(word_q),.numeric_has_query(hq),.numeric_identity(identity),.numeric_query_seq(seq),.core_credit(credit),.consume_ready(ready),.consume_v(cv),.consume_word(cw),.consume_has_query(ch),.consume_query_tuple(cm),.fault(fault));
 always @(negedge clk)begin
  step<=rst_n&&credit&&sent<WORDS;
  ready<=!STALL||cycle>=35&&(cycle%29<17);
 end
 always @(posedge clk)begin
  if(!rst_n)begin sent=0;received=0;cycle=0;nv<=0;hq<=0;posts=0;typed_retire=0;nonquery_count=0;done<=0;end
  else begin
   cycle=cycle+1;
   if(step)begin
    if(first_produce<0)first_produce=cycle;last_produce=cycle;
    word_q<=packet(sent);identity<=tag(sent);nv<=1;hq<=queried(sent);seq<=qseq(sent);sent=sent+1;
   end else paused=paused+1;
   if(dut.pending_post)posts=posts+1;
   if(cv&&ready)begin
    if(cw!==packet(received)||ch!==queried(received)||cm[87:40]!==tag(received)||cm[39:0]!==qseq(received))$fatal(1,"stream numeric/tag mismatch depth%0d stall%0d index%0d",DEPTH,STALL,received);
    if(first_pop<0)first_pop=cycle;last_pop=cycle;received=received+1;
    if(ch)typed_retire=typed_retire+1;else nonquery_count=nonquery_count+1;
   end
   if(STALL&&cycle==30&&(typed_retire!=0||posts!=DEPTH))$fatal(1,"posting fabricated retirement or failed full reservation");
   #1;if(fault)$fatal(1,"stream reservation fault");if(dut.count>peak)peak=dut.count;
   if(received==WORDS&&!done)begin
    if(typed_retire!=128||nonquery_count!=64||posts!=WORDS||dut.count!=0)$fatal(1,"stream counts/drain wrong");
    if(!STALL&&DEPTH==8&&last_produce-first_produce!=WORDS-1)$fatal(1,"stream unit rate lost");
    done=1;$display("STREAM depth=%0d stall=%0d words=%0d query_retire=%0d nonquery=%0d posts=%0d interval=%0d first_pop_delta=%0d peak=%0d paused=%0d last_pop=%0d",DEPTH,STALL,received,typed_retire,nonquery_count,posts,last_produce-first_produce,first_pop-first_produce,peak,paused,last_pop);
   end
  end
 end
endmodule
module stream_reset(input wire clk,rst_n,output reg done=0);
 reg reset=0,step=0,nv=0,ready=0,hq=0;reg [511:0] w=0;reg [47:0] id=0;reg [39:0] seq=0;
 wire credit,cv,ch,fault;wire [511:0] cw;wire [87:0] cm;
 ot_qwen_numeric_stream_queue #(.ENABLE(1),.DEPTH(8)) dut(.base_clk(clk),.rst_n(reset),.core_output_step(step),.numeric_v(nv),.numeric_word(w),.numeric_has_query(hq),.numeric_identity(id),.numeric_query_seq(seq),.core_credit(credit),.consume_ready(ready),.consume_v(cv),.consume_word(cw),.consume_has_query(ch),.consume_query_tuple(cm),.fault(fault));
 initial begin
  wait(rst_n);@(negedge clk);reset=1;
  repeat(8)begin @(negedge clk);step=credit;@(posedge clk);if(step)begin w<=512'hdead;id<=48'hdead;seq<=40'hdead;hq<=1;nv<=1;end end
  @(negedge clk);step=0;repeat(3)@(negedge clk);
  if(!cv)$fatal(1,"reset scene did not fill");reset=0;nv=0;step=0;
  repeat(2)@(negedge clk);reset=1;ready=1;
  repeat(3)begin @(posedge clk);#1;if(cv||fault)$fatal(1,"reset leaked old tuple");end
  @(negedge clk);step=1;@(posedge clk);w<=512'h123456;id<=48'h123456789abc;seq<=40'h8100000001;hq<=0;nv<=1;
  @(negedge clk);step=0;wait(cv);if(cw!==512'h123456||ch!==0||cm!=={48'h123456789abc,40'h8100000001})$fatal(1,"reset fresh tuple mismatch");
  @(posedge clk);#1;if(cv||fault)$fatal(1,"reset fresh pop failed");done=1;$display("STREAM reset flushed queued old words and accepted fresh nonquery");
 end
endmodule
module tb_qwen_numeric_stream_queue;
 reg clk=0;always #5 clk=~clk;reg rst_n=0;wire [4:0] done;
 stream_case #(.DEPTH(2)) a(clk,rst_n,done[0]);stream_case #(.DEPTH(8)) b(clk,rst_n,done[1]);
 stream_case #(.DEPTH(2),.STALL(1)) c(clk,rst_n,done[2]);stream_case #(.DEPTH(8),.STALL(1)) d(clk,rst_n,done[3]);
 stream_reset e(clk,rst_n,done[4]);
 initial begin repeat(4)@(negedge clk);rst_n=1;wait(&done);$display("PASS streaming queue words/tags/pop-only-retire/full stalls/reset");$finish;end
 initial begin #200000;$fatal(1,"stream timeout");end
endmodule
