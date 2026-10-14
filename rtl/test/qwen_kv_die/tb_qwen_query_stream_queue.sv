`timescale 1ns/1ps
module query_case #(parameter integer DEPTH=8,STALL=0)(input wire clk,rst_n,output reg done=0);
 localparam integer WORDS=192;
 reg step=0,ready=0,nv=0;reg [209:0] tuple_q=0;
 wire credit,cv,fault;wire [209:0] cm;
 integer sent=0,received=0,cycle=0,first_produce=-1,last_produce=-1,first_pop=-1,last_pop=-1,peak=0,paused=0,posts=0,recorded=0,unallocated=0;
 function automatic [209:0] packet(input integer index);
 reg [95:0] key;
 for(integer z=0;z<4;z=z+1)key[24*z+:24]=24'(index*7919+z*1234567+24'hfedcba);
 packet={4'(index%15+1),key,21'(index*319+21'h1abcde),1'(index%2),tag(index),qseq(index)};
 endfunction
 function automatic [47:0] tag(input integer index);tag={16'(index^16'h2345),32'(32'hc1230400+index)};endfunction
 function automatic [39:0] qseq(input integer index);qseq=40'h8100000000+40'(index);endfunction
 function automatic bit queried(input integer index);queried=index%3!=0;endfunction
 ot_qwen_query_stream_queue #(.ENABLE(1),.DEPTH(DEPTH)) dut(.base_clk(clk),.rst_n(rst_n),.core_output_step(step),.query_alloc_v(nv),.query_tuple(tuple_q),.core_credit(credit),.consume_ready(ready),.consume_v(cv),.consume_tuple(cm),.fault(fault));
 always @(negedge clk)begin
  step<=rst_n&&credit&&sent<WORDS;
  ready<=!STALL||cycle>=35&&(cycle%29<17);
 end
 always @(posedge clk)begin
  if(!rst_n)begin sent=0;received=0;cycle=0;nv<=0;posts=0;recorded=0;unallocated=0;done<=0;end
  else begin
   cycle=cycle+1;
   if(step)begin
    if(first_produce<0)first_produce=cycle;last_produce=cycle;
    tuple_q<=packet(sent);nv<=1;sent=sent+1;
   end else paused=paused+1;
   if(dut.pending_post)posts=posts+1;
   if(cv&&ready)begin
    if(cm!==packet(received))$fatal(1,"stream numeric/tag mismatch depth%0d stall%0d index%0d",DEPTH,STALL,received);
    if(first_pop<0)first_pop=cycle;last_pop=cycle;received=received+1;
    recorded=recorded+1;
   end
   if(STALL&&cycle==30&&(recorded!=0||posts!=DEPTH))$fatal(1,"posting fabricated query recording or failed full reservation");
   #1;if(fault)$fatal(1,"stream reservation fault");if(dut.count>peak)peak=dut.count;
   if(received==WORDS&&!done)begin
    if(recorded!=WORDS||unallocated!=0||posts!=WORDS||dut.count!=0)$fatal(1,"stream counts/drain wrong");
    if(!STALL&&DEPTH==8&&last_produce-first_produce!=WORDS-1)$fatal(1,"stream unit rate lost");
    done=1;$display("QUERY_STREAM depth=%0d stall=%0d words=%0d real_records=%0d unallocated=%0d posts=%0d interval=%0d first_pop_delta=%0d peak=%0d paused=%0d last_pop=%0d",DEPTH,STALL,received,recorded,unallocated,posts,last_produce-first_produce,first_pop-first_produce,peak,paused,last_pop);
   end
  end
 end
endmodule
module query_reset(input wire clk,rst_n,output reg done=0);
 reg reset=0,step=0,nv=0,ready=0;reg [209:0] tuple_q=0;
 wire credit,cv,fault;wire [209:0] ct;
 localparam [209:0] OLD={4'hf,96'hdeadbeefc123456789abcdef,21'h1abcde,1'b0,16'h1234,32'hc1230001,40'h8100000000};
 localparam [209:0] NEW={4'h5,96'hfed123abc4569876543210ab,21'h176543,1'b1,16'h5678,32'hc9870001,40'hf100000001};
 ot_qwen_query_stream_queue #(.ENABLE(1),.DEPTH(8)) dut(.base_clk(clk),.rst_n(reset),.core_output_step(step),.query_alloc_v(nv),.query_tuple(tuple_q),.core_credit(credit),.consume_ready(ready),.consume_v(cv),.consume_tuple(ct),.fault(fault));
 initial begin
  wait(rst_n);@(negedge clk);reset=1;
  repeat(8)begin @(negedge clk);step=credit;@(posedge clk);if(step)begin tuple_q<=OLD;nv<=1;end end
  @(negedge clk);step=0;repeat(3)@(negedge clk);
  if(!cv)$fatal(1,"query reset scene did not fill");reset=0;nv=0;step=0;
  repeat(2)@(negedge clk);reset=1;ready=1;
  repeat(3)begin @(posedge clk);#1;if(cv||fault)$fatal(1,"query reset leaked old tuple");end
  @(negedge clk);step=1;@(posedge clk);tuple_q<=NEW;nv<=1;
  @(negedge clk);step=0;wait(cv);if(ct!==NEW)$fatal(1,"query reset fresh full tuple mismatch");
  @(posedge clk);#1;if(cv||fault)$fatal(1,"query reset fresh record failed");done=1;$display("QUERY_STREAM local reset flushed old unrecorded tuples before fresh full210 packet");
 end
endmodule
module tb_qwen_query_stream_queue;
 reg clk=0;always #5 clk=~clk;reg rst_n=0;wire [4:0] done;
 query_case #(.DEPTH(2)) a(clk,rst_n,done[0]);query_case #(.DEPTH(8)) b(clk,rst_n,done[1]);
 query_case #(.DEPTH(2),.STALL(1)) c(clk,rst_n,done[2]);query_case #(.DEPTH(8),.STALL(1)) d(clk,rst_n,done[3]);

 query_reset e(clk,rst_n,done[4]);
 initial begin repeat(4)@(negedge clk);rst_n=1;wait(&done);$display("PASS live query queue full210 fields/record-only-pop/full stalls");$finish;end
 initial begin #200000;$fatal(1,"stream timeout");end
endmodule
