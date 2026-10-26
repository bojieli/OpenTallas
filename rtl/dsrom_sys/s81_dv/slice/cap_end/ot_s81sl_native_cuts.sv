`timescale 1ns/1ps
// Source-only native CN/IK cut candidates. Existing closed wrappers and selected
// raw provider remain unchanged. New physical views, port mapping, equivalence,
// cut timing and compiler-calendar adoption are required before use.

module ot_s81sl_native_kve (
    input  wire          ck, rst,
    input  wire          i_v, input wire [255:0] i_x, input wire i_gk, input wire [1:0] i_gr, input wire [1:0] i_gw,
    input  wire          r_v, input wire [31:0] r_d,
    output wire          norm_v, output wire [127:0] norm_y,
    output wire          p_v, output wire [31:0] p_d, output wire y_v, output wire [255:0] y, output wire o_f
);
    ot_s81_su_kve #(.RP(0), .LM(5), .LA(4)) u_e (
        .clk(ck), .rst_in(rst), .i_v(i_v), .i_x(i_x), .i_gk(i_gk), .i_gr(i_gr), .i_gw(i_gw), .i_cos(128'd0),
        .i_sin(128'd0), .r_v(r_v), .r_d(r_d), .p_v(p_v), .p_d(p_d), .norm_v(norm_v), .norm_y(norm_y), .y_v(y_v), .y(y), .o_f(o_f));
endmodule

module ot_s81sl_native_kvp (
    input  wire          ck, rst,
    input  wire          i_v, input wire [255:0] i_x, input wire i_gk, input wire [1:0] i_gr, input wire [1:0] i_gw,
    input  wire [127:0]  i_cos, input wire [127:0] i_sin, input wire r_v, input wire [31:0] r_d,
    output wire          norm_v, output wire [127:0] norm_y,
    output wire          p_v, output wire [31:0] p_d, output wire y_v, output wire [255:0] y, output wire o_f
);
    ot_s81_su_kve #(.RP(1), .LM(5), .LA(4)) u_e (
        .clk(ck), .rst_in(rst), .i_v(i_v), .i_x(i_x), .i_gk(i_gk), .i_gr(i_gr), .i_gw(i_gw), .i_cos(i_cos),
        .i_sin(i_sin), .r_v(r_v), .r_d(r_d), .p_v(p_v), .p_d(p_d), .norm_v(norm_v), .norm_y(norm_y), .y_v(y_v), .y(y), .o_f(o_f));
endmodule

module ot_s81sl_native_kvt (
    input  wire          ck, rst,
    input  wire          dn_st, input wire [3:0] dn_kind, input wire [1:0] dn_gsel, input wire [7:0] dn_jid,
    input  wire [15:0]   dn_v, input wire [2047:0] dn_d, input wire [64:0] i_f,
    output wire [31:0]   e_v, output wire [4095:0] e_d, output wire e_gk, output wire [1:0] e_gr, output wire [1:0] e_gw,
    output wire          e_go, output wire [13:0] e_ob, output wire [31:0] e_eps, output wire [511:0] e_cs,
    output wire [1:0] e_mode, output wire [13:0] e_nb,
    output wire          o_fu, o_fo, o_alive, o_den, o_rdy, output wire [7:0] o_rjid
);
    ot_s81_su_kvt #(.N(512), .S_RD(16), .NFI(65)) u_t (
        .clk(ck), .rst_in(rst), .dn_st_i(dn_st), .dn_kind_i(dn_kind), .dn_gsel_i(dn_gsel), .dn_jid_i(dn_jid),
        .dn_v_i(dn_v), .dn_d_i(dn_d), .i_f(i_f), .e_v(e_v), .e_d(e_d), .e_gk(e_gk), .e_gr(e_gr), .e_gw(e_gw), .e_mode(e_mode), .e_nb(e_nb),
        .e_go(e_go), .e_ob(e_ob), .e_eps(e_eps), .e_cs(e_cs), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive),
        .o_den(o_den), .o_rdy(o_rdy), .o_rjid(o_rjid));
endmodule
