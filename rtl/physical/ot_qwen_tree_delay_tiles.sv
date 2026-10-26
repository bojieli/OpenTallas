// Hard-view wrappers of ot_qwen_tree_delay: one parameter-free module per depth, so each depth has its own LEF/ETM
// master name (a hard child has no parameters).  Depth set {1,2,3,4,8,16} binds the 590-leg pad ledger with <= 3 tiles per leg.
module ot_qwen_tree_delay1_t (input wire clk, input wire [511:0] d, output wire [511:0] q);
  ot_qwen_tree_delay #(.DW(512), .LAT(1)) u (.clk(clk), .d(d), .q(q));
endmodule
module ot_qwen_tree_delay2_t (input wire clk, input wire [511:0] d, output wire [511:0] q);
  ot_qwen_tree_delay #(.DW(512), .LAT(2)) u (.clk(clk), .d(d), .q(q));
endmodule
module ot_qwen_tree_delay3_t (input wire clk, input wire [511:0] d, output wire [511:0] q);
  ot_qwen_tree_delay #(.DW(512), .LAT(3)) u (.clk(clk), .d(d), .q(q));
endmodule
module ot_qwen_tree_delay4_t (input wire clk, input wire [511:0] d, output wire [511:0] q);
  ot_qwen_tree_delay #(.DW(512), .LAT(4)) u (.clk(clk), .d(d), .q(q));
endmodule
module ot_qwen_tree_delay8_t (input wire clk, input wire [511:0] d, output wire [511:0] q);
  ot_qwen_tree_delay #(.DW(512), .LAT(8)) u (.clk(clk), .d(d), .q(q));
endmodule
module ot_qwen_tree_delay16_t (input wire clk, input wire [511:0] d, output wire [511:0] q);
  ot_qwen_tree_delay #(.DW(512), .LAT(16)) u (.clk(clk), .d(d), .q(q));
endmodule
