`timescale 1ns/1ps
module ot_probe_bf16_add_flat (
    input wire clk, input wire rst_n,
    input wire [15:0] l, input wire [15:0] r,
    output reg [15:0] q, output reg sat, output reg [1:0] err);
  reg [15:0] l_q, r_q;
  wire [15:0] res; wire s; wire [1:0] e;
  ot_bf16_add_flat u (.left_code(l_q), .right_code(r_q),
                      .result_code(res), .result_saturated(s), .result_error(e));
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin l_q<=16'b0; r_q<=16'b0; q<=16'b0; sat<=1'b0; err<=2'b0; end
    else begin l_q<=l; r_q<=r; q<=res; sat<=s; err<=e; end
endmodule
