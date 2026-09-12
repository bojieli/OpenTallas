`timescale 1ns/1ps
// BF16 significand multiply (8x8 incl implicit) -- the activation path.
module ot_probe_mul_bf16 (input wire clk, input wire rst_n,
    input wire [15:0] a, input wire [15:0] b,
    output reg [9:0] e, output reg [15:0] p);
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin e<=10'b0; p<=16'b0; end
    else begin
      e <= {2'b0,a[14:7]} + {2'b0,b[14:7]};
      p <= (a[14:0]==0 || b[14:0]==0) ? 16'b0 : ({1'b1,a[6:0]} * {1'b1,b[6:0]});
    end
endmodule
