// Full K2048 synthesis/P&R vehicle. No reduced shape.  RST_RELAY / OUT_SKID: opt-in boundary standard (default 0 =
// the historical vehicle; ot_hgi_idx_topk_registered).
module ot_hgi_idx_topk_full #(parameter integer RST_RELAY=0, parameter integer OUT_SKID=0)(
 input wire clk,rst_n,
 input wire cmd_valid, output wire cmd_ready,
 input wire [3:0] cmd_unit, input wire [5:0] cmd_op,
 input wire [24:0] cmd_param, input wire [31:0] cmd_n,cmd_m,
 input wire cmd_values,
 input wire in_valid, output wire in_ready, input wire [31:0] in_score,
 output wire out_valid, input wire out_ready,
 output wire [31:0] out_id,out_score,out_row,
 output wire out_last, output wire out_values_valid, output reg done, output reg [3:0] error
);
 ot_hgi_idx_topk_registered #(.ENABLE(1),.MAX_K(2048),.RST_RELAY(RST_RELAY),.OUT_SKID(OUT_SKID)) u(.*);
endmodule
