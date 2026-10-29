(* blackbox *) module hnx_xs3(input clk, rst_a, input [8:0] xs_a1, input [4:0] xs_g1, input [6:0] xs_a2, input [4:0] xs_g2, input [817:0] rl1, input [2068:0] bk1, input [12:0] ohl1, input [2:0] wl,
 output o_iv_b, o_iv_f, o_ifirst, o_ilast, o_ifp4, output [15:0] o_itag, output [531:0] o_iwb, output [1595:0] o_ixb, output [255:0] o_iwf_e, output [255:0] o_ixf_e, output [255:0] o_iwf_w, output [511:0] o_ixf_w,
 output o_ifirst_e, o_ilast_e, output [15:0] o_itag_e, output o_iv_fw, o_ifirst_w, o_ilast_w, output [15:0] o_itag_w);
endmodule
(* blackbox *) module ot_hbm_accel_smh_bdc(input clk, rst_a, i_v, i_first, i_last, i_fp4, input [15:0] i_tag, input [531:0] i_w, i_x, output ov, output [31:0] y, output [15:0] otag, output fault);
endmodule
(* blackbox *) module hnx_rp4_tcc(input [2:0] clk_hard, input rst_a, i_v, i_first, i_last, input [15:0] i_tag, input [255:0] i_w, i_x, output ov, output [31:0] y, output [15:0] otag, output fault);
endmodule
(* blackbox *) module hnx_rp4lp4_pub #(parameter integer P = 4, parameter integer LSKEW = 8, parameter integer MUT = 0, parameter integer RING = 1)(input clk, rst_n, input [P*50-1:0] g_p, input [P-1:0] act, output [49:0] g);
endmodule
