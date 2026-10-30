(* blackbox *) module ot_s81sl_cap_tr (clk, fault, o_d, o_e, o_t, o_v, rst_n, rt);
  input wire clk;
  output wire fault;
  output wire [31:0] o_d;
  output wire o_e;
  output wire [31:0] o_t;
  output wire o_v;
  input wire rst_n;
  input wire [279:0] rt;
endmodule
