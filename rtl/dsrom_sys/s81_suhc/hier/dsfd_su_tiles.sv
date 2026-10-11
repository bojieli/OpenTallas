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
// root tile master: ot_s81_su_root at production params (the slab's adapter + control + VM pin flops)
module dsfd_su_t_root (
    input  wire cck, crs, sk, srs, c_cmd_v, input wire [83:0] c_cmd_d, output wire c_done_v, output wire [7:0] c_done_tag,
    input  wire inp, output wire [15:0] rq_v, output wire [223:0] rq_row, input wire [15:0] rs_v, input wire [8191:0] rs_d,
    output wire [15:0] wq_v, output wire [223:0] wq_row, output wire [255:0] wq_mask, output wire [8191:0] wq_d,
    output wire flt, online, output wire [3:0] fcode, output wire rst_o,
    output wire dn_st, output wire [3:0] dn_kind, output wire [1:0] dn_gsel, output wire dn_fp4, output wire [7:0] dn_jid,
    output wire [15:0] dn_v, output wire dn_ph, output wire [15:0] dn_idx, output wire [8191:0] dn_d,
    input  wire [15:0] up_v, input wire [223:0] up_a, input wire [255:0] up_m, input wire [8191:0] up_d,
    input  wire up_fu, up_fo, up_alive, up_den, up_rdy, input wire [7:0] up_rjid
);
    ot_s81_su_root #(.QN_N(256), .KV_N(512), .QB_NB(32), .SW_W(1024), .SM_H(16), .SM_LPH(16), .S_RD(16), .S_WR(16),
                     .NSW(8), .NQB(4), .MUT(0), .AMUT(0)) u_r (
        .cck(cck), .crs(crs), .sk(sk), .srs(srs), .c_cmd_v(c_cmd_v), .c_cmd_d(c_cmd_d), .c_done_v(c_done_v),
        .c_done_tag(c_done_tag), .inp(inp), .rq_v(rq_v), .rq_row(rq_row), .rs_v(rs_v), .rs_d(rs_d), .wq_v(wq_v),
        .wq_row(wq_row), .wq_mask(wq_mask), .wq_d(wq_d), .flt(flt), .online(online), .fcode(fcode), .rst_o(rst_o),
        .dn_st(dn_st), .dn_kind(dn_kind), .dn_gsel(dn_gsel), .dn_fp4(dn_fp4), .dn_jid(dn_jid), .dn_v(dn_v), .dn_ph(dn_ph),
        .dn_idx(dn_idx), .dn_d(dn_d), .up_v(up_v), .up_a(up_a), .up_m(up_m), .up_d(up_d), .up_fu(up_fu), .up_fo(up_fo),
        .up_alive(up_alive), .up_den(up_den), .up_rdy(up_rdy), .up_rjid(up_rjid));
endmodule
