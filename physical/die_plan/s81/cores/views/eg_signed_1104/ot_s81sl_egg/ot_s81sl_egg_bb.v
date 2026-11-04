(* blackbox *) module ot_s81sl_egg (clk, fault, g, g_c, g_v, i_c, i_dd, i_v, n_f, n_rh, n_rk, n_v, rst_n, scale);
  input wire clk;
  output wire fault;
  output wire [31:0] g;
  output wire [1:0] g_c;
  output wire g_v;
  input wire [1:0] i_c;
  input wire [31:0] i_dd;
  input wire i_v;
  input wire [1:0] n_f;
  input wire [31:0] n_rh;
  input wire [31:0] n_rk;
  input wire [1:0] n_v;
  input wire rst_n;
  input wire [31:0] scale;
endmodule
