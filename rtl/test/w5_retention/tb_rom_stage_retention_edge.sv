`timescale 1ns/1ps
// Full NB2 retention map and actual replay/reset synchronizer; no arithmetic array.
module tb_rom_stage_retention_edge;
 parameter integer FIX = 0;
 reg clk=0;
 always #0.5 clk=~clk;
 reg rst_n=0, cfg_v=0, pwr_good=0, iso_n=0, arst_n=0;
 reg [4:0] cfg_a=0;
 reg [47:0] cfg_d=0;
 wire rq, ready, dbusy, dack, ack, rdy, e_rst_n, e_cfg_v, e_go;
 wire [4:0] rp_a, e_cfg_a;
 wire [47:0] rp_d, e_cfg_d;
 wire el_ready, el_busy;
 ot_v41_rom_pg_eao #(.RETENTION_EDGE_WRITE(FIX), .NB(2)) ao (
 .a_clk(clk),.rst_n(rst_n),.cfg_v(cfg_v),.cfg_a(cfg_a),.cfg_d(cfg_d),.go(1'b0),
 .pwr_good(pwr_good),.iso_n(iso_n),.e_pv(2'b0),.e_pval(64'b0),.e_prow(32'b0),
 .e_pseg(10'b0),.e_pnseg(10'b0),.e_perr(2'b0),.e_ppos(6'b0),.e_busy(1'b0),.e_fault(1'b0),
 .dbusy(dbusy),.dack(dack),.ack(ack),.rdy(rdy),.rq(rq),.cdc_rp_a(rp_a),.cdc_rp_d(rp_d),
 .ready(ready),.el_ready(el_ready),.el_busy(el_busy));
 ot_v41_rom_pg_dif #(.NB(2)) dif (
 .e_clk(clk),.arst_n(arst_n),.cfg_v(1'b0),.cfg_a(5'b0),.cfg_d(48'b0),.go(1'b0),
 .rq(rq),.rp_a(rp_a),.rp_d(rp_d),.ready_a(ready),.e_busy(1'b0),.e_pv(2'b0),
 .e_rst_n(e_rst_n),.e_cfg_v(e_cfg_v),.e_cfg_a(e_cfg_a),.e_cfg_d(e_cfg_d),.e_go(e_go),
 .dbusy(dbusy),.dack(dack),.ack(ack),.rdy(rdy));
 function automatic [47:0] mask(input integer a);
  integer w;
  begin w=(a<8)?43:(a<16)?23:(a==16)?20:16; mask=(48'h1<<w)-1; end
 endfunction
 integer target, receipts=0, total=0;
 reg [24:0] retained_valid, retained_dirty;
 reg [47:0] expected;
 always @(posedge clk) if (rst_n && e_cfg_v) begin
  if (e_cfg_a !== target[4:0] || e_cfg_d !== expected)
   $fatal(1,"replay tuple mismatch addr=%0d expected=%h got=%h",e_cfg_a,expected,e_cfg_d);
  receipts=receipts+1; total=total+1;
 end
 initial begin
  for(target=0;target<25;target=target+1) begin
   @(negedge clk); rst_n=0; arst_n=0; pwr_good=0; iso_n=0; cfg_v=0;
   repeat(4) @(negedge clk);
   rst_n=1; pwr_good=1;
   repeat(4) @(negedge clk);
   // First accepted host write to this address on the same edge as power loss.
   pwr_good=0; cfg_v=1; cfg_a=target[4:0]; cfg_d=48'hace5fedcba98 ^ target;
   expected=cfg_d & mask(target); receipts=0;
   @(negedge clk); cfg_v=0;
   if (ao.sh_q[target] !== expected) $fatal(1,"shadow not written");
   if (ao.valid[target] !== 1'b1 || ao.dirty[target] !== 1'b1)
    $fatal(1,"LOST_POWER_LOSS_EDGE_WRITE address=%0d valid=%b dirty=%b",target,ao.valid[target],ao.dirty[target]);
   repeat(4) @(negedge clk);
   // Invalid addresses must never enter the finite replay map while asleep.
   retained_valid=ao.valid; retained_dirty=ao.dirty;
   cfg_v=1; cfg_a=5'd31; cfg_d=48'hffffffffffff;
   @(negedge clk); cfg_v=0;
   if (ao.valid !== retained_valid || ao.dirty !== retained_dirty)
    $fatal(1,"invalid address changed retained ownership");
   if (el_ready || e_cfg_v) $fatal(1,"sleep fabricated ready/replay");
   pwr_good=1; iso_n=1; arst_n=1;
   repeat(32) @(negedge clk);
   if (receipts!=1 || !el_ready || el_busy) $fatal(1,"replay debt/ready mismatch receipts=%0d",receipts);
   // A rewrite of an already-valid address must supersede its old shadow
   // without losing the retained validity or duplicating the replay receipt.
   pwr_good=0; iso_n=0; arst_n=0; cfg_v=1; cfg_a=target[4:0]; cfg_d=~cfg_d;
   expected=cfg_d & mask(target); receipts=0;
   @(negedge clk); cfg_v=0;
   if (ao.sh_q[target] !== expected || !ao.valid[target] || !ao.dirty[target])
    $fatal(1,"rewrite lost on power-loss edge");
   repeat(6) @(negedge clk);
   if (e_cfg_v || el_ready) $fatal(1,"off-domain receipt/readiness");
   pwr_good=1; iso_n=1; arst_n=1;
   repeat(32) @(negedge clk);
   if (receipts!=1 || !el_ready || el_busy) $fatal(1,"rewrite replay debt mismatch");
  end
  @(negedge clk); rst_n=0; arst_n=0; cfg_v=1;
  repeat(3) @(negedge clk);
  if (ao.valid !== 25'b0 || ao.dirty !== 25'b0 || el_ready)
   $fatal(1,"cold reset did not clear validity/debt");
  $display("PASS full25 firstwrite+rewrite retention, invalid address, sleep isolation, cold reset; exactly-once receipts=%0d",total);
  $finish;
 end
endmodule
