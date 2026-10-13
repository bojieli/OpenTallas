`timescale 1ns/1ps
module tb_hbm_b2_xload_command;
 parameter integer MUT=0;
 reg clk=0;always #0.5 clk=~clk;reg rst_n=0,installed=1,cmd_v=0;
 wire cmd_r;reg [191:0] cmd_owner=192'hab37;reg [39:0] cmd_base=0;
 reg [20:0] cmd_n=7168;reg [3:0] cmd_p=4;reg [31:0] cmd_stride=7168;
 reg [1:0] cmd_space=1,cmd_fmt=1;reg [6:0] cmd_xb=0;reg [1:0] cluster_sid=2;
 wire x_v;reg x_rdy=0;wire [39:0] x_base;wire [20:0] x_n;wire [3:0] x_p;
 wire [31:0] x_stride;wire [1:0] x_space,x_fmt;wire [6:0] x_xb;
 reg x_done=0,traffic_drained=0;wire lease_v;wire [191:0] lease_owner;
 wire [1:0] lease_sid;wire lease_mirror,done,fault;
 ot_hbm_b2_xload_command #(.MUT(MUT)) u(.*);
 initial begin
  repeat(4)@(negedge clk);rst_n=1;cmd_base=262144;cmd_v=1;#0.1;
  if(!cmd_r)$fatal(1,"legal mirror command refused");
  @(negedge clk);cmd_v=0;
  // Inputs may change; the outstanding aperture/identity cannot follow them.
  cluster_sid=3;cmd_owner=0;cmd_base=196608;
  repeat(4)begin
   if(!x_v||x_base!=0||lease_sid!=2||!lease_mirror||lease_owner!=192'hab37||fault)$fatal(1,"lease/command capture");
   @(negedge clk);
  end
  x_rdy=1;@(negedge clk);x_rdy=0;x_done=1;@(negedge clk);x_done=0;
  repeat(8)begin if(!lease_v||cmd_r||done)$fatal(1,"early aperture release");@(negedge clk);end
  traffic_drained=1;@(negedge clk);
  if(lease_v||!done||fault)$fatal(1,"drained command did not finish");
  // P8 x7168 mirror is larger than the installed32768word window.
  cmd_base=262144;cmd_p=8;cmd_v=1;#0.1;
  if(cmd_r)$fatal(1,"overflow alias accepted");
  @(negedge clk);if(!fault)$fatal(1,"overflow did not fault");
  $display("PASS_COMMAND mirror_rebased identity_retained drain_required P8_7168_overflow_refused");$finish;
 end
endmodule
