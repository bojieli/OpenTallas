`timescale 1ns/1ps
// Plesiochronous link contract, transmitter side (stream hbm-contracts, item 4).
// Clocking found in the repo (see results/rtl/hbm_contracts_20261007/README.md):
//   * on the die, clk_link (endpoint pclk) and clk_stream (core) are both outputs of the die PLL hb_coll
//     (tools/hbm_accel_die_fp.py SDC_R15: pll_stream / pll_link, 0.833 ns each): MESOCHRONOUS, so the endpoint CDC
//     drains at II=1 >= arrival (locked case);
//   * between dies the collective crosses IEEE 802.3 PHY/FEC and a Tomahawk-Ultra-class switch on cables
//     (tools/dshbm_1m_coll.py budget; "L* plesiochronous at the link macro"): every device runs from its own
//     reference, +-100 ppm each, so the receiver's elastic buffer sees up to delta = 200 ppm more flits than it drains.
// Rule: the transmitter leaves at least one IDLE slot after every M consecutive flits, with
//       M <= (1 - delta) / delta ~= 1/delta  (200 ppm -> M <= 4999).  The receiver writes flits only, never idles,
//       so its buffer drains one slot per M+1.  Default M = 1024: 0.098 % of TX slots, ~4.9x margin on the bound.
// M = 0 disables insertion (negative controls only; refused at elaboration unless CHECK = 0).
module ot_hbm_coll_idle_insert #(parameter integer M=1024, PPM=200, CHECK=1)(
 input wire clk,rst_n,
 input wire in_v,          // a flit is offered this cycle
 output wire slot,         // 1: the flit may go this cycle; 0: forced idle
 output wire send);        // in_v && slot
 localparam integer M_EFF=(M<=0)?32'h7fffffff:M;
 localparam integer BOUND=(1000000-PPM)/PPM;
`ifndef SYNTHESIS
 initial if(CHECK&&(M<=0||M>BOUND))$fatal(1,"IDLE_M_BOUND M=%0d must be in 1..%0d for %0d ppm",M,BOUND,PPM);
`endif
 reg [31:0] run_q;                         // consecutive flits since the last idle slot
 wire due=run_q>=M_EFF;
 assign slot=!due;
 assign send=in_v&&slot;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)run_q<=0;
  else run_q<=send?run_q+1:32'd0;
`ifndef SYNTHESIS
 always @(posedge clk)if(rst_n&&send&&run_q>=M_EFF)$fatal(1,"IDLE_SPACING %0d consecutive flits",run_q+1);
`endif
endmodule
