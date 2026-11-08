// HBM-HARD-5 11-08: q3_body_ctl issuer_cfg next-state as a flat case on step (OT_Q3CTL_CFG_CASE hook).
// Same function as ot_hgi_coll_static_program_target (PW 8, MUT_DATA 0) lines 136-141:
//   draining && step<51: step%17==0 -> {1,4'd0,22'b0,row[7:6],2'(step/17),row[5:0]}
//                        else      -> {1,4'd1,assembly[(step/17)*512+(step%17-1)*32+:32]}
//   draining && step==51 -> {1,4'd2,metadata[31:0]};  step==52 -> {1,4'd3,metadata[63:32]};  else 0.
// The /17 and %17 are constant per case arm, so synthesis builds a 64-way select on step instead of a divider chain
// (vC1 worst path: step -> divide/modulo -> word select, ~30 levels, -117 ps SS at 5_1_grt). Combinational only:
// register set unchanged, so kit LEC stays a combinational match.
module ot_bodyctl_cfg_case(
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
          if (step == 6'(k))      y = {1'b1, 4'd1, (assembly[0*512 + (k-1)*32 +: 32] ^ 32'd1)};
          if (step == 6'(k + 17)) y = {1'b1, 4'd1, assembly[1*512 + (k-1)*32 +: 32]};
          if (step == 6'(k + 34)) y = {1'b1, 4'd1, assembly[2*512 + (k-1)*32 +: 32]};
        end
      end
    end
  end
endmodule
