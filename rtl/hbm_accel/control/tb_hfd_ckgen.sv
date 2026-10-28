`timescale 1ns/1ps
// hfd_ckgen reset release (H-HARDEN 10-15): with the PLL simulation model, every por_<domain> stays asserted until
// por_n AND lock, then releases on exactly the 2nd rising edge of its OWN domain clock; por_n low asserts all four
// asynchronously; re-lock repeats the release.  (The analog PLL is the modelled hard core; only the model is here.)
// DIE-HBM-10 10-28 reset contract: release on exactly own edge 2 + HOLD (HOLD 64) after arm, so >= 64 clocked edges in
// reset; mid-run re-assertion (por_n glitches of 0.05..1.94 ns at varied phases, and PLL lock loss) restarts the full
// window.  Mutants (bench_ckgen.sh): MUT=1 one-flop release, MUT=2 short window (HOLD 8): both must FAIL.
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
 localparam integer RELEASE=2+64, CONTRACT=64;
 integer edges[0:3],checks=0,minheld=1000000;
 genvar g;
 for(g=0;g<4;g=g+1)begin:E
  always @(posedge ck[g]) if(dut.u_pll.locked&&por_n) edges[g]=edges[g]+1; else edges[g]=0;
  always @(posedge po[g]) begin
   if(edges[g]<CONTRACT)$fatal(1,"domain%0d reset window %0d edges < contract %0d",g,edges[g],CONTRACT);
   if(edges[g]!==RELEASE)$fatal(1,"domain%0d released after %0d own edges (want %0d)",g,edges[g],RELEASE);
   if(edges[g]<minheld)minheld=edges[g];
   checks=checks+1;
  end
 end
 task automatic cycle_reset;begin
  #3.3;por_n=0;#0.01;if(po!==4'b0)$fatal(1,"por_n low must assert all resets asynchronously");checks=checks+1;
  #40;if(po!==4'b0)$fatal(1,"released while por_n low");checks=checks+1;
  por_n=1;wait(dut.u_pll.locked);if(po!==4'b0)$fatal(1,"released before lock");checks=checks+1;
  #100;if(po!==4'b1111)$fatal(1,"not all released 100 ns after lock: %b",po);checks=checks+1;
 end endtask
 // mid-run re-assertion: a por_n glitch (any width) after release must assert at once and hold the full window again
 task automatic glitch(input real w, input real ph);begin
  #(20+ph);por_n=0;#0.01;if(po!==4'b0)$fatal(1,"mid-run por_n glitch must assert all resets");checks=checks+1;
  #(w);por_n=1;wait(dut.u_pll.locked);
  #100;if(po!==4'b1111)$fatal(1,"not re-released after glitch: %b",po);checks=checks+1;
 end endtask
 // PLL lock loss mid-run: same window
 task automatic lockloss;begin
  #17.3;force dut.u_pll.locked=1'b0;#0.01;if(po!==4'b0)$fatal(1,"lock loss must assert all resets");checks=checks+1;
  #3.1;release dut.u_pll.locked;
  #100;if(po!==4'b1111)$fatal(1,"not re-released after lock loss: %b",po);checks=checks+1;
 end endtask
 initial begin
  for(integer k=0;k<4;k=k+1)edges[k]=0;
  repeat(3)cycle_reset;
  for(integer k=0;k<8;k=k+1)glitch(0.05+k*0.27,k*0.137);
  repeat(2)lockloss;
  $display("CKGEN_PASS checks=%0d domains=4 release_edges=%0d min_reset_edges=%0d contract=%0d async_assert=1 midrun_glitches=8 lockloss=2",checks,RELEASE,minheld,CONTRACT);$finish;
 end
endmodule
