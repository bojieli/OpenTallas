`timescale 1ns/1ps
`ifndef LK
`define LK 2
`endif
`ifndef LP_MUT
`define LP_MUT 0
`endif
module col_h9_l4_lp_b #(parameter string INSTANCE = "col_h9") (
 input wire clk, cr, cr_s, rst_n, input wire [1103:0] x,
 input wire [3:0] xk, output wire [1103:0] xo,
 output wire [3:0] xok, output wire [69:0] ret);
 col_h9_l4_lp #(.INSTANCE(INSTANCE), .MUT(`LP_MUT)) u_f (
 .ck_r0(cr), .ck_r1(clk), .ck_r2(clk), .rst_n(rst_n),
 .x(x), .xk(xk), .lk({4{3'd`LK}}), .xo(xo), .xok(xok), .ret(ret));
endmodule
