// ot_keep_regs_split.v -- techmap used by physical/common_flow/ot_keep_regs.tcl under SYNTH_HIERARCHICAL=1:
// splits a kept multi-bit coarse flip-flop / latch cell into WIDTH one-bit coarse cells of the same type (instead of
// gate-level $_DFF_*_ cells).  One-bit cells are recursed into by techmap and refused via _TECHMAP_FAIL_, so they stay.
// Why: yosys keep_hierarchy -min_cost (ORFS SYNTH_MINIMUM_KEEP_SIZE) costs cells with CellCosts, which throws
// std::out_of_range in Cell::getParam() on gate-level async-reset flops ($_DFF_PN0_ ...), killing synthesis.
(* techmap_celltype = "$dff" *)
module _ot_kr_split_dff (CLK, D, Q);
  parameter WIDTH = 1;
  parameter CLK_POLARITY = 1'b1;
  input CLK; input [WIDTH-1:0] D; output [WIDTH-1:0] Q;
  wire _TECHMAP_FAIL_ = WIDTH <= 1;
  genvar i;
  generate for (i = 0; i < WIDTH; i = i + 1) begin : b
    \$dff #(.WIDTH(1), .CLK_POLARITY(CLK_POLARITY)) f (.CLK(CLK), .D(D[i]), .Q(Q[i]));
  end endgenerate
endmodule

(* techmap_celltype = "$adff" *)
module _ot_kr_split_adff (CLK, ARST, D, Q);
  parameter WIDTH = 1;
  parameter CLK_POLARITY = 1'b1;
  parameter ARST_POLARITY = 1'b1;
  parameter ARST_VALUE = 0;
  input CLK, ARST; input [WIDTH-1:0] D; output [WIDTH-1:0] Q;
  wire _TECHMAP_FAIL_ = WIDTH <= 1;
  localparam [WIDTH-1:0] RV = ARST_VALUE;
  genvar i;
  generate for (i = 0; i < WIDTH; i = i + 1) begin : b
    \$adff #(.WIDTH(1), .CLK_POLARITY(CLK_POLARITY), .ARST_POLARITY(ARST_POLARITY), .ARST_VALUE(RV[i]))
      f (.CLK(CLK), .ARST(ARST), .D(D[i]), .Q(Q[i]));
  end endgenerate
endmodule

(* techmap_celltype = "$aldff" *)
module _ot_kr_split_aldff (CLK, ALOAD, AD, D, Q);
  parameter WIDTH = 1;
  parameter CLK_POLARITY = 1'b1;
  parameter ALOAD_POLARITY = 1'b1;
  input CLK, ALOAD; input [WIDTH-1:0] AD, D; output [WIDTH-1:0] Q;
  wire _TECHMAP_FAIL_ = WIDTH <= 1;
  genvar i;
  generate for (i = 0; i < WIDTH; i = i + 1) begin : b
    \$aldff #(.WIDTH(1), .CLK_POLARITY(CLK_POLARITY), .ALOAD_POLARITY(ALOAD_POLARITY))
      f (.CLK(CLK), .ALOAD(ALOAD), .AD(AD[i]), .D(D[i]), .Q(Q[i]));
  end endgenerate
endmodule

(* techmap_celltype = "$dffsr" *)
module _ot_kr_split_dffsr (CLK, SET, CLR, D, Q);
  parameter WIDTH = 1;
  parameter CLK_POLARITY = 1'b1;
  parameter SET_POLARITY = 1'b1;
  parameter CLR_POLARITY = 1'b1;
  input CLK; input [WIDTH-1:0] SET, CLR, D; output [WIDTH-1:0] Q;
  wire _TECHMAP_FAIL_ = WIDTH <= 1;
  genvar i;
  generate for (i = 0; i < WIDTH; i = i + 1) begin : b
    \$dffsr #(.WIDTH(1), .CLK_POLARITY(CLK_POLARITY), .SET_POLARITY(SET_POLARITY), .CLR_POLARITY(CLR_POLARITY))
      f (.CLK(CLK), .SET(SET[i]), .CLR(CLR[i]), .D(D[i]), .Q(Q[i]));
  end endgenerate
endmodule

(* techmap_celltype = "$dlatch" *)
module _ot_kr_split_dlatch (EN, D, Q);
  parameter WIDTH = 1;
  parameter EN_POLARITY = 1'b1;
  input EN; input [WIDTH-1:0] D; output [WIDTH-1:0] Q;
  wire _TECHMAP_FAIL_ = WIDTH <= 1;
  genvar i;
  generate for (i = 0; i < WIDTH; i = i + 1) begin : b
    \$dlatch #(.WIDTH(1), .EN_POLARITY(EN_POLARITY)) f (.EN(EN), .D(D[i]), .Q(Q[i]));
  end endgenerate
endmodule
