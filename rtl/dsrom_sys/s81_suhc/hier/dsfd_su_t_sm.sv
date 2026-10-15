`timescale 1ns/1ps
// SM (el1011-s81su-sm, spec v3): production masters of the split softmax SE / SO (rtl ot_s81_su_sm.sv), each hardened
// once: the tap/out (x 8 stops), the lane (x 16 a head), the sum and the root (x 1 a head), the divide pair (x 8 a head).
module dsfd_su_t_smt (
    input  wire          ck, rst, input wire [3:0] cfg_ti,
    input  wire          dn_st, input wire [3:0] dn_kind, input wire [7:0] dn_jid, input wire [15:0] dn_v,
    input  wire [2559:0] dn_p,
    output wire          s_v, p_v, output wire c_v, output wire [6:0] c_nv,
    output wire [2:0]    c_lt, output wire [31:0] c_scale, output wire [63:0] c_sink,
    output wire          cs_v, output wire [4:0] cs_i, output wire [63:0] cs_d,
    input  wire          e_v, input wire [1023:0] e_d, input wire o_vi, input wire [511:0] o_di, input wire den_v, f_i,
    output wire [1:0] o_v, output wire [27:0] o_a, output wire [31:0] o_m, output wire [1023:0] o_d,
    output wire          o_fu, o_fo, o_alive, o_den, o_rdy, output wire [7:0] o_rjid
);
    ot_s81_su_smt #(.SM_H(16), .SM_LPH(16), .S_RD(16), .WS(2)) u_t (
        .clk(ck), .rst_in(rst), .cfg_ti(cfg_ti), .dn_st_i(dn_st), .dn_kind_i(dn_kind), .dn_jid_i(dn_jid), .dn_v_i(dn_v),
        .dn_p_i(dn_p), .s_v(s_v), .p_v(p_v), .c_v(c_v), .c_nv(c_nv), .c_lt(c_lt),
        .c_scale(c_scale), .c_sink(c_sink), .cs_v(cs_v), .cs_i(cs_i), .cs_d(cs_d), .e_v_i(e_v), .e_d_i(e_d),
        .o_v_i(o_vi), .o_d_i(o_di), .den_v_i(den_v), .f_i(f_i), .o_v(o_v), .o_a(o_a), .o_m(o_m), .o_d(o_d),
        .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den), .o_rdy(o_rdy), .o_rjid(o_rjid));
endmodule
module dsfd_su_t_sml (
    input  wire          ck, rst, sk_en,
    input  wire          i_cv, input wire [6:0] i_nv, input wire [31:0] i_scale, input wire [31:0] i_sink,
    input  wire          i_sv, input wire [31:0] i_s, input wire i_mv, input wire [31:0] i_nmb,
    output wire          o_mxv, output wire [31:0] o_mx, output wire o_ev, o_es, o_el, output wire [31:0] o_e
);
    ot_s81_su_sml #(.NVMAX(40), .LM(5), .LA(4)) u_l (
        .clk(ck), .rst_in(rst), .sk_en(sk_en), .i_cv(i_cv), .i_nv(i_nv), .i_scale(i_scale), .i_sink(i_sink),
        .i_sv(i_sv), .i_s(i_s), .i_mv(i_mv), .i_nmb(i_nmb), .o_mxv(o_mxv), .o_mx(o_mx), .o_ev(o_ev), .o_es(o_es),
        .o_el(o_el), .o_e(o_e));
endmodule
module dsfd_su_t_smc (
    input  wire          ck, rst, i_v, i_l, input wire [511:0] i_e,
    output wire          o_v, o_l, output wire [31:0] o_s
);
    ot_s81_su_smc #(.LPH(16), .LA(4)) u_c (.clk(ck), .rst_in(rst), .i_v(i_v), .i_l(i_l), .i_e(i_e), .o_v(o_v),
        .o_l(o_l), .o_s(o_s));
endmodule
module dsfd_su_t_smr (
    input  wire          ck, rst, i_cv, input wire [2:0] i_lt, input wire i_mxv, input wire [511:0] i_mx,
    input  wire          i_skv, input wire [31:0] i_sk, input wire i_vv, i_vl, input wire [31:0] i_vs,
    output wire          o_mv, output wire [31:0] o_nmb, output wire o_dv, output wire [31:0] o_den
);
    ot_s81_su_smr #(.LPH(16), .LA(4)) u_r (.clk(ck), .rst_in(rst), .i_cv(i_cv), .i_lt(i_lt), .i_mxv(i_mxv), .i_mx(i_mx),
        .i_skv(i_skv), .i_sk(i_sk), .i_vv(i_vv), .i_vl(i_vl), .i_vs(i_vs), .o_mv(o_mv), .o_nmb(o_nmb), .o_dv(o_dv),
        .o_den(o_den));
endmodule
module dsfd_su_t_smd (
    input  wire          ck, rst, input wire [2:0] cfg_p,
    input  wire          i_pv, input wire [63:0] i_pa, input wire i_dv, input wire [31:0] i_den,
    input  wire          i_csv, input wire [4:0] i_csi, input wire [63:0] i_csd,
    output wire          o_ov, output wire [31:0] o_o, output wire o_f
);
    ot_s81_su_smd #(.LPH(16), .LM(5), .LA(4)) u_d (.clk(ck), .rst_in(rst), .cfg_p(cfg_p), .i_pv(i_pv), .i_pa(i_pa),
        .i_dv(i_dv), .i_den(i_den), .i_csv(i_csv), .i_csi(i_csi), .i_csd(i_csd), .o_ov(o_ov), .o_o(o_o), .o_f(o_f));
endmodule
