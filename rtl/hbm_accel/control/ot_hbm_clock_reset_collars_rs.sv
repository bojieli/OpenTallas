`default_nettype none
// strip-protect 2026-10-09: TA15 clock/reset collars, standard reset structure (successor of
// ot_hbm_clock_reset_collars in ot_hbm_clock_reset_boundary.sv; same ports, same 3-edge release).
//
// Measured failure of the original (Codex r4, 6_finish.rpt): TT -179 ps / FF -9 ps, both RECOVERY/REMOVAL checks of
// the raw AON reset intent (input delay on clock hbm) at a collar flop clocked by link: a cross-clock check at a
// 1.35 ps LCM edge separation that no layout can meet.  Root cause = all three collar flops take the RAW
// asynchronous reset, so every flop's recovery is an unconstrainable CDC, and the SDC referenced the AON inputs to
// destination clocks.  Reg-to-reg was +670 ps.
//
// Structure here (per endpoint region, one region per reset output, 17 regions):
//   sync_q[SYNC-1:0]  reset synchroniser: async assert from the raw intent (qualified POR & PLL reset & lock &
//                     endpoint intent), sync deassert (D chain from 1).  The ONLY flops whose RESETN sees a raw
//                     asynchronous input; in the SDC the raw deassert into them is a bounded-skew set_max/min_delay,
//                     and the raw ASSERT edge (-fall_from) is the only false path.
//   tree[TREE] .q     registered reset tree: each stage's RESETN is the SYNCHRONISED reset of the stage before it
//                     (async assert ripples clocklessly through CLR->Q; deassert is synchronous, so its recovery /
//                     removal is an ordinary same-clock check, timed).  The last stage drives the output port
//                     (registered output, no logic between flop and pin).
// SYNC=2, TREE=1 releases exactly 3 destination edges after the last qualifier rises, like the original 3-flop
// collar; assertion stays asynchronous and needs no clock edge (stopped-clock case of the bench).
module ot_hbm_reset_sync_tree #(parameter integer SYNC=2,TREE=1)(
 input wire clk,async_reset_n,output wire reset_n
);
 (* async_reg="true" *) reg [SYNC-1:0] sync_q;
 always @(posedge clk or negedge async_reset_n)
  if(!async_reset_n) sync_q<={SYNC{1'b0}};
  else sync_q<={sync_q[SYNC-2:0],1'b1};
 wire [TREE:0] up;
 assign up[0]=sync_q[SYNC-1];
 for(genvar k=0;k<TREE;k=k+1) begin:tree
  reg q;
  always @(posedge clk or negedge up[k])
   if(!up[k]) q<=1'b0;
   else q<=1'b1;
  assign up[k+1]=q;
 end
 assign reset_n=up[TREE];
endmodule

module ot_hbm_clock_reset_collars_rs #(parameter integer LINK_PORTS=9,SYNC=2,TREE=1)(
 input wire clk_stream, clk_serial, clk_hbm, clk_link,
 input wire por_n, pll_reset_n, pll_lock,
 input wire [3:0] phy_reset_intent_n,
 input wire [LINK_PORTS-1:0] link_reset_intent_n,
 input wire coll_reset_intent_n, cmd_reset_intent_n,
 output wire [3:0] phy_reset_n,
 output wire [LINK_PORTS-1:0] link_reset_n,
 output wire coll_reset_stream_n, coll_reset_serial_n,
 output wire cmd_reset_stream_n, cmd_reset_serial_n
);
 wire qualified_n=por_n & pll_reset_n & pll_lock;
 for(genvar p=0;p<4;p=p+1) begin:phy
  ot_hbm_reset_sync_tree #(.SYNC(SYNC),.TREE(TREE)) c(.clk(clk_hbm),
   .async_reset_n(qualified_n & phy_reset_intent_n[p]),.reset_n(phy_reset_n[p]));
 end
 for(genvar p=0;p<LINK_PORTS;p=p+1) begin:link
  ot_hbm_reset_sync_tree #(.SYNC(SYNC),.TREE(TREE)) c(.clk(clk_link),
   .async_reset_n(qualified_n & link_reset_intent_n[p]),.reset_n(link_reset_n[p]));
 end
 ot_hbm_reset_sync_tree #(.SYNC(SYNC),.TREE(TREE)) coll_stream(.clk(clk_stream),
  .async_reset_n(qualified_n & coll_reset_intent_n),.reset_n(coll_reset_stream_n));
 ot_hbm_reset_sync_tree #(.SYNC(SYNC),.TREE(TREE)) coll_serial(.clk(clk_serial),
  .async_reset_n(qualified_n & coll_reset_intent_n),.reset_n(coll_reset_serial_n));
 ot_hbm_reset_sync_tree #(.SYNC(SYNC),.TREE(TREE)) cmd_stream(.clk(clk_stream),
  .async_reset_n(qualified_n & cmd_reset_intent_n),.reset_n(cmd_reset_stream_n));
 ot_hbm_reset_sync_tree #(.SYNC(SYNC),.TREE(TREE)) cmd_serial(.clk(clk_serial),
  .async_reset_n(qualified_n & cmd_reset_intent_n),.reset_n(cmd_reset_serial_n));
 initial if(SYNC<2||TREE<1) $fatal(1,"collar needs a >=2-flop synchroniser and >=1 registered tree stage");
endmodule
`default_nettype wire
