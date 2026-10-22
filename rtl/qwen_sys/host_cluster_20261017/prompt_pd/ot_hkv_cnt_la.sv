`timescale 1ns/1ps
// HKV-PROMPT6 (10-19): W-bit event counter with a registered low-half carry lookahead.  Bit- and cycle-exact to
// `if (en) q <= q + 1` with an asynchronous active-low reset to 0: lo_full == (q[LO-1:0] == all ones) is kept as a
// register (next value = (q[LO-1:0] == all ones - 1) on an increment), so the high half increments on lo_full instead of
// waiting for the LO-bit carry.  Longest path: en -> LO-bit increment (or the W-LO bit high increment), never W bits.
// Routed p5 qkd_hr_core_prompt: the 64-bit c_busy ripple chain (inflight -> 16 OR levels -> c_busy[63]) was TT -34.9 ps.
// OT_HKV_CNT_LA_MUTANT (bench only): lookahead one count early (high half increments at all-ones - 1).
module ot_hkv_cnt_la #(parameter integer W=64, parameter integer LO=32)(
 input wire clk, rst_n, en,
 output reg [W-1:0] q
);
 reg lo_full;
`ifdef OT_HKV_CNT_LA_MUTANT
 localparam [LO-1:0] PRE = {{(LO-2){1'b1}},2'b01};
`else
 localparam [LO-1:0] PRE = {{(LO-1){1'b1}},1'b0};
`endif
 always @(posedge clk or negedge rst_n)
  if (!rst_n) begin q <= {W{1'b0}}; lo_full <= 1'b0; end
  else if (en) begin
   q[LO-1:0] <= q[LO-1:0] + 1'b1;
   if (lo_full) q[W-1:LO] <= q[W-1:LO] + 1'b1;
   lo_full <= (q[LO-1:0] == PRE);
  end
endmodule
