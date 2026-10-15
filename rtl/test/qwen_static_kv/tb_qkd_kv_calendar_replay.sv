`timescale 1ns/1ps
module tb_qkd_kv_calendar_replay;
 parameter integer MUT=0, WIDTH=64;
 reg ck=0;always #0.5 ck=~ck;
 reg rst_n=0,cfg_we=0,cfg_seal=0,start=0;
 reg[5:0]cfg_addr=0;reg[31:0]cfg_time=0;reg[WIDTH-1:0]cfg_payload=0;
 wire[WIDTH-1:0]payload;wire configured,active,done,fault;wire[31:0]cycle;
 qkd_kv_calendar_replay #(.WIDTH(WIDTH),.MUT(MUT))dut(.*);
 function automatic[31:0]t(input integer n);t=n<16?n:16+(n-16)*3+(n%2);endfunction
 function automatic[WIDTH-1:0]word(input integer n);
  word=(64'h4000800010020001 ^ (64'(n+1)<<19)) & {WIDTH{1'b1}};
 endfunction
 task automatic reset;
  rst_n=0;cfg_we=0;cfg_seal=0;start=0;
  repeat(3)@(negedge ck);rst_n=1;repeat(3)@(negedge ck);
 endtask
 task automatic boot;
  for(integer n=0;n<64;n++)begin
   cfg_we=1;cfg_addr=6'(n);cfg_time=t(n);cfg_payload=word(n);@(negedge ck);
  end
  cfg_we=0;cfg_seal=1;cfg_time=200;@(negedge ck);
  cfg_seal=0;repeat(2)@(negedge ck);
  if(!configured||fault)$fatal(1,"BOOT failed");
 endtask
 integer hits=0,checks=0;
 initial begin
  reset();boot();
  // Two starts reuse the immutable image, then asynchronous reset reboots it.
  for(integer pass=0;pass<3;pass++)begin
   if(pass==2)begin reset();boot();end
   start=1;@(negedge ck);start=0;
   // Pin capture is one edge; internal start accepts on the following edge.
   @(negedge ck);
   for(integer c=0;c<200;c++)begin
    reg[WIDTH-1:0]expected;expected=0;
    for(integer n=0;n<64;n++)if(c==t(n))begin expected=word(n);hits++;end
    if(!active||cycle!=c||payload!==expected||fault)
     $fatal(1,"EDGE mismatch pass%0d c%0d gotcycle%0d got%h expected%h fault%0b",pass,c,cycle,payload,expected,fault);
    checks++;@(negedge ck);
   end
   if(active||!done||payload||fault)$fatal(1,"exact STOP mismatch");
   @(negedge ck);if(done)$fatal(1,"DONE is not pulse");
  end
  // Seal must lock configuration; no new image may mutate a running token.
  cfg_we=1;cfg_addr=0;cfg_time=1;cfg_payload=0;
  repeat(2)@(negedge ck);cfg_we=0;
  if(!fault)$fatal(1,"sealed write accepted");
  reset();
  // Missing first word, duplicate/nonmonotone timestamps, start before seal.
  cfg_we=1;cfg_addr=1;@(negedge ck);cfg_we=0;@(negedge ck);
  if(!fault)$fatal(1,"noncontiguous boot accepted");
  reset();cfg_we=1;cfg_addr=0;cfg_time=10;@(negedge ck);
  cfg_addr=1;cfg_time=10;@(negedge ck);cfg_we=0;@(negedge ck);
  if(!fault)$fatal(1,"duplicate timestamp accepted");
  reset();start=1;repeat(2)@(negedge ck);start=0;
  if(!fault||active)$fatal(1,"unsealed start accepted");
  $display("PASS replay width%0d checks%0d events%0d resets/reuse/seal/index/order/start",WIDTH,checks,hits);$finish;
 end
 initial begin #10000;$fatal(1,"timeout");end
endmodule
