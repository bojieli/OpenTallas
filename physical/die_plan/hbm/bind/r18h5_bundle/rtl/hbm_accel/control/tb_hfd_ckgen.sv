`timescale 1ns/1ps
// hfd_ckgen reset release (H-HARDEN 10-15): with the PLL simulation model, every por_<domain> stays asserted until
// por_n AND lock, then releases on exactly the 2nd rising edge of its OWN domain clock; por_n low asserts all four
// asynchronously; re-lock repeats the release.  (The analog PLL is the modelled hard core; only the model is here.)
module ot_hbm_pll_bb(input wire refclk, reset_n, output reg clk_stream,clk_serial,clk_hbm,clk_link,locked);
 initial begin clk_stream=0;clk_serial=0;clk_hbm=0;clk_link=0;locked=0;end
 integer acquisition=0;
 always #0.416667 clk_stream=~clk_stream;
 always #0.555556 clk_serial=~clk_serial;
 always #0.512 clk_hbm=~clk_hbm;
 always #0.416667 clk_link=~clk_link;
 always @(posedge refclk or negedge reset_n)
  if(!reset_n) begin acquisition<=0;locked<=0;end
  else if(acquisition==3) locked<=1;
  else acquisition<=acquisition+1;
endmodule
module tb_hfd_ckgen;
 reg refclk=0,por_n=0;always #5 refclk=~refclk;
 wire pll_stream,pll_serial,pll_hbm,pll_link,por_stream,por_serial,por_hbm,por_link;
 hfd_ckgen dut(.*);
 wire [3:0] ck={pll_link,pll_hbm,pll_serial,pll_stream}, po={por_link,por_hbm,por_serial,por_stream};
 integer edges[0:3],checks=0;
 genvar g;
 for(g=0;g<4;g=g+1)begin:E
  always @(posedge ck[g]) if(dut.u_pll.locked&&por_n) edges[g]=edges[g]+1; else edges[g]=0;
  always @(posedge po[g]) begin
   if(edges[g]!==2)$fatal(1,"domain%0d released after %0d own edges (want 2)",g,edges[g]);
   checks=checks+1;
  end
 end
 task automatic cycle_reset;begin
  #3.3;por_n=0;#0.01;if(po!==4'b0)$fatal(1,"por_n low must assert all resets asynchronously");checks=checks+1;
  #40;if(po!==4'b0)$fatal(1,"released while por_n low");checks=checks+1;
  por_n=1;wait(dut.u_pll.locked);if(po!==4'b0)$fatal(1,"released before lock");checks=checks+1;
  #10;if(po!==4'b1111)$fatal(1,"not all released 10 ns after lock: %b",po);checks=checks+1;
 end endtask
 initial begin
  for(integer k=0;k<4;k=k+1)edges[k]=0;
  repeat(3)cycle_reset;
  $display("CKGEN_PASS checks=%0d domains=4 release_edges=2 async_assert=1",checks);$finish;
 end
endmodule
