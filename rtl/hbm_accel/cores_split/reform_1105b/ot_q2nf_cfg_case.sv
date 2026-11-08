// Q2NF: exact PW8 static-program configuration decode, reused from HBM-HARD-5 CFG_CASE.
// Flat constant selects replace step/17 and variable1536-bit word shifts; same D/register/reset/clocks.
module ot_q2nf_cfg_case(
  input  [5:0]    step,
  input  [7:0]    row,
  input  [1535:0] assembly,
  input  [63:0]   metadata,
  input           draining,
  output reg [36:0] y
);
  integer k;
  always @* begin
    y = 37'd0;
    if (draining) begin
      if (step == 6'd0)       y = {1'b1, 4'd0, 22'b0, row[7:6], 2'd0, row[5:0]};
      else if (step == 6'd17) y = {1'b1, 4'd0, 22'b0, row[7:6], 2'd1, row[5:0]};
      else if (step == 6'd34) y = {1'b1, 4'd0, 22'b0, row[7:6], 2'd2, row[5:0]};
      else if (step == 6'd51) y = {1'b1, 4'd2, metadata[31:0]};
      else if (step == 6'd52) y = {1'b1, 4'd3, metadata[63:32]};
      else begin
        for (k = 1; k <= 16; k = k + 1) begin
          if (step == 6'(k))      y = {1'b1, 4'd1, assembly[0*512 + (k-1)*32 +: 32]};
          if (step == 6'(k + 17)) y = {1'b1, 4'd1, assembly[1*512 + (k-1)*32 +: 32]};
          if (step == 6'(k + 34)) y = {1'b1, 4'd1, assembly[2*512 + (k-1)*32 +: 32]};
        end
      end
    end
  end
endmodule
