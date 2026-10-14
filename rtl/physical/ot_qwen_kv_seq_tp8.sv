`timescale 1ns/1ps
// Opt-in native TP8 masters. Fresh core/xs views required; historical CLOSED views stand.
module qkd_seq_core_tp8 (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          x3_v,
    input  wire [10:0]   x3_tag,
    output wire          x3_cr,
    input  wire [55:0]   r_sd,
    input  wire [43:0]   r_kvd,
    output wire [519:0]  t_ar_d,
    input  wire          t_ar_cr,
    output wire [186:0]  t_ds,
    output wire [74:0]   t_pw,
    output wire          s_qpop,
    output wire          s_kpop,
    output wire [2:0]    s_kidx,
    output wire          s_kwgo,
    output wire [1:0]    s_kwn,
    output wire [27:0]   f_aqm_w,                 // W fans (WS, WN) / E fans (ES, EN): own registered copies
    output wire [27:0]   f_aqm_e,
    output wire [22:0]   f_kwm_w,
    output wire [22:0]   f_kwm_e,
    output wire [32:0]   f_kc_w,
    output wire [32:0]   f_kc_e,
    input  wire [1:0]    f_cr_w,                  // {WN, WS}
    input  wire [1:0]    f_cr_e,                  // {EN, ES}
    input  wire [1:0]    f_af_w,
    input  wire [1:0]    f_af_e,
    input  wire [1:0]    f_mf_w,
    input  wire [1:0]    f_mf_e,
    output wire          hs,
    input  wire [519:0]  ar,
    input  wire          hf,
    input  wire [181:0]  hc,
    output wire [92:0]   tk,
    output wire [9:0]    kst
);
 qkd_seq_core #(.HEADS(1), .Q_FP32(1)) u_native (
 .ck(ck),
 .rst_n(rst_n),
 .x3_v(x3_v),
 .x3_tag(x3_tag),
 .x3_cr(x3_cr),
 .r_sd(r_sd),
 .r_kvd(r_kvd),
 .t_ar_d(t_ar_d),
 .t_ar_cr(t_ar_cr),
 .t_ds(t_ds),
 .t_pw(t_pw),
 .s_qpop(s_qpop),
 .s_kpop(s_kpop),
 .s_kidx(s_kidx),
 .s_kwgo(s_kwgo),
 .s_kwn(s_kwn),
 .f_aqm_w(f_aqm_w),
 .f_aqm_e(f_aqm_e),
 .f_kwm_w(f_kwm_w),
 .f_kwm_e(f_kwm_e),
 .f_kc_w(f_kc_w),
 .f_kc_e(f_kc_e),
 .f_cr_w(f_cr_w),
 .f_cr_e(f_cr_e),
 .f_af_w(f_af_w),
 .f_af_e(f_af_e),
 .f_mf_w(f_mf_w),
 .f_mf_e(f_mf_e),
 .hs(hs),
 .ar(ar),
 .hf(hf),
 .hc(hc),
 .tk(tk),
 .kst(kst));
endmodule
module qkd_seq_xs_tp8 (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          x_v,
    input  wire [2:0]    x_cls,
    input  wire [127:0]  x_d,
    input  wire          qpop,
    input  wire          kpop,
    input  wire [2:0]    kidx,
    input  wire          kwgo,
    input  wire [1:0]    kwn,
    output wire [127:0]  q_w,                     // to the W fans / the E fans: own registered copies
    output wire [127:0]  q_e,
    output wire [255:0]  kw_w,                    // {word {vg, 1} slice, word {vg, 0} slice}
    output wire [255:0]  kw_e
);
 qkd_seq_xs #(.HEADS(1)) u_native (
 .ck(ck),
 .rst_n(rst_n),
 .x_v(x_v),
 .x_cls(x_cls),
 .x_d(x_d),
 .qpop(qpop),
 .kpop(kpop),
 .kidx(kidx),
 .kwgo(kwgo),
 .kwn(kwn),
 .q_w(q_w),
 .q_e(q_e),
 .kw_w(kw_w),
 .kw_e(kw_e));
endmodule
module qkd_seq_tp8 (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [523:0]  r_x3_d,
    output wire          r_x3_cr,
    input  wire [55:0]   r_sd,
    input  wire [43:0]   r_kvd,
    output wire [519:0]  t_ar_d,
    input  wire          t_ar_cr,
    output wire [186:0]  t_ds,
    output wire [74:0]   t_pw,
    output wire [539:0]  aq_WS,
    output wire [539:0]  aq_WN,
    output wire [539:0]  aq_ES,
    output wire [539:0]  aq_EN,
    output wire [1046:0] kvn_WS_d,
    output wire [1046:0] kvn_WN_d,
    output wire [1046:0] kvn_ES_d,
    output wire [1046:0] kvn_EN_d,
    input  wire          kvn_WS_cr,
    input  wire          kvn_WN_cr,
    input  wire          kvn_ES_cr,
    input  wire          kvn_EN_cr,
    output wire [32:0]   kc_WS,
    output wire [32:0]   kc_WN,
    output wire [32:0]   kc_ES,
    output wire [32:0]   kc_EN,
    input  wire          af_WS,
    input  wire          af_WN,
    input  wire          af_ES,
    input  wire          af_EN,
    input  wire          mf_WS,
    input  wire          mf_WN,
    input  wire          mf_ES,
    input  wire          mf_EN,
    input  wire [519:0]  ar,
    input  wire          hf,
    output wire          hs,
    input  wire [181:0]  hc,
    output wire [92:0]   tk,
    output wire [9:0]    kst
);
    wire          s_qpop, s_kpop, s_kwgo;
    wire [2:0]    s_kidx;
    wire [1:0]    s_kwn;
    wire [27:0]   f_aqm [0:1];
    wire [22:0]   f_kwm [0:1];
    wire [32:0]   f_kc  [0:1];
    wire [3:0]    f_cr, f_af, f_mf;
    wire [255:0]  sq  [0:3];
    wire [511:0]  skw [0:3];
    qkd_seq_core_tp8 u_core (.ck(ck), .rst_n(rst_n), .x3_v(r_x3_d[523]), .x3_tag(r_x3_d[522:512]), .x3_cr(r_x3_cr), .r_sd(r_sd),
        .r_kvd(r_kvd), .t_ar_d(t_ar_d), .t_ar_cr(t_ar_cr), .t_ds(t_ds), .t_pw(t_pw),
        .s_qpop(s_qpop), .s_kpop(s_kpop), .s_kidx(s_kidx), .s_kwgo(s_kwgo), .s_kwn(s_kwn), .f_aqm_w(f_aqm[0]),
        .f_aqm_e(f_aqm[1]), .f_kwm_w(f_kwm[0]), .f_kwm_e(f_kwm[1]), .f_kc_w(f_kc[0]), .f_kc_e(f_kc[1]), .f_cr_w(f_cr[1:0]),
        .f_cr_e(f_cr[3:2]), .f_af_w(f_af[1:0]), .f_af_e(f_af[3:2]), .f_mf_w(f_mf[1:0]), .f_mf_e(f_mf[3:2]), .hs(hs), .ar(ar), .hf(hf), .hc(hc),
        .tk(tk), .kst(kst));
    genvar s, k;
    generate for (s = 0; s < 4; s = s + 1) begin : g_xs
        qkd_seq_xs_tp8 u_xs (.ck(ck), .rst_n(rst_n), .x_v(r_x3_d[523]), .x_cls(r_x3_d[522:520]), .x_d(r_x3_d[128*s +: 128]),
            .qpop(s_qpop), .kpop(s_kpop), .kidx(s_kidx), .kwgo(s_kwgo), .kwn(s_kwn), .q_w(sq[s][127:0]), .q_e(sq[s][255:128]), .kw_w(skw[s][255:0]), .kw_e(skw[s][511:256]));
    end endgenerate
    // the store slices' two copies -> the full words of the W (copy 0) and E (copy 1) fans
    wire [511:0]  fq  [0:1];
    wire [1023:0] fkw [0:1];
    generate for (k = 0; k < 2; k = k + 1) begin : g_cp
        for (s = 0; s < 4; s = s + 1) begin : g_s
`ifdef OT_QKD_SEQ_MUT
            assign fq[k][128*s +: 128] = (k == 1 && s < 2) ? sq[1 - s][128*k +: 128] : sq[s][128*k +: 128];
`else
            assign fq[k][128*s +: 128] = sq[s][128*k +: 128];
`endif
            assign fkw[k][128*s +: 128]       = skw[s][256*k +: 128];
            assign fkw[k][512 + 128*s +: 128] = skw[s][256*k + 128 +: 128];
        end
    end endgenerate
    wire [539:0]  aq  [0:3];
    wire [1046:0] kvn [0:3];
    wire [32:0]   kc  [0:3];
    wire [3:0]    cr = {kvn_EN_cr, kvn_ES_cr, kvn_WN_cr, kvn_WS_cr};
    wire [3:0]    af = {af_EN, af_ES, af_WN, af_WS};
    wire [3:0]    mf = {mf_EN, mf_ES, mf_WN, mf_WS};
    generate for (k = 0; k < 4; k = k + 1) begin : g_fan
        qkd_seq_fan u_fan (.ck(ck), .rst_n(rst_n), .aqm(f_aqm[k/2]), .q(fq[k/2]), .kwm(f_kwm[k/2]),
            .kw(fkw[k/2]), .kc_i(f_kc[k/2]), .aq(aq[k]), .kvn(kvn[k]), .kc(kc[k]), .kvn_cr(cr[k]), .af(af[k]),
            .mf(mf[k]), .cr_o(f_cr[k]), .af_o(f_af[k]), .mf_o(f_mf[k]));
    end endgenerate
    assign aq_WS = aq[0];   assign aq_WN = aq[1];   assign aq_ES = aq[2];   assign aq_EN = aq[3];
    assign kvn_WS_d = kvn[0]; assign kvn_WN_d = kvn[1]; assign kvn_ES_d = kvn[2]; assign kvn_EN_d = kvn[3];
    assign kc_WS = kc[0];   assign kc_WN = kc[1];   assign kc_ES = kc[2];   assign kc_EN = kc[3];
endmodule
