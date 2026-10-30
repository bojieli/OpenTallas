(* blackbox *)
module ot_s81ph_native_sel_hist_bank (busy, clk, gbin, gsum, i_dg, i_en, i_v, rst_n, clr, gsel);
  output wire busy;
  input wire clk;
  output wire [175:0] gbin;
  output wire [29:0] gsum;
  input wire [127:0] i_dg;
  input wire [15:0] i_en;
  input wire i_v;
  input wire rst_n;
  input wire [16:0] clr;
  input wire [63:0] gsel;
endmodule
