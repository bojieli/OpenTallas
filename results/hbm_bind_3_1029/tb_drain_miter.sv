`timescale 1ns/1ps
module tb;
 localparam N=16,NS=2,LWB=15,AW=24;
 reg clk=0;always #0.416667 clk=~clk;
 reg rst_n=0;reg [NS-1:0] sr_v=0;reg [NS*LWB-1:0] sr_addr=0;
 reg [N-1:0] lw=0;reg [N*AW-1:0] lwa=0;reg [N*32-1:0] lwd=0;
 wire [NS*256-1:0] g_d,c_d;wire [NS-1:0] g_v,c_v;wire g_f,c_f;
 integer checks=0,active=0,mutant=0;
 wire [N*32-1:0] cand_write=lwd ^ (mutant ? 512'd1 : 512'd0);
 ot_hgi_su_lgroup2 #(.N(N),.M(16),.LWB(LWB),.AW(AW),.NLW(N),.MACRO(0),.NS(NS)) gold(
 .clk(clk),.rst_n(rst_n),.rq(16'd0),.rr(16'd0),.ra(384'd0),.rd(),
 .sr_v(sr_v),.sr_addr(sr_addr),.sr_d(g_d),.sr_rv(g_v),.sw_v(2'd0),.sw_addr(30'd0),.sw_mask(16'd0),.sw_d(512'd0),
 .lw(lw),.lwa(lwa),.lwd(lwd),.s1_v(1'b0),.s1_a(15'd0),.s1_d(32'd0),.flt(g_f));
 ot_hgi_su_lgroup2_drain #(.N(N),.M(16),.LWB(LWB),.AW(AW),.NLW(N),.MACRO(0),.NS(NS)) cand(
 .clk(clk),.rst_n(rst_n),.sr_v(sr_v),.sr_addr(sr_addr),.sr_d(c_d),.sr_rv(c_v),.lw(lw),.lwa(lwa),.lwd(cand_write),.flt(c_f));
 task tick;begin
  @(posedge clk);#0.001;
  if(g_v!==c_v || g_f!==c_f || (|g_v && g_d!==c_d))begin
   if(mutant)begin $display("CAUGHT drain write mutant checks=%0d",checks);$finish;end
   else $fatal(1,"DRAIN_MISMATCH checks=%0d",checks);
  end
  checks++;
  if(|g_v && |g_d)active++;
  @(negedge clk);
 end endtask
 initial begin
  mutant=$test$plusargs("MUTANT");repeat(4)tick();rst_n=1;
  // All 16 write lanes, full-depth addresses, two independent eight-word drains.
  for(integer phase=0;phase<3;phase++)begin
   for(integer row=0;row<2048;row++)begin
    lw='1;sr_v=0;
    for(integer lane=0;lane<N;lane++)begin lwa[AW*lane+:AW]=24'(row*16+lane);lwd[32*lane+:32]=32'h3f000000 ^32'(row*31+lane*17+phase);end
    tick();
   end
   lw=0;
   for(integer row=0;row<2048;row++)begin sr_v=3;sr_addr={LWB'(row*16+8),LWB'(row*16)};tick();end
   sr_v=0;tick();rst_n=0;tick();rst_n=1;tick();
  end
  // Two writes sharing a bank, and two drain sectors requesting different rows of one bank.
  lw=3;lwa=0;lwd=512'd23;tick();lw=0;sr_v=3;sr_addr={15'd16,15'd0};tick();sr_v=0;tick();
  if(mutant)$fatal(1,"MUTANT_NOT_CAUGHT");
  if(active<6000 || !g_f)$fatal(1,"DRAIN_COVERAGE active=%0d fault=%0d",active,g_f);
  $display("PASS drain lockstep checks=%0d active_nonzero=%0d full_depth=32768 midreset=3 fault=1 cycles_added=0",checks,active);$finish;
 end
endmodule
