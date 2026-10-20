`timescale 1ns/1ps
module qfd_rlyr0_1_NS_65x30 (input wire ck, input wire [0:0] a, output wire [0:0] b, output wire ck_o);
    ot_qfd_rlane_st #(.W(1)) u_st (.cap(ck), .a(a), .b(b), .ck_o(ck_o));
endmodule
module qfd_rlyr_1_NW_65x30 (input wire ckf, input wire [0:0] a, output wire [0:0] b, output wire ck_o);
    ot_qfd_rlane_st #(.W(1)) u_st (.cap(ckf), .a(a), .b(b), .ck_o(ck_o));
endmodule
module qfd_rlyrl_1_EW_65x30 (input wire ck, input wire [0:0] a, output wire [0:0] b);
    ot_qfd_rlane_land #(.W(1)) u_land (.ck(ck), .a(a), .b(b));
endmodule
module qfd_rst_rep (input wire clk, input wire d, output wire q0, output wire q1);
    ot_qwen_rst_rep #(.PAD(0)) u_rep (.clk(clk), .d(d), .q0(q0), .q1(q1));
endmodule
