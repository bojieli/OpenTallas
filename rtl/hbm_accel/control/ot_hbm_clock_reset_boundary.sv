`default_nettype none
// Boot ordering belongs to ot_hbm_reset_seq. Its AON reset intents enter
// destination-clock collars here. Clock outputs are direct analog macro pins;
// this module never gates, divides or fabricates them.
module ot_hbm_clock_reset_boundary #(parameter integer LINK_PORTS=9)(
 input wire refclk, por_n, pll_reset_n,
 input wire [3:0] phy_reset_intent_n,
 input wire [LINK_PORTS-1:0] link_reset_intent_n,
 input wire coll_reset_intent_n, cmd_reset_intent_n,
 output wire clk_stream, clk_serial, clk_hbm, clk_link, pll_lock,
 output wire [3:0] phy_reset_n,
 output wire [LINK_PORTS-1:0] link_reset_n,
 output wire coll_reset_stream_n, coll_reset_serial_n,
 output wire cmd_reset_stream_n, cmd_reset_serial_n
);
 wire qualified_pll_reset_n=por_n & pll_reset_n;
 ot_hbm_pll_bb pll(.refclk(refclk),.reset_n(qualified_pll_reset_n),
  .clk_stream(clk_stream),.clk_serial(clk_serial),.clk_hbm(clk_hbm),
  .clk_link(clk_link),.locked(pll_lock));
 ot_hbm_clock_reset_collars #(.LINK_PORTS(LINK_PORTS)) collars(
  .clk_stream(clk_stream),.clk_serial(clk_serial),.clk_hbm(clk_hbm),.clk_link(clk_link),
  .por_n(por_n),.pll_reset_n(pll_reset_n),.pll_lock(pll_lock),
  .phy_reset_intent_n(phy_reset_intent_n),.link_reset_intent_n(link_reset_intent_n),
  .coll_reset_intent_n(coll_reset_intent_n),.cmd_reset_intent_n(cmd_reset_intent_n),
  .phy_reset_n(phy_reset_n),.link_reset_n(link_reset_n),
  .coll_reset_stream_n(coll_reset_stream_n),.coll_reset_serial_n(coll_reset_serial_n),
  .cmd_reset_stream_n(cmd_reset_stream_n),.cmd_reset_serial_n(cmd_reset_serial_n));
endmodule

// Separately synthesizable digital body permits honest physical measurement
// against external clock obligations without replacing the analog PLL.
module ot_hbm_clock_reset_collars #(parameter integer LINK_PORTS=9)(
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
  ot_hbm_reset_release release_reset(.clk(clk_hbm),
   .async_reset_n(qualified_n & phy_reset_intent_n[p]),.reset_n(phy_reset_n[p]));
 end
 for(genvar p=0;p<LINK_PORTS;p=p+1) begin:link
  ot_hbm_reset_release release_reset(.clk(clk_link),
   .async_reset_n(qualified_n & link_reset_intent_n[p]),.reset_n(link_reset_n[p]));
 end
 ot_hbm_reset_release coll_stream(.clk(clk_stream),
  .async_reset_n(qualified_n & coll_reset_intent_n),.reset_n(coll_reset_stream_n));
 ot_hbm_reset_release coll_serial(.clk(clk_serial),
  .async_reset_n(qualified_n & coll_reset_intent_n),.reset_n(coll_reset_serial_n));
 ot_hbm_reset_release cmd_stream(.clk(clk_stream),
  .async_reset_n(qualified_n & cmd_reset_intent_n),.reset_n(cmd_reset_stream_n));
 ot_hbm_reset_release cmd_serial(.clk(clk_serial),
  .async_reset_n(qualified_n & cmd_reset_intent_n),.reset_n(cmd_reset_serial_n));
endmodule
`default_nettype wire
