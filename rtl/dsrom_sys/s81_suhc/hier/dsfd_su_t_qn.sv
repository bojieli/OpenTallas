`timescale 1ns/1ps
// QN (el1011-s81su-qn, spec v3): production masters of the split q RMSNorm -> FP8 (rtl ot_s81_su_qn.sv), each hardened
// once: the tap (x 2, data halves), the 8-lane norm engine (x 32), the reduce (x 1), the act-quant engine (x 8).
module dsfd_su_t_qnt #(parameter integer CB = 32) (
    input  wire          ck, rst,
    input  wire          dn_st, input wire [3:0] dn_kind, input wire [1:0] dn_gsel, input wire [7:0] dn_jid,
    input  wire [15:0]   dn_v, input wire [4095:0] dn_d, input wire [32:0] i_f,
    output wire [15:0]   e_v, output wire [4095:0] e_d, output wire [127:0] e_t, output wire e_gq,
    output wire [1:0]    e_gr, output wire [1:0] e_gw, output wire e_go, output wire [13:0] e_ob, output wire [31:0] e_eps,
    output wire          o_fu, o_fo, o_alive, o_den, o_rdy, output wire [7:0] o_rjid
);
    ot_s81_su_qnt #(.N(256), .S_RD(16), .NFI(33), .CB(CB)) u_t (
        .clk(ck), .rst_in(rst), .dn_st_i(dn_st), .dn_kind_i(dn_kind), .dn_gsel_i(dn_gsel), .dn_jid_i(dn_jid),
        .dn_v_i(dn_v), .dn_d_i(dn_d), .i_f(i_f), .e_v(e_v), .e_d(e_d), .e_t(e_t), .e_gq(e_gq), .e_gr(e_gr), .e_gw(e_gw),
        .e_go(e_go), .e_ob(e_ob), .e_eps(e_eps), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den),
        .o_rdy(o_rdy), .o_rjid(o_rjid));
endmodule
module dsfd_su_t_qne (
    input  wire          ck, rst,
    input  wire          i_v, input wire [255:0] i_x, input wire [7:0] i_t, input wire i_gq, input wire [1:0] i_gr,
    input  wire [1:0]    i_gw, input wire r_v, input wire [31:0] r_d,
    output wire          p_v, output wire [7:0] p_i, output wire [31:0] p_d,
    output wire          y_v, output wire [7:0] y_i, output wire [255:0] y, output wire o_f
);
    ot_s81_su_qne #(.NV(5), .LM(5), .LA(4)) u_e (
        .clk(ck), .rst_in(rst), .i_v(i_v), .i_x(i_x), .i_t(i_t), .i_gq(i_gq), .i_gr(i_gr), .i_gw(i_gw), .r_v(r_v),
        .r_d(r_d), .p_v(p_v), .p_i(p_i), .p_d(p_d), .y_v(y_v), .y_i(y_i), .y(y), .o_f(o_f));
endmodule
module dsfd_su_t_qnr (
    input  wire          ck, rst,
    input  wire          i_go, input wire [31:0] i_eps,
    input  wire [1:0]    p_v, input wire [1:0] p_p, input wire [63:0] p_d, input wire [1:0] p_f,
    output wire          r_v, output wire [31:0] r_d, output wire o_f
);
    ot_s81_su_qnr #(.NE(2), .NV(5), .D(1280), .LM(5), .LA(4)) u_r (
        .clk(ck), .rst_in(rst), .i_go(i_go), .i_eps(i_eps), .p_v(p_v), .p_p(p_p), .p_d(p_d), .p_f(p_f), .r_v(r_v),
        .r_d(r_d), .o_f(o_f));
endmodule

module dsfd_su_t_qnh (
    input  wire          ck, rst,
    input  wire          i_go,
    input  wire [15:0]   p_v, input wire [15:0] p_p, input wire [511:0] p_d,
    output wire          s_v, output wire s_p, output wire [31:0] s_d, output wire o_f
);
    ot_s81_su_qnh #(.NE(16), .LA(4)) u_h (
        .clk(ck), .rst_in(rst), .i_go(i_go), .p_v(p_v), .p_p(p_p), .p_d(p_d), .s_v(s_v), .s_p(s_p), .s_d(s_d), .o_f(o_f));
endmodule
module dsfd_su_t_qnq (
    input  wire          ck, rst,
    input  wire [3:0]    cfg_b,
    input  wire          i_v, input wire [7:0] i_t, input wire [1023:0] i_y, input wire [13:0] i_ob,
    input  wire          nx_i_v, input wire [255:0] nx_i_q, input wire [9:0] nx_i_e,
    output wire          nx_o_v, output wire [255:0] nx_o_q, output wire [9:0] nx_o_e,
    output wire          o_v, output wire [13:0] o_a, output wire [15:0] o_m, output wire [511:0] o_d,
    output wire          o_fu, o_fo, o_alive, o_den, o_rdy, output wire [7:0] o_rjid
);
    ot_s81_su_qnq #(.N(256), .MLAT(5)) u_q (
        .clk(ck), .rst_in(rst), .cfg_b(cfg_b), .i_v(i_v), .i_t(i_t), .i_y(i_y), .i_ob(i_ob), .nx_i_v(nx_i_v),
        .nx_i_q(nx_i_q), .nx_i_e(nx_i_e), .nx_o_v(nx_o_v), .nx_o_q(nx_o_q), .nx_o_e(nx_o_e), .o_v(o_v), .o_a(o_a),
        .o_m(o_m), .o_d(o_d), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den), .o_rdy(o_rdy),
        .o_rjid(o_rjid));
endmodule
