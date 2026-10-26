// Clock-mechanism witness only; arithmetic bodies unchanged and outside this proof.
module ot_hidx_score_hcol #(parameter integer HALF=0,MUT=0)(
input wire [1:0] clk_pair,
input wire rst_col,
input wire qv_b,
input wire [567:0] q_b,
input wire [543:0] key,
input wire [31:0] hid4,
input wire [31:0] cs_in,
input wire cf_in,
output wire [31:0] cs_out,
output wire cf_out,
output wire [1:0] prdy);
reg [17:0] q0;reg [16:0]q1;
always @(posedge clk_pair[0]) q0<=q_b[17:0];
always @(posedge clk_pair[1]) q1<=q_b[34:18];
assign {cs_out,cf_out,prdy}={q0,q1};
endmodule
