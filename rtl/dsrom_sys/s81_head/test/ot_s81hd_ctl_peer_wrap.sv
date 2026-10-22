// ot_s81hd_ctl_peer wrapper only (copied verbatim from ot_s81hd_ctl_peer.sv eb58f5989) for benches of an alternative ot_s81hd_ctl_glue body (glue R3).
module ot_s81hd_ctl_peer (
    input  wire              ck,
    input  wire              rst_n,
    // stage-circuit endpoint (ot_s81hd_lep, ring form)
    input  wire [1103:0]     ri,
    input  wire [31:0]       mu_rt,
    input  wire [10:0]       lw,
    input  wire              lep_f,
    output wire [1103:0]     ro,
    output wire [33:0]       mu_c,
    output wire [10:0]       mu_rc,
    output wire              ctl_f,
    // spines (bus B)
    output wire [564:0]      sn_o,
    output wire [564:0]      ss_o,
    input  wire [564:0]      sn_i,
    input  wire [564:0]      ss_i,
    // 6 TP4 mesh lanes
    output wire [5:0]        mtx_v,
    output wire [6*553-1:0]  mtx_d,
    input  wire [5:0]        mrx_v,
    input  wire [6*553-1:0]  mrx_d,
    input  wire [23:0]       mflt,
    // 2 host lanes
    output wire [1:0]        htx_v,
    output wire [2*553-1:0]  htx_d,
    input  wire [1:0]        hrx_v,
    input  wire [2*553-1:0]  hrx_d,
    input  wire [7:0]        hflt,
    // 5 draft lanes
    output wire [4:0]        dtx_v,
    output wire [5*553-1:0]  dtx_d,
    input  wire [4:0]        drx_v,
    input  wire [5*553-1:0]  drx_d,
    input  wire [19:0]       dflt
);
    wire [0:0] seq_rst;
    wire [41:0] seq_f_cfg;
    wire [0:0] seq_f_rv;
    wire [511:0] seq_f_rd;
    wire [0:0] seq_t_rg;
    wire [0:0] seq_t_tv;
    wire [511:0] seq_t_td;
    wire [0:0] seq_f_tg;
    wire [0:0] seq_t_sv;
    wire [76:0] seq_t_sd;
    wire [0:0] seq_f_sg;
    wire [0:0] seq_f_wv;
    wire [9:0] seq_f_wd;
    wire [0:0] seq_t_wg;
    wire [0:0] seq_t_hv;
    wire [33:0] seq_t_hd;
    wire [0:0] seq_f_hg;
    wire [0:0] seq_f_qv;
    wire [33:0] seq_f_qd;
    wire [0:0] seq_t_qg;
    wire [56:0] seq_t_acc;
    ot_s81hd_ctl_glue u_glue (.ck(ck), .rst_n(rst_n), .ri(ri), .mu_rt(mu_rt), .lw(lw), .lep_f(lep_f), .ro(ro), .mu_c(mu_c), .mu_rc(mu_rc), .ctl_f(ctl_f), .sn_o(sn_o), .ss_o(ss_o), .sn_i(sn_i), .ss_i(ss_i), .mtx_v(mtx_v), .mtx_d(mtx_d), .mrx_v(mrx_v), .mrx_d(mrx_d), .mflt(mflt), .htx_v(htx_v), .htx_d(htx_d), .hrx_v(hrx_v), .hrx_d(hrx_d), .hflt(hflt), .dtx_v(dtx_v), .dtx_d(dtx_d), .drx_v(drx_v), .drx_d(drx_d), .dflt(dflt), .seq_rst(seq_rst), .seq_f_cfg(seq_f_cfg), .seq_f_rv(seq_f_rv), .seq_f_rd(seq_f_rd), .seq_t_rg(seq_t_rg), .seq_t_tv(seq_t_tv), .seq_t_td(seq_t_td), .seq_f_tg(seq_f_tg), .seq_t_sv(seq_t_sv), .seq_t_sd(seq_t_sd), .seq_f_sg(seq_f_sg), .seq_f_wv(seq_f_wv), .seq_f_wd(seq_f_wd), .seq_t_wg(seq_t_wg), .seq_t_hv(seq_t_hv), .seq_t_hd(seq_t_hd), .seq_f_hg(seq_f_hg), .seq_f_qv(seq_f_qv), .seq_f_qd(seq_f_qd), .seq_t_qg(seq_t_qg), .seq_t_acc(seq_t_acc));
    dsfd_mtp_seq u_seq (.ck(ck), .rst(seq_rst), .f_cfg(seq_f_cfg), .f_rv(seq_f_rv), .f_rd(seq_f_rd), .t_rg(seq_t_rg), .t_tv(seq_t_tv), .t_td(seq_t_td), .f_tg(seq_f_tg), .t_sv(seq_t_sv), .t_sd(seq_t_sd), .f_sg(seq_f_sg), .f_wv(seq_f_wv), .f_wd(seq_f_wd), .t_wg(seq_t_wg), .t_hv(seq_t_hv), .t_hd(seq_t_hd), .f_hg(seq_f_hg), .f_qv(seq_f_qv), .f_qd(seq_f_qd), .t_qg(seq_t_qg), .t_acc(seq_t_acc));
endmodule
