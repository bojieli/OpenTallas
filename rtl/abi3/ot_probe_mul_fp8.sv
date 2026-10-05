`timescale 1ns/1ps
// FP8 E4M3 significand multiply (4x4 incl implicit) -- the ROM/HBM weight path.
module ot_probe_mul_fp8 (input wire clk, input wire rst_n,
    input wire [7:0] a, input wire [7:0] b,
    output reg [6:0] e, output reg [7:0] p);
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin e<=7'b0; p<=8'b0; end
    else begin
      e <= {3'b0,a[6:3]} + {3'b0,b[6:3]};
      p <= (a[6:0]==0 || b[6:0]==0) ? 8'b0 : ({1'b1,a[2:0]} * {1'b1,b[2:0]});
    end
endmodule
