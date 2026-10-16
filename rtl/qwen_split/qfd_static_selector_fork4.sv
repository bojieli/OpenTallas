`timescale 1ns/1ps
// NEW fixed-cycle selector fork. Each output is an independent registered copy.
// One normal execution edge; reset adds one cold-release edge only. Fresh
// physical/native qualification required; no inherited station/view evidence.
module qfd_static_selector_fork4 (
 input wire ck, rst_n,
 input wire [3:0] a,
 output reg [3:0] b0,b1
);
 (* keep *) reg reset_pin_q;
 always @(posedge ck or negedge rst_n)
  if (!rst_n) reset_pin_q<=1'b0; else reset_pin_q<=1'b1;
 always @(posedge ck or negedge reset_pin_q) begin
  if (!reset_pin_q) begin b0<=4'b0;b1<=4'b0;end
  else begin
   b0<=a;
`ifdef OT_QFD_SELECTOR4_FORK_MUT
   b1<=a ^ 4'h1;
`else
   b1<=a;
`endif
  end
 end
endmodule
