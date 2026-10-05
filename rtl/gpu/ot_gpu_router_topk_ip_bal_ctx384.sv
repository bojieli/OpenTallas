module ot_gpu_router_topk_ip_bal_ctx384(input wire clk,rst_n,in_valid,in_last,
 input wire [511:0] in_vals,output wire out_valid,output wire [53:0] out_ids);
 ot_gpu_router_topk_ip_bal #(.LOOKAHEAD(1),.BALANCED(1),.NEG_VALID(1),.N(384),.P(16),.K(6),.IW(9)) u_selector
 (.clk(clk),.rst_n(rst_n),.in_valid(in_valid),.in_last(in_last),.in_vals(in_vals),.out_valid(out_valid),.out_ids(out_ids));
endmodule
