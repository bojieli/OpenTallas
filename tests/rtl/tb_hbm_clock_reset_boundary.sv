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
 reg refclk=0,por_n=0,pll_reset_n=0;
 reg [3:0] phy_reset_intent_n=0;
 reg [8:0] link_reset_intent_n=0;
 reg coll_reset_intent_n=0,cmd_reset_intent_n=0;
 wire clk_stream,clk_serial,clk_hbm,clk_link,pll_lock;
 wire [3:0] phy_reset_n;
 wire [8:0] link_reset_n;
 wire coll_reset_stream_n,coll_reset_serial_n,cmd_reset_stream_n,cmd_reset_serial_n;
 ot_hbm_clock_reset_boundary dut(.*);
 always #2 refclk=~refclk;
 integer counts[0:16];
 integer j;
 reg [16:0] expected=0;
 wire [16:0] resets={cmd_reset_serial_n,cmd_reset_stream_n,
   coll_reset_serial_n,coll_reset_stream_n,link_reset_n,phy_reset_n};
 wire qualified=por_n && pll_reset_n && pll_lock;
 wire [16:0] intents={{2{cmd_reset_intent_n}},{2{coll_reset_intent_n}},link_reset_intent_n,phy_reset_intent_n};
 // Independent edge-count oracle: every endpoint must wait exactly 3 edges.
 for(genvar k=0;k<17;k=k+1) begin:oracle
  wire c=(k<4)?clk_hbm:(k<13)?clk_link:(k==13 || k==15)?clk_stream:clk_serial;
  wire q=qualified && intents[k];
  initial counts[k]=0;
  always @(posedge c or negedge q) begin
   if(!q) begin counts[k]=0;expected[k]=0;end
   else begin if(counts[k]<3) counts[k]=counts[k]+1;expected[k]=(counts[k]>=3);end
   #0.002;
   if(resets[k]!==expected[k]) $fatal(1,"endpoint %0d got %b expected %b edge %0d",k,resets[k],expected[k],counts[k]);
  end
 end
 task all_asserted;
  begin #0.01;if(resets!==17'b0) $fatal(1,"asynchronous reset missing %h",resets);end
 endtask
 initial begin
  #0.1;por_n=1;pll_reset_n=1;
  phy_reset_intent_n=15;link_reset_intent_n=511;
  coll_reset_intent_n=1;cmd_reset_intent_n=0;
  #5;if(pll_lock!==0 || resets!==0) $fatal(1,"release before acquisition");
  wait(pll_lock);#4;
  if(resets[14:0]!==15'h7fff || resets[16:15]!==0) $fatal(1,"boot intent ordering");
  cmd_reset_intent_n=1;#4;
  if(resets!==17'h1ffff) $fatal(1,"command release missing");
  // Independent endpoint loss must not reset healthy siblings.
  phy_reset_intent_n[2]=0;link_reset_intent_n[8]=0;#0.01;
  if(phy_reset_n!==4'b1011 || link_reset_n!==9'b011111111) $fatal(1,"endpoint isolation");
  phy_reset_intent_n[2]=1;link_reset_intent_n[8]=1;#4;
  // Stop actual destination clocks before losing lock: no edge may be
  // needed to assert reset, and no release can occur without future edges.
  dut.pll.stop_hbm=1;dut.pll.stop_link=1;
  #0.07;force dut.pll.locked=0;all_asserted();
  release dut.pll.locked;#5;
  if(phy_reset_n!==0 || link_reset_n!==0) $fatal(1,"stopped clock released reset");
  dut.pll.stop_hbm=0;dut.pll.stop_link=0;#4;
  if(resets!==17'h1ffff) $fatal(1,"reacquisition release missing");
  pll_reset_n=0;all_asserted();pll_reset_n=1;wait(pll_lock);#4;
  por_n=0;all_asserted();
  $display("PASS clock/reset boundary: 17 endpoints, 3-edge release, async lock/POR assertion, stopped clocks, boot isolation");
  $finish;
 end
 initial begin #100;$fatal(1,"bench failed to complete");end
endmodule
