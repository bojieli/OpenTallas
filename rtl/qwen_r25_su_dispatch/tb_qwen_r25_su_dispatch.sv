`timescale 1ns/1ps
module tb_qwen_r25_su_dispatch #(parameter OWNER_W=74);
 reg clk=0;always #0.555556 clk=~clk;
 reg rst_n=0,launch_v=0;wire launch_rdy;
 reg [1:0] launch_checked=3;reg [OWNER_W-1:0] launch_owner={20'd8191,18'h3ffff,4'ha,32'h12345678};
 reg [11:0] launch_pc=17;reg [12:0] launch_count=1;
 reg [19:0] launch_position=8191;reg [2:0] launch_queries=4;
 wire rom_v;reg rom_rdy=1;wire [11:0] rom_pc;
 reg rom_out_v=0;wire rom_out_rdy;reg [11:0] rom_out_pc=17;
 reg [2759:0] rom_words=0;reg [3:0] rom_quarters=15;
 reg rom_valid=1,rom_window=1;reg [19:0] rom_row0=8192;reg [15:0] rom_rows=32;
 wire [3:0] cmd_v;reg [3:0] cmd_rdy=15;wire [2759:0] cmd_words;
 wire [OWNER_W-1:0] cmd_owner;wire [11:0] cmd_pc;wire [1:0] cmd_query;
 wire [19:0] cmd_position;wire [20:0] cmd_valid_length;
 reg [3:0] done_v=0;reg [4*OWNER_W-1:0] done_owner=0;
 reg [47:0] done_pc=0;reg [7:0] done_query=0;
 wire finished_v,fault;reg finished_rdy=0;
 ot_qwen_r25_su_dispatch #(.ENABLE(1),.OWNER_W(OWNER_W)) dut(.*);
 integer q,seen=0,fetches=0,cycles=0;
 always @(negedge clk)if(rst_n)begin
  cycles=cycles+1;if(cycles>200)$fatal(1,"functional deadlock");
  rom_out_v=rom_out_rdy;rom_out_pc=rom_pc;
  if(rom_v)fetches=fetches+1;
  done_v=0;
  if(|cmd_v)begin
   if(cmd_owner!=launch_owner||cmd_pc!=17||cmd_query==0||cmd_position!=8191+cmd_query||cmd_valid_length!=8192+cmd_query)$fatal(1,"identity/length");
   for(q=0;q<4;q=q+1)begin
    if(cmd_words[q*690+16+:16]!=cmd_query)$fatal(1,"native NIN clipping");
    done_owner[q*OWNER_W+:OWNER_W]=cmd_owner;done_pc[q*12+:12]=cmd_pc;done_query[q*2+:2]=cmd_query;
   end
   done_v=cmd_v;seen=seen+1;
  end
 end
 initial begin
  repeat(3)@(posedge clk);@(negedge clk);rst_n=1;launch_v=1;
  @(negedge clk);launch_v=0;
  wait(finished_v);if(fault||seen!=3||fetches!=4)$fatal(1,"p4 schedule");
  repeat(3)@(negedge clk);if(!finished_v)$fatal(1,"completion not held");
  // Foreign late completion must fence even while finished is held.
  #0.02;done_v=1;done_owner=0;@(posedge clk);#0.01;
  if(!fault||finished_v)$fatal(1,"foreign completion admitted");
  $display("PASS_QWEN_DISPATCH_P4 native690 quarters4 queries4 fetches4 nonempty3 tail_NIN1_2_3 checked_completion_negative");$finish;
 end
endmodule
