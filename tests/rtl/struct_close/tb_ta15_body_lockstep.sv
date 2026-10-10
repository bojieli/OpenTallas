`timescale 1ns/1ps
// struct-close 2026-10-09: TA15 production body "-cl" (ot_hbm_production_clock_digital_body_cl.sv) in LOCK-STEP with the
// original composition (ot_hbm_production_clock_control.sv renamed ot_hbm_production_clock_control_ref by the runner).
// Both get the same AON / refclk, POR, power_good, readiness inputs, BIST, fatal_error, requalify, PLL lock loss and
// stopped destination clocks (random, seeded).  Every output (ready, state, all 17 destination resets, pll_lock) is
// compared at every half-cycle of the fastest clock; any difference FAILS.
module ot_hbm_pll_bb(input wire refclk, reset_n,
 output reg clk_stream,clk_serial,clk_hbm,clk_link,locked);
 initial begin clk_stream=0;clk_serial=0;clk_hbm=0;clk_link=0;locked=0;end
 integer acquisition=0;
 always #0.416667 if(!tb.stop_stream) clk_stream=~clk_stream;
 always #0.555556 if(!tb.stop_serial) clk_serial=~clk_serial;
 always #0.512 if(!tb.stop_hbm) clk_hbm=~clk_hbm;
 always #0.416667 if(!tb.stop_link) clk_link=~clk_link;
 always @(posedge refclk or negedge reset_n)
  if(!reset_n) begin acquisition<=0;locked<=0;end
  else if(tb.lock_loss) begin acquisition<=0;locked<=0;end
  else if(acquisition==3) locked<=1;
  else acquisition<=acquisition+1;
endmodule
module tb;
 parameter integer SEED=1, NEV=400;
 reg aon_clk=0,refclk=0,por_n=0,power_good=0,bist_done=0,bist_pass=0,fatal_error=0,requalify=0,lock_loss=0;
 reg stop_stream=0,stop_serial=0,stop_hbm=0,stop_link=0;
 reg [3:0] phy_ready=0; reg [8:0] links_ready=0;
 wire [3:0] st_a,st_b,phy_a,phy_b; wire [8:0] lnk_a,lnk_b;
 wire [3:0] c_a,c_b; wire rdy_a,rdy_b,lk_a,lk_b;
 wire cs_a,cser_a,ms_a,mser_a,cs_b,cser_b,ms_b,mser_b;
 wire [3:0] dk_a,dk_b;
 ot_hbm_production_clock_control_ref ref_i(.aon_clk(aon_clk),.refclk(refclk),.por_n(por_n),.power_good(power_good),
  .phy_ready(phy_ready),.links_ready(links_ready),.bist_done(bist_done),.bist_pass(bist_pass),.fatal_error(fatal_error),
  .requalify(requalify),.clk_stream(dk_a[0]),.clk_serial(dk_a[1]),.clk_hbm(dk_a[2]),.clk_link(dk_a[3]),.pll_lock(lk_a),
  .phy_reset_n(phy_a),.link_reset_n(lnk_a),.coll_reset_stream_n(cs_a),.coll_reset_serial_n(cser_a),
  .cmd_reset_stream_n(ms_a),.cmd_reset_serial_n(mser_a),.ready(rdy_a),.state(st_a));
 ot_hbm_production_clock_control dut(.aon_clk(aon_clk),.refclk(refclk),.por_n(por_n),.power_good(power_good),
  .phy_ready(phy_ready),.links_ready(links_ready),.bist_done(bist_done),.bist_pass(bist_pass),.fatal_error(fatal_error),
  .requalify(requalify),.clk_stream(dk_b[0]),.clk_serial(dk_b[1]),.clk_hbm(dk_b[2]),.clk_link(dk_b[3]),.pll_lock(lk_b),
  .phy_reset_n(phy_b),.link_reset_n(lnk_b),.coll_reset_stream_n(cs_b),.coll_reset_serial_n(cser_b),
  .cmd_reset_stream_n(ms_b),.cmd_reset_serial_n(mser_b),.ready(rdy_b),.state(st_b));
 always #2 refclk=~refclk;
 always #1.5 aon_clk=~aon_clk;
 integer bad=0, nready=0, nrise=0, ev, rs, k;
 wire [31:0] va={rdy_a,lk_a,st_a,phy_a,lnk_a,cs_a,cser_a,ms_a,mser_a};
 wire [31:0] vb={rdy_b,lk_b,st_b,phy_b,lnk_b,cs_b,cser_b,ms_b,mser_b};
 always #0.2 if (va !== vb) begin bad=bad+1; if (bad<5) $display("MISMATCH t=%0t ref %h cl %h", $time, va, vb); end
 always @(posedge rdy_a) nrise=nrise+1;
 always @(posedge aon_clk) if (rdy_a) nready=nready+1;
 initial begin
  rs=SEED;
  #0.1; #3; por_n=1; power_good=1;
  for (ev=0; ev<NEV; ev=ev+1) begin
   // let the sequence progress, then perturb
   phy_ready=15; links_ready=511; bist_done=1; bist_pass=1;
   #($urandom(rs)%60+10);
   k=$urandom(rs)%9;
   case (k)
    0: begin por_n=0; #($urandom(rs)%5+1); por_n=1; end
    1: begin lock_loss=1; #($urandom(rs)%9+4); lock_loss=0; end
    2: begin fatal_error=1; #3; fatal_error=0; #($urandom(rs)%10+3); requalify=1; #6; requalify=0; end
    3: begin phy_ready=$urandom(rs)%15; #($urandom(rs)%12+3); end
    4: begin links_ready=$urandom(rs)%511; #($urandom(rs)%12+3); end
    5: begin stop_serial=1; #($urandom(rs)%20+2); stop_serial=0; end
    6: begin stop_hbm=1; stop_link=1; #($urandom(rs)%20+2); stop_hbm=0; stop_link=0; end
    7: begin power_good=0; #($urandom(rs)%6+3); power_good=1; #6; requalify=1; #6; requalify=0; end
    8: begin bist_pass=0; #4; requalify=1; #6; requalify=0; end
   endcase
   if (st_a==6) begin requalify=1; #6; requalify=0; end
  end
  #40;
  if (bad==0 && nrise>10) $display("TA15_LOCKSTEP PASS events=%0d ready_rises=%0d ready_cycles=%0d", NEV, nrise, nready);
  else $display("TA15_LOCKSTEP FAIL mismatches=%0d ready_rises=%0d", bad, nrise);
  $finish;
 end
endmodule
