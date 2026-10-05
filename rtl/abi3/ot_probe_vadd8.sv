`timescale 1ns/1ps
module ot_probe_vadd8 (
    input wire clk, input wire rst_n,
    input wire iv, output wire ir,
    input wire [127:0] a, input wire [127:0] b,
    output wire ov, input wire orr,
    output wire [127:0] q, output wire [7:0] sat, output wire [15:0] err);
  ot_vector_add_unit #(.LANES(8), .FIFO_LOG2(4)) u (
    .clk(clk), .rst_n(rst_n), .in_valid(iv), .in_ready(ir),
    .in_left(a), .in_right(b), .out_valid(ov), .out_ready(orr),
    .out_result(q), .out_saturated(sat), .out_error(err));
endmodule
