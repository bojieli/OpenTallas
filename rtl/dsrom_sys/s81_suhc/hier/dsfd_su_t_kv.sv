`timescale 1ns/1ps
// KV (el1011-s81su-kv, spec v3): production masters of the split kv RMSNorm -> RoPE -> FP8 QDQ (rtl ot_s81_su_kv.sv),
// each hardened once: the tap (x 4, data quarters), the 8-lane norm engine (x 56), its RoPE variant (x 8), the reduce
// (x 1; the 4 half trees are the QN master dsfd_su_t_qnh), the act-quant engine (x 16).
module dsfd_su_t_kvt (
    input  wire          ck, rst,
    input  wire          dn_st, input wire [3:0] dn_kind, input wire [1:0] dn_gsel, input wire [7:0] dn_jid,
    input  wire [15:0]   dn_v, input wire [2047:0] dn_d, input wire [64:0] i_f,
    output wire [31:0]   e_v, output wire [4095:0] e_d, output wire e_gk, output wire [1:0] e_gr, output wire [1:0] e_gw,
    output wire          e_go, output wire [13:0] e_ob, output wire [31:0] e_eps, output wire [511:0] e_cs,
    output wire          o_fu, o_fo, o_alive, o_den, o_rdy, output wire [7:0] o_rjid
);
    ot_s81_su_kvt #(.N(512), .S_RD(16), .NFI(65)) u_t (
        .clk(ck), .rst_in(rst), .dn_st_i(dn_st), .dn_kind_i(dn_kind), .dn_gsel_i(dn_gsel), .dn_jid_i(dn_jid),
        .dn_v_i(dn_v), .dn_d_i(dn_d), .i_f(i_f), .e_v(e_v), .e_d(e_d), .e_gk(e_gk), .e_gr(e_gr), .e_gw(e_gw),
        .e_go(e_go), .e_ob(e_ob), .e_eps(e_eps), .e_cs(e_cs), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive),
        .o_den(o_den), .o_rdy(o_rdy), .o_rjid(o_rjid));
endmodule
module dsfd_su_t_kve (
    input  wire          ck, rst,
    input  wire          i_v, input wire [255:0] i_x, input wire i_gk, input wire [1:0] i_gr, input wire [1:0] i_gw,
    input  wire          r_v, input wire [31:0] r_d,
    output wire          p_v, output wire [31:0] p_d, output wire y_v, output wire [255:0] y, output wire o_f
);
    ot_s81_su_kve #(.RP(0), .LM(5), .LA(4)) u_e (
        .clk(ck), .rst_in(rst), .i_v(i_v), .i_x(i_x), .i_gk(i_gk), .i_gr(i_gr), .i_gw(i_gw), .i_cos(128'd0),
        .i_sin(128'd0), .r_v(r_v), .r_d(r_d), .p_v(p_v), .p_d(p_d), .y_v(y_v), .y(y), .o_f(o_f));
endmodule
module dsfd_su_t_kvp (
    input  wire          ck, rst,
    input  wire          i_v, input wire [255:0] i_x, input wire i_gk, input wire [1:0] i_gr, input wire [1:0] i_gw,
    input  wire [127:0]  i_cos, input wire [127:0] i_sin, input wire r_v, input wire [31:0] r_d,
    output wire          p_v, output wire [31:0] p_d, output wire y_v, output wire [255:0] y, output wire o_f
);
    ot_s81_su_kve #(.RP(1), .LM(5), .LA(4)) u_e (
        .clk(ck), .rst_in(rst), .i_v(i_v), .i_x(i_x), .i_gk(i_gk), .i_gr(i_gr), .i_gw(i_gw), .i_cos(i_cos),
        .i_sin(i_sin), .r_v(r_v), .r_d(r_d), .p_v(p_v), .p_d(p_d), .y_v(y_v), .y(y), .o_f(o_f));
endmodule
module dsfd_su_t_kvr (
    input  wire          ck, rst,
    input  wire          i_go, input wire [31:0] i_eps,
    input  wire [3:0]    p_v, input wire [3:0] p_p, input wire [127:0] p_d, input wire [3:0] p_f,
    output wire          r_v, output wire [31:0] r_d, output wire o_f
);
    ot_s81_su_qnr #(.NE(4), .NV(1), .D(512), .LM(5), .LA(4)) u_r (
        .clk(ck), .rst_in(rst), .i_go(i_go), .i_eps(i_eps), .p_v(p_v), .p_p(p_p), .p_d(p_d), .p_f(p_f), .r_v(r_v),
        .r_d(r_d), .o_f(o_f));
endmodule
module dsfd_su_t_kvq (
    input  wire          ck, rst,
    input  wire [3:0]    cfg_b,
    input  wire          i_v, input wire [1023:0] i_y, input wire [13:0] i_ob,
    input  wire          nx_i_v, input wire [255:0] nx_i_q,
    output wire          nx_o_v, output wire [255:0] nx_o_q, output wire e_o_v, output wire [9:0] e_o_e,
    input  wire [7:0]    g_i_v, input wire [79:0] g_i_e,
    output wire          o_v, output wire [13:0] o_a, output wire [15:0] o_m, output wire [511:0] o_d,
    output wire          o_fu, o_fo, o_alive, o_den, o_rdy, output wire [7:0] o_rjid
);
    ot_s81_su_kvq #(.N(512), .MLAT(5)) u_q (
        .clk(ck), .rst_in(rst), .cfg_b(cfg_b), .i_v(i_v), .i_y(i_y), .i_ob(i_ob), .nx_i_v(nx_i_v), .nx_i_q(nx_i_q),
        .nx_o_v(nx_o_v), .nx_o_q(nx_o_q), .e_o_v(e_o_v), .e_o_e(e_o_e), .g_i_v(g_i_v), .g_i_e(g_i_e), .o_v(o_v),
        .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den), .o_rdy(o_rdy),
        .o_rjid(o_rjid));
endmodule
