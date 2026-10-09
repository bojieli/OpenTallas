`timescale 1ns/1ps
module tb_qwen_r25_cp_native_launch;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,warm_abort=0,map_v=0,req_v=0,vm_ready=0,launch_rdy=0;
 reg native_finished_v=0,native_fault=0,complete_rdy=0;
 reg [2:0] map_slot=0,req_queries=1;
 reg [1:0] map_checked=3,req_checked=3,vm_checked=3;
 reg [31:0] map_cp_pc=32'h87654321,req_cp_pc=32'h87654321;
 reg [11:0] map_rom_pc=19;reg [12:0] map_count=23;
 reg [73:0] req_owner,vm_owner,native_finished_owner=0;
 wire map_rdy,req_rdy,launch_v,native_finished_rdy,complete_v,fault;
 wire [1:0] launch_checked;wire [73:0] launch_owner,complete_owner;
 wire [11:0] launch_pc;wire [12:0] launch_count;wire [19:0] launch_position;
 wire [2:0] launch_queries;
 ot_qwen_r25_cp_native_launch #(.ENABLE(1)) dut(.*);
 integer cases=0;
 task tick;begin @(posedge clk);#1;end endtask
 task reset;
 begin
  @(negedge clk);rst_n=0;map_v=0;req_v=0;vm_ready=0;warm_abort=0;
  launch_rdy=0;native_finished_v=0;native_fault=0;complete_rdy=0;
  req_checked=3;map_checked=3;vm_checked=3;map_slot=0;
  map_cp_pc=32'h87654321;req_cp_pc=32'h87654321;map_rom_pc=19;map_count=23;req_queries=1;
  req_owner={20'd8192,18'd151935,4'd13,32'hfeedabcd};vm_owner=req_owner;
  tick;@(negedge clk);rst_n=1;tick;
 end endtask
 task install;
 begin @(negedge clk);map_v=1;tick;@(negedge clk);map_v=0;tick;end
 endtask
 task request;
 begin @(negedge clk);req_v=1;vm_ready=1;tick;@(negedge clk);req_v=0;tick;end
 endtask
 task expect_fault;
 begin tick;if(!fault||launch_v||complete_v)$fatal(1,"expected quarantine case%0d",cases);cases=cases+1;end
 endtask
 task expect_launch;
 begin
  if(!launch_v||launch_checked!=3||launch_owner!==req_owner||launch_pc!=19||
     launch_count!=23||launch_position!=8192||launch_queries!=1)$fatal(1,"actual launch mismatch");
 end endtask
 initial begin
  reset;install;request;expect_launch;
  repeat(3)begin tick;expect_launch;end
  @(negedge clk);launch_rdy=1;tick;@(negedge clk);launch_rdy=0;
  if(complete_v||!native_finished_rdy)$fatal(1,"manufactured completion");
  repeat(3)tick;
  @(negedge clk);native_finished_owner=req_owner;native_finished_v=1;tick;
  @(negedge clk);native_finished_v=0;
  if(!complete_v||complete_owner!==req_owner)$fatal(1,"actual retirement mismatch");
  repeat(3)begin tick;if(!complete_v||complete_owner!==req_owner)$fatal(1,"completion stall");end
  @(negedge clk);complete_rdy=1;tick;
  if(!req_rdy||map_rdy)$fatal(1,"immutable mapping lock missing");cases=cases+1;
  reset;install;req_cp_pc=32'hdeadbeef;request;expect_fault;
  reset;install;vm_owner[53]=~vm_owner[53];request;expect_fault;
  reset;install;req_queries=4;request;expect_fault;
  reset;install;vm_checked=0;request;expect_fault;
  reset;install;req_checked=0;request;expect_fault;
  reset;install;req_owner[53:36]=18'd151936;vm_owner=req_owner;request;expect_fault;
  reset;install;req_owner[73:54]=20'd8224;vm_owner=req_owner;request;expect_fault;
  reset;install;map_slot=1;install;expect_fault;
  reset;map_rom_pc=4095;map_count=2;install;expect_fault;
  reset;install;request;expect_launch;
  @(negedge clk);launch_rdy=1;tick;@(negedge clk);launch_rdy=0;
  native_finished_owner=req_owner^74'd1;native_finished_v=1;tick;expect_fault;
  reset;install;request;expect_launch;
  @(negedge clk);dut.g_on.owner_lo=dut.g_on.owner_lo^72'd1;tick;expect_launch;cases=cases+1;
  reset;install;request;expect_launch;
  @(negedge clk);dut.g_on.owner_lo=dut.g_on.owner_lo^72'd3;tick;expect_fault;
  reset;install;request;expect_launch;@(negedge clk);warm_abort=1;tick;expect_fault;
  $display("PASS actual CP32/native690 launch %0d cases",cases);$finish;
 end
endmodule
