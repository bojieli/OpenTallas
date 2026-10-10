`default_nettype none
// struct-close 2026-10-09 ("-cl" line, coordinator: TA15 production body hard element). SAME module names and ports as
// ot_hbm_production_clock_digital_body.sv / ot_hbm_production_clock_control.sv (a route or bench uses ONE of the files).
//
// pi-ta15prod-c7c53c4c2-tc-hm10-cl: TT -353.9 / FF +10.3 / DRC 0, 4 violating endpoints, all CROSS-DOMAIN or async:
//   (1) collars.phy[0].release_pipe[2] (clk_hbm) -> ready (aon output) -399.5: `ready = ready_sync && released` ANDs 17
//       destination-domain reset flops combinationally into an AON output (timed at the hbm/aon LCM edge separation);
//   (2) the same released AND -> ready_meta (aon synchroniser stage 1) -256.1: one synchroniser for a 17-domain AND;
//   (3) sequence_control.state (aon) -> collars release_pipe CLR (recovery, "asynchronous" group) -188.1: every collar
//       flop takes the raw AON intent as its async reset (the r4 class that ot_hbm_clock_reset_collars_rs fixed; that
//       collar CLOSED, sp-ta15rs-006e20771, TT +275.9 / FF +10.9);
//   (4) bist_done / por_n inputs -> sequence_control.status_meta (aon synchroniser stage 1) -46 / -30.
// Structure here (0 cycles on every reset release; readiness rise unchanged at 2 AON edges):
//   * collars = ot_hbm_clock_reset_collars_rs (2-flop synchroniser + registered tree, same 3-edge release);
//   * each of the 17 destination resets is synchronised INTO AON by its own 2-flop synchroniser (rel_sync_q), and
//     readiness = AND of the synchronised bits (aon flops) -- the same 2 AON edges as ready_meta/ready_sync on the AND;
//   * the IMMEDIATE drop of readiness is kept exactly: every cause that can assert a destination reset (por_n,
//     pll_reset_n, pll_lock, the intents) is AON-domain or a primary input, so ready = (&rel_sync) && sequence_ready &&
//     pll_lock (sequence_ready = RUN implies every intent and pll_reset_n released); no destination-domain flop reaches
//     an AON flop D or the output except through a synchroniser.
// SDC: physical/hbm_accel_die_views/clock_boundary/production_body_cl.sdc (the owner's body SDC + the closed collar's
// bounded-window idiom on the synchroniser stage-1 flops; no waiver, no false path except the raw assert edge).
module ot_hbm_production_clock_digital_body (
 input wire aon_clk,clk_stream,clk_serial,clk_hbm,clk_link,
 input wire por_n,power_good,pll_lock,
 input wire [3:0] phy_ready,
 input wire [8:0] links_ready,
 input wire bist_done,bist_pass,fatal_error,requalify,
 output wire pll_reset_n,
 output wire [3:0] phy_reset_n,
 output wire [8:0] link_reset_n,
 output wire coll_reset_stream_n,coll_reset_serial_n,
 output wire cmd_reset_stream_n,cmd_reset_serial_n,
 output wire ready,
 output wire [3:0] state
);
 wire coll_intent_n,cmd_intent_n,sequence_ready;
 wire [3:0] phy_intent_n;
 wire [8:0] link_intent_n;
 ot_hbm_reset_seq #(.PORTS(9)) sequence_control(
  .aon_clk(aon_clk),.por_n(por_n),.power_good(power_good),.pll_lock(pll_lock),
  .phy_ready(phy_ready),.links_ready(links_ready),.bist_done(bist_done),
  .bist_pass(bist_pass),.fatal_error(fatal_error),.requalify(requalify),
  .pll_reset_n(pll_reset_n),.phy_reset_n(phy_intent_n),.link_reset_n(link_intent_n),
  .coll_reset_n(coll_intent_n),.cmd_reset_n(cmd_intent_n),.ready(sequence_ready),.state(state));
 ot_hbm_clock_reset_collars_rs #(.LINK_PORTS(9)) collars(
  .clk_stream(clk_stream),.clk_serial(clk_serial),.clk_hbm(clk_hbm),.clk_link(clk_link),
  .por_n(por_n),.pll_reset_n(pll_reset_n),.pll_lock(pll_lock),
  .phy_reset_intent_n(phy_intent_n),.link_reset_intent_n(link_intent_n),
  .coll_reset_intent_n(coll_intent_n),.cmd_reset_intent_n(cmd_intent_n),
  .phy_reset_n(phy_reset_n),.link_reset_n(link_reset_n),
  .coll_reset_stream_n(coll_reset_stream_n),.coll_reset_serial_n(coll_reset_serial_n),
  .cmd_reset_stream_n(cmd_reset_stream_n),.cmd_reset_serial_n(cmd_reset_serial_n));
 wire [16:0] dest_rel={phy_reset_n,link_reset_n,coll_reset_stream_n,coll_reset_serial_n,cmd_reset_stream_n,cmd_reset_serial_n};
 (* async_reg="true" *) reg [16:0] rel_sync_q0,rel_sync_q1;
 always @(posedge aon_clk or negedge por_n)
  if(!por_n) begin rel_sync_q0<=17'd0;rel_sync_q1<=17'd0; end
  else begin rel_sync_q0<=dest_rel;rel_sync_q1<=rel_sync_q0; end
`ifndef OT_TA15_CL_MUT_NODROP
 assign ready=(&rel_sync_q1) && sequence_ready && pll_lock;
`else   // mutant: readiness from the synchronised release only (loses the immediate drop on POR / lock / intent)
 assign ready=(&rel_sync_q1);
`endif
endmodule

// Production composition for the bench (same module as ot_hbm_production_clock_control.sv): analog PLL + this body.
module ot_hbm_production_clock_control (
 input wire aon_clk,refclk,por_n,power_good,
 input wire [3:0] phy_ready,
 input wire [8:0] links_ready,
 input wire bist_done,bist_pass,fatal_error,requalify,
 output wire clk_stream,clk_serial,clk_hbm,clk_link,pll_lock,
 output wire [3:0] phy_reset_n,
 output wire [8:0] link_reset_n,
 output wire coll_reset_stream_n,coll_reset_serial_n,
 output wire cmd_reset_stream_n,cmd_reset_serial_n,
 output wire ready,
 output wire [3:0] state
);
 wire pll_reset_n;
 ot_hbm_pll_bb pll(.refclk(refclk),.reset_n(por_n & pll_reset_n),
  .clk_stream(clk_stream),.clk_serial(clk_serial),.clk_hbm(clk_hbm),
  .clk_link(clk_link),.locked(pll_lock));
 ot_hbm_production_clock_digital_body body(.aon_clk(aon_clk),.clk_stream(clk_stream),.clk_serial(clk_serial),
  .clk_hbm(clk_hbm),.clk_link(clk_link),.por_n(por_n),.power_good(power_good),.pll_lock(pll_lock),
  .phy_ready(phy_ready),.links_ready(links_ready),.bist_done(bist_done),.bist_pass(bist_pass),
  .fatal_error(fatal_error),.requalify(requalify),.pll_reset_n(pll_reset_n),.phy_reset_n(phy_reset_n),
  .link_reset_n(link_reset_n),.coll_reset_stream_n(coll_reset_stream_n),.coll_reset_serial_n(coll_reset_serial_n),
  .cmd_reset_stream_n(cmd_reset_stream_n),.cmd_reset_serial_n(cmd_reset_serial_n),.ready(ready),.state(state));
endmodule
`default_nettype wire
