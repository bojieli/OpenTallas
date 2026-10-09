`timescale 1ns/1ps
// Test-only analog stand-in: never a production frequency/timing claim.
module ot_hbm_pll_bb(input wire refclk, reset_n,
 output reg clk_stream,clk_serial,clk_hbm,clk_link,locked);
 initial begin clk_stream=0;clk_serial=0;clk_hbm=0;clk_link=0;locked=0;end
 integer acquisition=0;
 reg stop_hbm=0,stop_link=0;
 always #0.416667 clk_stream=~clk_stream;
 always #0.555556 clk_serial=~clk_serial;
 always #0.512 if(!stop_hbm) clk_hbm=~clk_hbm;
 always #0.416667 if(!stop_link) clk_link=~clk_link;
 always @(posedge refclk or negedge reset_n)
  if(!reset_n) begin acquisition<=0;locked<=0;end
  else if(acquisition==3) locked<=1;
  else acquisition<=acquisition+1;
endmodule

module tb;
 reg aon_clk=0,refclk=0,por_n=0,power_good=0;
 reg [3:0] phy_ready=0; reg [8:0] links_ready=0;
 reg bist_done=0,bist_pass=0,fatal_error=0,requalify=0;
 wire clk_stream,clk_serial,clk_hbm,clk_link,pll_lock;
 wire [3:0] phy_reset_n,state; wire [8:0] link_reset_n;
 wire coll_reset_stream_n,coll_reset_serial_n,cmd_reset_stream_n,cmd_reset_serial_n,ready;
 ot_hbm_production_clock_control_ready_aon_bound dut(.*);
 always #2 refclk=~refclk;
 always #1.5 aon_clk=~aon_clk;
 always @(posedge ready) if(!cmd_reset_stream_n || !cmd_reset_serial_n || !(&phy_reset_n) || !(&link_reset_n))
  $fatal(1,"acceptance before actual destination release");
 initial begin
  #0.1;por_n=0; #3;por_n=1;power_good=1;
  wait(state==2); phy_ready=15;
  wait(state==3); links_ready=511;
  wait(state==4); force dut.clk_serial=0; bist_pass=1;bist_done=1;
  wait(state==5); #15;
  if(ready!==0 || cmd_reset_serial_n!==0 || cmd_reset_stream_n!==1)
   $fatal(1,"stopped serial domain must block readiness");
  release dut.clk_serial;
  wait(ready); #0.1; force dut.pll_lock=0;#0.01;
  if(ready!==0 || phy_reset_n!==0 || link_reset_n!==0 || cmd_reset_stream_n!==0 || cmd_reset_serial_n!==0)
   $fatal(1,"raw lock loss must revoke acceptance and resets asynchronously");
  por_n=0;#0.01;
  if(ready!==0 || phy_reset_n!==0 || link_reset_n!==0 || cmd_reset_stream_n!==0 || cmd_reset_serial_n!==0)
   $fatal(1,"POR must revoke qualification asynchronously");
  $display("PASS AON synchronized ready digital body composition stopped-clock readiness and POR");$finish;
 end
 initial begin #250; $fatal(1,"composition did not qualify");end
endmodule
