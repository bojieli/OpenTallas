`default_nettype none
// Full production boot/reset body. The isolated collar vehicle does not contain
// the sequencer's POR-release mask; this successor routes that real composition.
// All clocks and lock enter from the actual analog PLL boundary. Readiness
// providers stay literal inputs until the native die endpoints supply them.
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
 ot_hbm_clock_reset_collars #(.LINK_PORTS(9)) collars(
  .clk_stream(clk_stream),.clk_serial(clk_serial),.clk_hbm(clk_hbm),.clk_link(clk_link),
  .por_n(por_n),.pll_reset_n(pll_reset_n),.pll_lock(pll_lock),
  .phy_reset_intent_n(phy_intent_n),.link_reset_intent_n(link_intent_n),
  .coll_reset_intent_n(coll_intent_n),.cmd_reset_intent_n(cmd_intent_n),
  .phy_reset_n(phy_reset_n),.link_reset_n(link_reset_n),
  .coll_reset_stream_n(coll_reset_stream_n),.coll_reset_serial_n(coll_reset_serial_n),
  .cmd_reset_stream_n(cmd_reset_stream_n),.cmd_reset_serial_n(cmd_reset_serial_n));
 wire released=sequence_ready && (&phy_reset_n) && (&link_reset_n) &&
  coll_reset_stream_n && coll_reset_serial_n && cmd_reset_stream_n && cmd_reset_serial_n;
 (* async_reg="true" *) reg ready_meta,ready_sync;
 always @(posedge aon_clk or negedge por_n)
  if(!por_n) begin ready_meta<=1'b0;ready_sync<=1'b0; end
  else begin ready_meta<=released;ready_sync<=ready_meta; end
 assign ready=ready_sync && released;
endmodule

// Real production wrapper: no test oscillator, invented divider or clock gate.
module ot_hbm_production_clock_control_body_bound (
 input wire aon_clk,refclk,por_n,power_good,
 input wire [3:0] phy_ready,input wire [8:0] links_ready,
 input wire bist_done,bist_pass,fatal_error,requalify,
 output wire clk_stream,clk_serial,clk_hbm,clk_link,pll_lock,
 output wire [3:0] phy_reset_n,output wire [8:0] link_reset_n,
 output wire coll_reset_stream_n,coll_reset_serial_n,
 output wire cmd_reset_stream_n,cmd_reset_serial_n,
 output wire ready,output wire [3:0] state
);
 wire pll_reset_n;
 ot_hbm_pll_bb pll(.refclk(refclk),.reset_n(por_n & pll_reset_n),
  .clk_stream(clk_stream),.clk_serial(clk_serial),.clk_hbm(clk_hbm),
  .clk_link(clk_link),.locked(pll_lock));
 ot_hbm_production_clock_digital_body body(.*);
endmodule
`default_nettype wire
