(* blackbox *) module ot_s81ph_native_sel_hist_bank (busy, clk, clr, gbin, gsel, gsum, i_dg, i_en, i_v, rst_n);
output busy;
input clk;
input [16:0] clr;
output [175:0] gbin;
input [63:0] gsel;
output [29:0] gsum;
input [127:0] i_dg;
input [15:0] i_en;
input i_v;
input rst_n;
endmodule
