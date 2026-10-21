`timescale 1ns/1ps
// PL-SEQ option B (PARENTS-LANDED decision 10-18 06:22): dsdv_seq_host_c = the COMPACT CORE of dsdv_seq_host -- leaves
// L0 dsdv_sh_lk, L1 dsdv_sh_sq, L2 dsdv_sh_vc only, pin-abutted (~255 x 471 um < 1 mm): ONE clock region, no landings
// (the L1 <-> L2 calendar loop and the L0 status fold stay in-region; nothing is re-scheduled).  The two registered rung
// hops L3 / L4 (dsdv_sh_ft) of dsdv_seq_host are NOT in the hardened parent: the vc N face rung (vo_n / vi_n) leaves the
// core directly and the col-4 lane seqhost -> s_4N is a DIE lane on CLOSED 276-b dvrlyh relays (die record counts them).
// Same leaves, nets and parameters as dsdv_seq_host (MUT / STAGE pass through to the leaves; MUT 3 is the lane's).
// Latency vs dsdv_seq_host: rung vi_s -> vo_n and vi_n -> vo_s 6 -> 4 edges inside the parent (+ k die-lane relay
// stages; k = 2 reproduces dsdv_seq_host exactly, test/dsdv_seq_host_bw.sv); every other port unchanged; reset unchanged.
// S81-GUSEQ 10-18: L0 = dsdv_sh_lk RL 1 (S81-SHLK2: rung landed at both lk faces, ONE CTS root ck -- ck_ih / ck_ic gone):
// Hardened (define OT_DSDV_SEQHOST_HARD): children without #() (hard views carry the default = hardened config).
// in-parent rung 4 + RL = 5 edges each way (V south command -> vo_s 7 + RL); host path f_host -> s_hw / t_host = golden + 2 (APIPE 7).
module dsdv_seq_host_c #(parameter integer V = 276, parameter integer STAGE = 0, parameter integer MUT = 0, parameter integer RL = 1) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [7:0]    tap_k, sink_k,   // vstop straps (captured pins); seqhost: 0 / 0
    input  wire [V-1:0]  vi_s, output wire [V-1:0] vo_s,      // rung S face (bk_sel)
    input  wire [V-1:0]  vi_n, output wire [V-1:0] vo_n,      // rung N face = vc N face (die lane to s_4N on closed dvrlyh relays)
    input  wire [514:0]  f_host, output wire [76:0] t_host, input wire [3:0] f_lf,
    input  wire [52:0]   f_ks,   output wire [53:0] t_kd,
    output wire [32:0]   s_j,    input  wire [1:0]  s_jd_w, s_jd_e,     // job broadcast to both halves / per-half done
    output wire [291:0]  s_hw_w, s_hw_e, input wire [8:0] s_hc_w, s_hc_e, // per-half host writes / credits + acks
    input  wire [1:0]    st_rg_w, st_rg_e,                               // per-half region status (svc entry st_rg)
    output wire          cw_v, output wire [9:0] cw_a, output wire [255:0] cw_d   // gunit cw port
);
    wire [V-1:0] n01, s10, n12, s21;
    wire [35:0] pw01; wire [8:0] pl01; wire [193:0] tw01, tw12; wire [52:0] ks01; wire [53:0] kd10; wire [32:0] j10;
    wire [1:0] jd01; wire [5:0] sq10; wire vf10, vf21; wire [84:0] cn12, cs12, cg12; wire [26:0] dn21; wire [266:0] cf01, cf12;
`ifdef OT_DSDV_SEQHOST_HARD
    dsdv_sh_lk u_l0 (
`else
    dsdv_sh_lk #(.V(V), .MUT(MUT), .RL(RL)) u_l0 (
`endif
        .ck(ck), .rst_n(rst_n), .f_host(f_host), .t_host(t_host), .f_lf(f_lf), .f_ks(f_ks), .t_kd(t_kd),
        .s_j(s_j), .s_jd_w(s_jd_w), .s_jd_e(s_jd_e), .s_hw_w(s_hw_w), .s_hw_e(s_hw_e), .s_hc_w(s_hc_w),
        .s_hc_e(s_hc_e), .st_rg_w(st_rg_w), .st_rg_e(st_rg_e), .vi_s(vi_s), .vo_s(vo_s),
        .rn_o(n01), .rs_i(s10), .pw_o(pw01), .pl_o(pl01), .tw_o(tw01), .cf_o(cf01), .ks_o(ks01), .kd_i(kd10), .j_i(j10), .jd_o(jd01),
        .sq_i(sq10), .vf_i(vf10));
`ifdef OT_DSDV_SEQHOST_HARD
    dsdv_sh_sq u_l1 (
`else
    dsdv_sh_sq #(.V(V), .STAGE(STAGE), .MUT(MUT)) u_l1 (
`endif
        .ck(ck), .rst_n(rst_n), .rn_i(n01), .rs_o(s10), .pw_i(pw01),
        .pl_i(pl01), .tw_i(tw01), .cf_i(cf01), .ks_i(ks01), .kd_o(kd10), .j_o(j10), .jd_i(jd01), .sq_o(sq10), .vf_o(vf10),
        .rn_o(n12), .rs_i(s21), .tw_o(tw12), .cf_o(cf12), .cn_o(cn12), .cs_o(cs12), .cg_o(cg12), .dn_i(dn21), .vf_i(vf21));
`ifdef OT_DSDV_SEQHOST_HARD
    dsdv_sh_vc u_l2 (
`else
    dsdv_sh_vc #(.V(V), .MUT(MUT)) u_l2 (
`endif
        .ck(ck), .rst_n(rst_n), .tap_k(tap_k), .sink_k(sink_k), .vi_s(n12), .vo_n(vo_n),
        .vi_n(vi_n), .vo_s(s21), .tw_i(tw12), .cn_i(cn12), .cs_i(cs12), .cf_i(cf12), .cg_i(cg12), .dn_o(dn21), .vf_o(vf21),
        .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d));
endmodule
