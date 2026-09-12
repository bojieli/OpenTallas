`timescale 1ns/1ps
// MXFP4 (E2M1) x FP8 E4M3 -- the mask-ROM weight path the density thesis needs.
// MXFP4 significand is 2 bits incl implicit, so the product is 2x4 = 6 bits.
module ot_probe_mul_mxfp4 (input wire clk, input wire rst_n,
    input wire [3:0] a,           // MXFP4 E2M1
    input wire [7:0] b,           // FP8 E4M3
    output reg [5:0] e, output reg [5:0] p);
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin e<=6'b0; p<=6'b0; end
    else begin
      e <= {4'b0,a[2:1]} + {2'b0,b[6:3]};
      p <= (a[2:0]==0 || b[6:0]==0) ? 6'b0 : ({1'b1,a[0]} * {1'b1,b[2:0]});
    end
endmodule
