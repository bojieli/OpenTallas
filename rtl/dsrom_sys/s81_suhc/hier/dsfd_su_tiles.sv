`timescale 1ns/1ps
// Hardened tile masters of dsfd_sp_su_h (s81-suhc-hier-1011): ot_s81_su_tile at production params, lane group 0
// of each function (pins: tools/s81_suhc/su_tiles_plan.py; the down-spine row data split dn_dl / dn_dh by face).
// Production SU: QN_N 256, KV_N 512, QB_NB 32, SW_W 1024, SM_H 16, SM_LPH 16, S_RD 16, S_WR 16, LM 5, LA 4.
module dsfd_su_t_qn (
    input  wire          ck, rst,
    input  wire          dn_st, input wire [3:0] dn_kind, input wire [1:0] dn_gsel, input wire dn_fp4,
    input  wire [7:0]    dn_jid, input wire [15:0] dn_v, input wire dn_ph, input wire [15:0] dn_idx,
    input  wire [4095:0] dn_dl, input wire [4095:0] dn_dh,
    output wire [15:0] o_v, output wire [223:0] o_a, output wire [255:0] o_m, output wire [8191:0] o_d,
    output wire          o_fu, o_fo, o_alive, o_den, o_rdy, output wire [7:0] o_rjid
);
    ot_s81_su_tile #(.TK(0), .TI(0), .NT(1), .QN_N(256), .KV_N(512), .QB_NB(32), .SW_W(1024), .SM_H(16), .SM_LPH(16),
                     .SM_NVMAX(40), .S_RD(16), .S_WR(16), .LM(5), .LA(4), .MUT(0)) u_t (
        .clk(ck), .rst_in(rst), .dn_st_i(dn_st), .dn_kind_i(dn_kind), .dn_gsel_i(dn_gsel), .dn_fp4_i(dn_fp4),
        .dn_jid_i(dn_jid), .dn_v_i(dn_v), .dn_ph_i(dn_ph), .dn_idx_i(dn_idx), .dn_d_i({dn_dh, dn_dl}),
        .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den),
        .o_rdy(o_rdy), .o_rjid(o_rjid));
endmodule
module dsfd_su_t_kv (
    input  wire          ck, rst,
    input  wire          dn_st, input wire [3:0] dn_kind, input wire [1:0] dn_gsel, input wire dn_fp4,
    input  wire [7:0]    dn_jid, input wire [15:0] dn_v, input wire dn_ph, input wire [15:0] dn_idx,
    input  wire [4095:0] dn_dl, input wire [4095:0] dn_dh,
    output wire [15:0] o_v, output wire [223:0] o_a, output wire [255:0] o_m, output wire [8191:0] o_d,
    output wire          o_fu, o_fo, o_alive, o_den, o_rdy, output wire [7:0] o_rjid
);
    ot_s81_su_tile #(.TK(1), .TI(0), .NT(1), .QN_N(256), .KV_N(512), .QB_NB(32), .SW_W(1024), .SM_H(16), .SM_LPH(16),
                     .SM_NVMAX(40), .S_RD(16), .S_WR(16), .LM(5), .LA(4), .MUT(0)) u_t (
        .clk(ck), .rst_in(rst), .dn_st_i(dn_st), .dn_kind_i(dn_kind), .dn_gsel_i(dn_gsel), .dn_fp4_i(dn_fp4),
        .dn_jid_i(dn_jid), .dn_v_i(dn_v), .dn_ph_i(dn_ph), .dn_idx_i(dn_idx), .dn_d_i({dn_dh, dn_dl}),
        .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den),
        .o_rdy(o_rdy), .o_rjid(o_rjid));
endmodule
module dsfd_su_t_qb (
    input  wire          ck, rst,
    input  wire          dn_st, input wire [3:0] dn_kind, input wire [1:0] dn_gsel, input wire dn_fp4,
    input  wire [7:0]    dn_jid, input wire [15:0] dn_v, input wire dn_ph, input wire [15:0] dn_idx,
    input  wire [4095:0] dn_dl, input wire [4095:0] dn_dh,
    output wire [3:0] o_v, output wire [55:0] o_a, output wire [63:0] o_m, output wire [2047:0] o_d,
    output wire          o_fu, o_fo, o_alive, o_den, o_rdy, output wire [7:0] o_rjid
);
    ot_s81_su_tile #(.TK(2), .TI(0), .NT(4), .QN_N(256), .KV_N(512), .QB_NB(32), .SW_W(1024), .SM_H(16), .SM_LPH(16),
                     .SM_NVMAX(40), .S_RD(16), .S_WR(16), .LM(5), .LA(4), .MUT(0)) u_t (
        .clk(ck), .rst_in(rst), .dn_st_i(dn_st), .dn_kind_i(dn_kind), .dn_gsel_i(dn_gsel), .dn_fp4_i(dn_fp4),
        .dn_jid_i(dn_jid), .dn_v_i(dn_v), .dn_ph_i(dn_ph), .dn_idx_i(dn_idx), .dn_d_i({dn_dh, dn_dl}),
        .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den),
        .o_rdy(o_rdy), .o_rjid(o_rjid));
endmodule
module dsfd_su_t_sw (
    input  wire          ck, rst,
    input  wire          dn_st, input wire [3:0] dn_kind, input wire [1:0] dn_gsel, input wire dn_fp4,
    input  wire [7:0]    dn_jid, input wire [15:0] dn_v, input wire dn_ph, input wire [15:0] dn_idx,
    input  wire [4095:0] dn_dl, input wire [4095:0] dn_dh,
    output wire [1:0] o_v, output wire [27:0] o_a, output wire [31:0] o_m, output wire [1023:0] o_d,
    output wire          o_fu, o_fo, o_alive, o_den, o_rdy, output wire [7:0] o_rjid
);
    ot_s81_su_tile #(.TK(3), .TI(0), .NT(8), .QN_N(256), .KV_N(512), .QB_NB(32), .SW_W(1024), .SM_H(16), .SM_LPH(16),
                     .SM_NVMAX(40), .S_RD(16), .S_WR(16), .LM(5), .LA(4), .MUT(0)) u_t (
        .clk(ck), .rst_in(rst), .dn_st_i(dn_st), .dn_kind_i(dn_kind), .dn_gsel_i(dn_gsel), .dn_fp4_i(dn_fp4),
        .dn_jid_i(dn_jid), .dn_v_i(dn_v), .dn_ph_i(dn_ph), .dn_idx_i(dn_idx), .dn_d_i({dn_dh, dn_dl}),
        .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den),
        .o_rdy(o_rdy), .o_rjid(o_rjid));
endmodule
module dsfd_su_t_sm (
    input  wire          ck, rst,
    input  wire          dn_st, input wire [3:0] dn_kind, input wire [1:0] dn_gsel, input wire dn_fp4,
    input  wire [7:0]    dn_jid, input wire [15:0] dn_v, input wire dn_ph, input wire [15:0] dn_idx,
    input  wire [4095:0] dn_dl, input wire [4095:0] dn_dh,
    output wire [1:0] o_v, output wire [27:0] o_a, output wire [31:0] o_m, output wire [1023:0] o_d,
    output wire          o_fu, o_fo, o_alive, o_den, o_rdy, output wire [7:0] o_rjid
);
    ot_s81_su_tile #(.TK(4), .TI(0), .NT(8), .QN_N(256), .KV_N(512), .QB_NB(32), .SW_W(1024), .SM_H(16), .SM_LPH(16),
                     .SM_NVMAX(40), .S_RD(16), .S_WR(16), .LM(5), .LA(4), .MUT(0)) u_t (
        .clk(ck), .rst_in(rst), .dn_st_i(dn_st), .dn_kind_i(dn_kind), .dn_gsel_i(dn_gsel), .dn_fp4_i(dn_fp4),
        .dn_jid_i(dn_jid), .dn_v_i(dn_v), .dn_ph_i(dn_ph), .dn_idx_i(dn_idx), .dn_d_i({dn_dh, dn_dl}),
        .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den),
        .o_rdy(o_rdy), .o_rjid(o_rjid));
endmodule
