`timescale 1ns/1ps
// Generated from exact actual RX source; no arithmetic replacement or added edge.
module ot_s81_su_rxh_clocked_candidate #(parameter S_RD=5, parameter LM=5, parameter LA=4, parameter XMUT=0, parameter QL=8) (
    input wire [(34+32/QL)-1:0] ck_leaf, rs_leaf,
    input  wire                   dn_st_i,
    input  wire [3:0]             dn_kind_i,
    input  wire [7:0]             dn_jid_i,
    input  wire [S_RD-1:0]        dn_v_i,
    input  wire [S_RD*512-1:0]    dn_d_i,
    output wire                   o_v,
    output wire [13:0]            o_a,
    output wire [15:0]            o_m,
    output wire [511:0]           o_d,
    output wire                   o_v2,
    output wire [13:0]            o_a2,
    output wire [511:0]           o_d2,
    output wire                   o_fu, o_fo, o_alive, o_den, o_rdy,
    output wire [7:0]             o_rjid
);
    wire xa_v; wire [511:0] xa_x, xa_r; wire [15:0] a_vo, a_f;
    wire [1:0] xq_v, xq_vi; wire [3:0] xq_f; wire [1023:0] xq_x, xq_y; wire [511:0] xq_c, xq_s;
    wire xb_v, xb_vi, xb_wi, xb_f, xw_st, xw_v, xw_last; wire [39:0] xw_cfg; wire [511:0] xb_y; wire [15:0] xb_m;
    ot_s81_su_rxc #(.S_RD(S_RD), .LM(LM), .LA(LA), .XMUT(XMUT), .QW(2)) u_c (
        .clk(ck_leaf[0]), .rst_in(rs_leaf[0]), .dn_st_i(dn_st_i), .dn_kind_i(dn_kind_i), .dn_jid_i(dn_jid_i), .dn_v_i(dn_v_i),
        .dn_d_i(dn_d_i), .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_v2(o_v2), .o_a2(o_a2), .o_d2(o_d2),
        .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den), .o_rdy(o_rdy), .o_rjid(o_rjid),
        .xa_v(xa_v), .xa_x(xa_x), .xa_vi(a_vo[0]), .xa_r(xa_r), .xa_f(a_f),
        .xq_v(xq_v), .xq_x(xq_x), .xq_c(xq_c), .xq_s(xq_s), .xq_vi(xq_vi), .xq_y(xq_y), .xq_f(xq_f),
        .xb_v(xb_v), .xw_st(xw_st), .xw_v(xw_v), .xw_last(xw_last), .xw_cfg(xw_cfg),
        .xb_vi(xb_vi), .xb_wi(xb_wi), .xb_y(xb_y), .xb_m(xb_m), .xb_f(xb_f));
    ot_s81_su_rxrb #(.LM(LM), .LA(LA), .MUT((XMUT == 2 || XMUT == 4) ? XMUT : 0)) u_b (.clk(ck_leaf[1]), .rst_in(rs_leaf[1]),
        .i_v(xb_v), .i_x(xq_x), .w_st(xw_st), .w_v(xw_v), .w_last(xw_last), .w_cfg(xw_cfg),
        .o_v(xb_vi), .o_w(xb_wi), .o_y(xb_y), .o_m(xb_m), .o_f(xb_f));
    genvar k;
    generate for (k = 0; k < 16; k = k + 1) begin : g_ra
        wire sv, sf; wire [31:0] su, su2, smx;
        ot_s81_su_rxsf #(.PCUT(1)) u_f (.clk(ck_leaf[2+k]), .rst_in(rs_leaf[2+k]), .i_v(xa_v), .i_x(xa_x[32 * k +: 32]),
            .o_v(sv), .o_u(su), .o_u2(su2), .o_mx(smx), .o_f(sf));
        ot_s81_su_rxsb #(.PCUT(1), .MUT(XMUT == 1 ? 1 : 0)) u_b (.clk(ck_leaf[18+k]), .rst_in(rs_leaf[18+k]), .i_v(sv), .i_u(su),
            .i_u2(su2), .i_mx(smx), .i_f(sf), .o_v(a_vo[k]), .o_r(xa_r[32 * k +: 32]), .o_f(a_f[k]));
    end endgenerate
    localparam integer NQ = 16 / QL;
    generate for (k = 0; k < 2; k = k + 1) begin : g_qr
        wire [NQ-1:0] q_vo, q_f;
        genvar j;
        for (j = 0; j < NQ; j = j + 1) begin : g_ql
            ot_s81_su_rxqr #(.LM(LM), .LA(LA), .MUT(XMUT == 3 ? 3 : 0), .QL(QL)) u_q (.clk(ck_leaf[34+k*NQ+j]), .rst_in(rs_leaf[34+k*NQ+j]),
                .i_v(xq_v[k]), .i_x(xq_x[512 * k + 32 * QL * j +: 32 * QL]), .i_c(xq_c[256 * k + 16 * QL * j +: 16 * QL]),
                .i_s(xq_s[256 * k + 16 * QL * j +: 16 * QL]), .o_v(q_vo[j]), .o_y(xq_y[512 * k + 32 * QL * j +: 32 * QL]),
                .o_f(q_f[j]));
        end
        assign xq_vi[k] = q_vo[0];
        assign xq_f[NQ * k +: NQ] = q_f;                                                              
    end endgenerate
endmodule
