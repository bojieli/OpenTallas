// Registered standalone pathfinding harness; adds one input and one output cycle.
module ot_qwen_r25_causal_mask_timing(input wire clk,rst_n,
input wire in_v,
input wire out_rdy,
input wire [1:0] in_checked,
input wire [72:0] in_owner,
input wire [79:0] in_query_positions,
input wire [2:0] in_queries,
input wire [19:0] in_row0,
output reg in_rdy,
output reg out_v,
output reg fault,
output reg [72:0] out_owner,
output reg [19:0] out_row0,
output reg [83:0] out_valid_lengths,
output reg [127:0] out_live);
reg in_v_r;
reg out_rdy_r;
reg [1:0] in_checked_r;
reg [72:0] in_owner_r;
reg [79:0] in_query_positions_r;
reg [2:0] in_queries_r;
reg [19:0] in_row0_r;
wire in_rdy_w;
wire out_v_w;
wire fault_w;
wire [72:0] out_owner_w;
wire [19:0] out_row0_w;
wire [83:0] out_valid_lengths_w;
wire [127:0] out_live_w;
always @(posedge clk or negedge rst_n) begin
 if(!rst_n) begin
 in_v_r<=0;
 out_rdy_r<=0;
 in_checked_r<=0;
 in_owner_r<=0;
 in_query_positions_r<=0;
 in_queries_r<=0;
 in_row0_r<=0;
 in_rdy<=0;
 out_v<=0;
 fault<=0;
 out_owner<=0;
 out_row0<=0;
 out_valid_lengths<=0;
 out_live<=0;
 end else begin
 in_v_r<=in_v;
 out_rdy_r<=out_rdy;
 in_checked_r<=in_checked;
 in_owner_r<=in_owner;
 in_query_positions_r<=in_query_positions;
 in_queries_r<=in_queries;
 in_row0_r<=in_row0;
 in_rdy<=in_rdy_w;
 out_v<=out_v_w;
 fault<=fault_w;
 out_owner<=out_owner_w;
 out_row0<=out_row0_w;
 out_valid_lengths<=out_valid_lengths_w;
 out_live<=out_live_w;
 end
end
ot_qwen_r25_causal_mask #(.ENABLE(1),.CAPACITY(8224)) u(.clk(clk),.rst_n(rst_n),
.in_v(in_v_r),
.out_rdy(out_rdy_r),
.in_checked(in_checked_r),
.in_owner(in_owner_r),
.in_query_positions(in_query_positions_r),
.in_queries(in_queries_r),
.in_row0(in_row0_r),
.in_rdy(in_rdy_w),
.out_v(out_v_w),
.fault(fault_w),
.out_owner(out_owner_w),
.out_row0(out_row0_w),
.out_valid_lengths(out_valid_lengths_w),
.out_live(out_live_w));
endmodule
