`timescale 1ns/1ps
// hfd_ckgen reset release (H-HARDEN 10-15): with the PLL simulation model, every por_<domain> stays asserted until
// por_n AND lock, then releases on exactly the 2nd rising edge of its OWN domain clock; por_n low asserts all four
// asynchronously; re-lock repeats the release.  (The analog PLL is the modelled hard core; only the model is here.)
module ot_hbm_pll_bb(input wire refclk, reset_n, output reg clk_stream,clk_serial,clk_hbm,clk_link,locked);
 initial begin clk_stream=0;clk_serial=0;clk_hbm=0;clk_link=0;locked=0;end
 integer acquisition=0;
 bit no_clock, no_lock;
 initial begin no_clock=$test$plusargs("NO_CLOCK"); no_lock=$test$plusargs("NO_LOCK"); end
 always #0.416667 if(!no_clock) clk_stream=~clk_stream;
 always #0.555556 if(!no_clock) clk_serial=~clk_serial;
 always #0.512 if(!no_clock) clk_hbm=~clk_hbm;
 always #0.416667 if(!no_clock) clk_link=~clk_link;
 always @(posedge refclk or negedge reset_n)
  if(!reset_n) begin acquisition<=0;locked<=0;end
  else if(acquisition==3) locked<=!no_lock;
  else acquisition<=acquisition+1;
endmodule
