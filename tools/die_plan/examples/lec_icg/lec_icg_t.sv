// LEC clock-gate fixture (lane LEC-ICG 2026-10-26): latch-based ICGs (ASAP7 ICGx1 under SYNTHESIS, as ot_hdc_cg)
// gating an async-reset register, an enabled register, a sync-reset register and a black-box clock pin.
// make_netlists.sh synthesises it as is (netlist_ok.v) and with one MUT_* / REF_* define per mutant netlist.
module lec_icg_cg (input wire clk, input wire en, output wire gclk);
`ifdef REF_CLK_IN_EN
  ICGx1_ASAP7_75t_R u_icg (.CLK(clk), .ENA(en & clk), .SE(1'b0), .GCLK(gclk));
`else
  ICGx1_ASAP7_75t_R u_icg (.CLK(clk), .ENA(en), .SE(1'b0), .GCLK(gclk));
`endif
endmodule

module lec_icg_t (input wire clk, input wire rst_n, input wire ea, input wire eb, input wire [3:0] d,
                  output wire [3:0] qa, output wire [3:0] qb, output wire [3:0] qc, output wire [3:0] qs,
                  output wire [3:0] y, output wire z);
  wire ga, gb;
  reg eb_q;
  always @(posedge clk) eb_q <= eb;                       // registered enable (same root clock)
`ifdef MUT_INV_EN
  lec_icg_cg u_ga (.clk(clk), .en(~(ea | ~rst_n)), .gclk(ga));
`else
  lec_icg_cg u_ga (.clk(clk), .en(ea | ~rst_n), .gclk(ga));
`endif
`ifdef REF_CASCADE
  lec_icg_cg u_gb (.clk(ga), .en(eb_q), .gclk(gb));
`else
  lec_icg_cg u_gb (.clk(clk), .en(eb_q), .gclk(gb));
`endif
  reg [3:0] ra, rb, rc, rs;
`ifdef MUT_UNGATED
  always @(posedge clk or negedge rst_n)
`else
  always @(posedge ga or negedge rst_n)
`endif
    if (!rst_n) ra <= 4'd0; else ra <= d;                 // gated, async reset
`ifdef MUT_WRONG_GATE
  always @(posedge ga)
`elsif REF_NEGEDGE
  always @(negedge gb)
`else
  always @(posedge gb)
`endif
    if (d[0]) rb <= rb + d;                               // gated + own enable
  always @(posedge gb)
    if (!rst_n) rs <= 4'd5; else if (d[1]) rs <= rs ^ d;  // gated, sync reset over enable
  always @(posedge clk) rc <= ra ^ rb ^ rs;               // ungated
  lec_bbx u_bb (.clk(gb), .a(rc), .y(y));                 // black-box clock pin on a gated clock
`ifdef REF_GCLK_LOGIC
  assign z = gb & d[2];
`else
  assign z = ^y;
`endif
  assign qa = ra;
  assign qb = rb;
  assign qc = rc;
  assign qs = rs;
endmodule
