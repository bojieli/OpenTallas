`default_nettype none
module ot_hbm_production_clock_quiescent #(parameter bit ENABLE=0)(
 input wire aon_clk,refclk,por_n,power_good,
 input wire [3:0] phy_ready,input wire [8:0] links_ready,
 input wire bist_done,bist_pass,fatal_error,requalify,
 output wire clk_stream,clk_serial,clk_hbm,clk_link,pll_lock,
 output wire [3:0] phy_reset_n,output wire [8:0] link_reset_n,
 output wire coll_reset_stream_n,coll_reset_serial_n,
 output wire cmd_reset_stream_n,cmd_reset_serial_n,
 output wire ready,clock_protocol_fault,output wire [3:0] state
);
 generate if(!ENABLE) begin:off
  assign clk_stream=0;assign clk_serial=0;assign clk_hbm=0;assign clk_link=0;assign pll_lock=0;
  assign phy_reset_n=0;assign link_reset_n=0;
  assign coll_reset_stream_n=0;assign coll_reset_serial_n=0;
  assign cmd_reset_stream_n=0;assign cmd_reset_serial_n=0;
  assign ready=0;assign clock_protocol_fault=0;assign state=0;
 end else begin:on
  wire pll_reset_n,coll_intent_n,cmd_intent_n,sequence_ready;
  wire [3:0] phy_intent_n;
  wire [8:0] link_intent_n;
  wire [3:0] root_clk,quiet_ack,enable_req,domain_clk;
  wire [16:0] reset_bus;
  wire raw_qualified_n=por_n && power_good && pll_reset_n && pll_lock && !fatal_error;
  ot_hbm_reset_seq #(.PORTS(9)) sequence_control(
   .aon_clk(aon_clk),.por_n(por_n),.power_good(power_good),.pll_lock(pll_lock),
   .phy_ready(phy_ready),.links_ready(links_ready),.bist_done(bist_done),.bist_pass(bist_pass),
   .fatal_error(fatal_error | clock_protocol_fault),.requalify(requalify),
   .pll_reset_n(pll_reset_n),.phy_reset_n(phy_intent_n),.link_reset_n(link_intent_n),
   .coll_reset_n(coll_intent_n),.cmd_reset_n(cmd_intent_n),.ready(sequence_ready),.state(state));
  ot_hbm_pll_bb pll(.refclk(refclk),.reset_n(por_n & pll_reset_n),
   .clk_stream(root_clk[0]),.clk_serial(root_clk[1]),.clk_hbm(root_clk[2]),.clk_link(root_clk[3]),.locked(pll_lock));
  for(genvar d=0;d<4;d=d+1) begin:gates
   ot_hbm_boot_clock_gate #(.ENABLE(1)) gate(
    .root_clk(root_clk[d]),.enable_req(enable_req[d]),.domain_clk(domain_clk[d]),.quiet_ack(quiet_ack[d]));
  end
  ot_hbm_quiescent_reset_commit #(.ENABLE(1),.GUARD(2)) commit_control(
   .aon_clk(aon_clk),.raw_qualified_n(raw_qualified_n),.sequence_ready(sequence_ready),
   .desired_reset_n({cmd_intent_n,cmd_intent_n,coll_intent_n,coll_intent_n,link_intent_n,phy_intent_n}),
   .actual_quiet_ack(quiet_ack),.reset_n(reset_bus),.clock_enable_req(enable_req),
   .ready(ready),.fault(clock_protocol_fault),.phase());
  assign {clk_link,clk_hbm,clk_serial,clk_stream}=domain_clk;
  assign {cmd_reset_serial_n,cmd_reset_stream_n,coll_reset_serial_n,coll_reset_stream_n,link_reset_n,phy_reset_n}=reset_bus;
 end endgenerate
endmodule
`default_nettype wire
