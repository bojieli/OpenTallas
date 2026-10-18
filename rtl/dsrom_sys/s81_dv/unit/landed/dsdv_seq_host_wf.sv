`timescale 1ns/1ps
// PL-SEQ (PARENTS-LANDED 10-18): WIRES-ONLY flat form of dsdv_seq_host (rtl/dsrom_sys/s81_dv/unit/dsdv_seq_host.sv) for
// tools/landed_parent/lp.py.  Identical to dsdv_seq_host at MUT = 0 / STAGE = 0 / V = 276 (the die instance): the same five
// leaves and nets, without the MUT == 3 generate (bench negative control of the flat unit) and without #() on the hard
// children (their defaults are the die's parameters).  lp.py builds dsdv_seq_host_wf_lp (landed regions) from it.
module dsdv_seq_host_wf #(parameter integer V = 276) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [7:0]    tap_k, sink_k,
    input  wire [V-1:0]  vi_s, output wire [V-1:0] vo_s,
    input  wire [V-1:0]  vi_n, output wire [V-1:0] vo_n,
    input  wire [514:0]  f_host, output wire [76:0] t_host, input wire [3:0] f_lf,
    input  wire [52:0]   f_ks,   output wire [53:0] t_kd,
    output wire [32:0]   s_j,    input  wire [1:0]  s_jd_w, s_jd_e,
    output wire [291:0]  s_hw_w, s_hw_e, input wire [8:0] s_hc_w, s_hc_e,
    input  wire [1:0]    st_rg_w, st_rg_e,
    output wire          cw_v, output wire [9:0] cw_a, output wire [255:0] cw_d
);
    wire [V-1:0] n01, s10, n12, s21, n23, s32, n34, s43;
    wire [35:0] pw01; wire [8:0] pl01; wire [193:0] tw01, tw12; wire [52:0] ks01; wire [53:0] kd10; wire [32:0] j10;
    wire [1:0] jd01; wire [5:0] sq10; wire vf10, vf21; wire [84:0] cn12, cs12, cg12; wire [26:0] dn21; wire [266:0] cf01, cf12;
    dsdv_sh_lk u_l0 (.ck(ck), .ck_ih(ck), .ck_ic(ck), .rst_n(rst_n), .f_host(f_host), .t_host(t_host), .f_lf(f_lf), .f_ks(f_ks), .t_kd(t_kd),
        .s_j(s_j), .s_jd_w(s_jd_w), .s_jd_e(s_jd_e), .s_hw_w(s_hw_w), .s_hw_e(s_hw_e), .s_hc_w(s_hc_w),
        .s_hc_e(s_hc_e), .st_rg_w(st_rg_w), .st_rg_e(st_rg_e), .vi_s(vi_s), .vo_s(vo_s),
        .rn_o(n01), .rs_i(s10), .pw_o(pw01), .pl_o(pl01), .tw_o(tw01), .cf_o(cf01), .ks_o(ks01), .kd_i(kd10), .j_i(j10), .jd_o(jd01),
        .sq_i(sq10), .vf_i(vf10));
    dsdv_sh_sq u_l1 (.ck(ck), .rst_n(rst_n), .rn_i(n01), .rs_o(s10), .pw_i(pw01),
        .pl_i(pl01), .tw_i(tw01), .cf_i(cf01), .ks_i(ks01), .kd_o(kd10), .j_o(j10), .jd_i(jd01), .sq_o(sq10), .vf_o(vf10),
        .rn_o(n12), .rs_i(s21), .tw_o(tw12), .cf_o(cf12), .cn_o(cn12), .cs_o(cs12), .cg_o(cg12), .dn_i(dn21), .vf_i(vf21));
    dsdv_sh_vc u_l2 (.ck(ck), .rst_n(rst_n), .tap_k(tap_k), .sink_k(sink_k), .vi_s(n12), .vo_n(n23),
        .vi_n(s32), .vo_s(s21), .tw_i(tw12), .cn_i(cn12), .cs_i(cs12), .cf_i(cf12), .cg_i(cg12), .dn_o(dn21), .vf_o(vf21),
        .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d));
    dsdv_sh_ft u_l3 (.ck(ck), .ni(n23), .no(n34), .si(s43), .so(s32));
    dsdv_sh_ft u_l4 (.ck(ck), .ni(n34), .no(vo_n), .si(vi_n), .so(s43));
endmodule
