`timescale 1ns/1ps
`default_nettype none
// One planned320-bit boot transport hop. Only cfg/desc/launch valid state resets;
// payload fields move on every edge, keeping source tuple identity. Not a FIFO.
module ot_hnx_host_boot_hop (
 input wire clk, rst_n,
 input wire [319:0] d,
 output wire [319:0] q
);
 reg [319:0] payload;
 reg [2:0] valid;
 always @(posedge clk) payload <= d;
 always @(posedge clk) begin
  if (!rst_n) valid <= 3'b000;
  else valid <= {d[319], d[42], d[0]};
 end
 assign q = {valid[2], payload[318:43], valid[1], payload[41:1], valid[0]};
endmodule
`default_nettype wire
