`timescale 1ns/1ps
// Flow calibration: the simplest possible register-to-register path.
// Whatever this measures is the practical ceiling of ASAP7 + this synthesis flow,
// and no RTL restructuring can exceed it.
module ot_probe_floor (input wire clk, input wire rst_n,
    input wire d, output reg q);
  always @(posedge clk or negedge rst_n)
    if (!rst_n) q <= 1'b0; else q <= ~d;
endmodule
