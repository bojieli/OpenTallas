module pair_top (clk, a_i, a_o, x_i, x_o);
 input clk;
 input [1:0] a_i;
 output [1:0] a_o;
 input x_i;
 output x_o;
 wire [1:0] w_a;
 wire w_x;
 part_a u0 (.clk(clk), .a_i(a_i), .a_o(w_a), .x_i(x_i), .x_o(w_x));
 part_a u1 (.clk(clk), .a_i(w_a), .a_o(a_o), .x_i(w_x), .x_o(x_o));
endmodule
