`timescale 1ns/1ps
// FP32 significand multiply (24x24) -- included to measure what it actually
// costs, since the precision table claims ~9x the BF16 array.
module ot_probe_mul_fp32 (input wire clk, input wire rst_n,
    input wire [31:0] a, input wire [31:0] b,
    output reg [9:0] e, output reg [47:0] p);
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin e<=10'b0; p<=48'b0; end
    else begin
      e <= {2'b0,a[30:23]} + {2'b0,b[30:23]};
      p <= (a[30:0]==0 || b[30:0]==0) ? 48'b0 : ({1'b1,a[22:0]} * {1'b1,b[22:0]});
    end
endmodule
