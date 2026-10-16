`timescale 1ns/1ps
// Hardened tile masters of dsfd_sp_su_h (s81-suhc-hier-1011) at production params (QN_N 256, KV_N 512, QB_NB 32,
// SW_W 1024, SM_H 16, SM_LPH 16, S_RD 16, S_WR 16, LM 5, LA 4); pins: tools/s81_suhc/su_tiles_plan.py.  Engine tiles
// take the down-spine row data split dn_dl / dn_dh by face.  Every master <= ~600 x 600 um.
// dsfd_su_t_qn0 / dsfd_su_t_qn1 replaced by the QN v3 split masters (dsfd_su_t_qn.sv)
// dsfd_su_t_kv0 / dsfd_su_t_kv1 replaced by the KV v3 split masters (dsfd_su_t_kv.sv)
// dsfd_su_t_sm replaced by the SM v3 split masters (dsfd_su_t_sm.sv)
// dsfd_su_t_sw replaced by the SW v3 split masters (dsfd_su_t_sw.sv: dsfd_su_t_swt + dsfd_su_t_swe; quant = dsfd_su_t_qbe)
// pin owner: 4 VM read + 4 VM write slots of the slab pins
module dsfd_su_t_pin (
    input  wire ck, rst,
    output wire [3:0] rq_v, output wire [55:0] rq_row, input wire [3:0] rs_v, input wire [2047:0] rs_d,
    output wire [3:0] wq_v, output wire [55:0] wq_row, output wire [63:0] wq_mask, output wire [2047:0] wq_d,
    output wire [3:0] dn_v, output wire [2047:0] dn_d,
    input  wire [3:0] up_v, input wire [55:0] up_a, input wire [63:0] up_m, input wire [2047:0] up_d,
    input  wire [3:0] c_rq_v, input wire [55:0] c_rq_row, output wire [3:0] c_rv, output wire [119:0] c_rf,
    output wire [3:0] c_uv
);
    ot_s81_su_pin #(.KR(4), .KW(4)) u_p (.clk(ck), .rst_in(rst), .rq_v(rq_v), .rq_row(rq_row), .rs_v(rs_v), .rs_d(rs_d),
        .wq_v(wq_v), .wq_row(wq_row), .wq_mask(wq_mask), .wq_d(wq_d), .dn_v(dn_v), .dn_d(dn_d), .up_v(up_v), .up_a(up_a),
        .up_m(up_m), .up_d(up_d), .c_rq_v(c_rq_v), .c_rq_row(c_rq_row), .c_rv(c_rv), .c_rf(c_rf), .c_uv(c_uv));
endmodule
// control tile: engine adapter (cck CDC) + job control
module dsfd_su_t_ctl (
    input  wire cck, crs, sk, srs, c_cmd_v, input wire [83:0] c_cmd_d, output wire c_done_v, output wire [7:0] c_done_tag,
    input  wire inp, output wire flt, online, output wire [3:0] fcode, output wire rst_o,
    output wire [15:0] p_rq_v, output wire [223:0] p_rq_row, input wire [15:0] p_rv, input wire [479:0] p_rf,
    input  wire [15:0] p_uv,
    output wire dn_st, output wire [3:0] dn_kind, output wire [1:0] dn_gsel, output wire dn_fp4, output wire [7:0] dn_jid,
    input  wire up_fu, up_fo, up_alive, up_den, up_rdy, input wire [7:0] up_rjid
);
    ot_s81_su_ctl #(.QN_N(256), .KV_N(512), .QB_NB(32), .SW_W(1024), .SM_H(16), .SM_LPH(16), .S_RD(16), .S_WR(16),
                    .NSW(16), .NQB(16), .NQN(4), .NKV(2), .MUT(0), .AMUT(0)) u_c (
        .cck(cck), .crs(crs), .sk(sk), .srs(srs), .c_cmd_v(c_cmd_v), .c_cmd_d(c_cmd_d), .c_done_v(c_done_v),
        .c_done_tag(c_done_tag), .inp(inp), .flt(flt), .online(online), .fcode(fcode), .rst_o(rst_o),
        .p_rq_v(p_rq_v), .p_rq_row(p_rq_row), .p_rv(p_rv), .p_rf(p_rf), .p_uv(p_uv),
        .dn_st(dn_st), .dn_kind(dn_kind), .dn_gsel(dn_gsel), .dn_fp4(dn_fp4), .dn_jid(dn_jid),
        .up_fu(up_fu), .up_fo(up_fo), .up_alive(up_alive), .up_den(up_den), .up_rdy(up_rdy), .up_rjid(up_rjid),.up_cp_done(1'b0));
endmodule
