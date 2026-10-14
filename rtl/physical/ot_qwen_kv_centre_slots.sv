`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen ROM TP8 die (track B, KV merged), KV-centre cells, 2026-10-13 (el1013-qwen-kvcentre).
//
// qkd_seq       the merged-die KV sequencer as a CLUSTER: a wires-only parent on the contract slot `seq` over nine
//               hardened leaves (three masters), each with its own clock root, every pin a register:
//                 qkd_seq_core x 1   control (ot_qkvd_seq_m_ctl): ROM-side words, hub, host, credits
//                 qkd_seq_xs   x 4   x3 data storage, bit slice s = word bits [128 s +: 128] (ot_qkvd_seq_m_store)
//                 qkd_seq_fan  x 4   quadrant pin registers WS / WN / ES / EN (ot_qkvd_seq_m_fan)
//               Flat reference: ot_qkvd_kv_seq_merged (rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_seq_merged.sv).
//               Pin bundles (first field = MSB; x_d with the flow + x_cr against it):
//                 r_x3_d[523:0] {v, tag 11, d 512} in     r_x3_cr out
//                 r_sd[55:0]   {rom_fault, kv_write_flush, coll_busy, core_fault, s_fault, s_done, ntok 18, nval 32} in
//                 r_kvd[43:0]  {v, kindk, pos 18, wbase 24} in
//                 t_ar_d[519:0] {v, g, beat 6, 16 FP32} out   t_ar_cr in
//                 t_ds[186:0]  {dw_v, dw_addr 3, dw_data 64, pw_v, pw_addr 10, pw_data 64, kv_write_drained, h_start,
//                               stage 6, tp_token 18, tp_pos 18} out
//                 t_pw[74:0]   {v, addr 10, data 64} out
//                 aq_<q>[539:0] {start, T 14, layer 6, q valid, beat 6, data 512} out
//                 kvn_<q>_d[1046:0] {v, vg 2, t 14, layer 6, row 1024} out   kvn_<q>_cr in
//                 kc_<q>[32:0] {v, d 32} out    af_<q>, mf_<q> in
//                 ar[519:0] {valid, g, beat 6, data 512} in   hf in   hs out
//                 hc[181:0] {dw 68, pw 75, d_start, d_gen 2, d_token 18, d_pos 18} in
//                 tk[92:0] {d_done, gen 2, drained, fault, code 4, coll_busy, kv_write_flush, next_token 18,
//                           next_val 32, cycles 32} out
//                 kst[9:0] {fault, cause 9} out
// qkd_rstseq    the die's reset sequencer (ot_qwen_sys_rst_seq) as its own small M5 leaf beside the PLL hard macro.
//
// OT_QKD_SEQ_MUT (bench only): the parent swaps two store slices on the E copies of the q word.
// OT_QKD_RSTSEQ_MUT (bench only): the quadrant resets follow the die reset instead of the HBM reset.
// ---------------------------------------------------------------------------------------------------------------------
module qkd_seq_core (
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
    wire rr;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr));
    ot_qkvd_seq_m_ctl #(.XS(40), .KD(8), .KWC(4), .OCR_AR(64), .NS(38), .KDESC(1), .KD_PMID(0), .KD_PTOK(0), .MUT(0)) u_body (
        .clk(ck), .rst_n(rr), .x3_v(x3_v), .x3_tag(x3_tag), .x3_cr(x3_cr), .sd(r_sd), .kvd(r_kvd),
        .ar_v(t_ar_d[519]), .ar_d(t_ar_d[518:0]), .ar_cr(t_ar_cr), .ds(t_ds), .pw(t_pw),
        .s_qpop(s_qpop), .s_kpop(s_kpop), .s_kidx(s_kidx), .s_kwgo(s_kwgo),
        .s_kwn(s_kwn), .f_aqm({f_aqm_e, f_aqm_w}), .f_kwm({f_kwm_e, f_kwm_w}), .f_kc({f_kc_e, f_kc_w}), .f_cr({f_cr_e, f_cr_w}),
        .f_af({f_af_e, f_af_w}), .f_mf({f_mf_e, f_mf_w}), .hs(hs),
        .a_out_valid(ar[519]), .a_out_g(ar[518]), .a_out_beat(ar[517:512]), .a_out_data(ar[511:0]), .a_hub_fault(hf),
        .hc(hc), .tk(tk), .fault(kst[9]), .fault_cause(kst[8:0]));
endmodule

module qkd_seq_xs (
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
    wire rr;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr));
    ot_qkvd_seq_m_store #(.DW(128), .XS(40), .KD(8)) u_body (.clk(ck), .rst_n(rr), .x_v(x_v), .x_cls(x_cls), .x_d(x_d),
        .qpop(qpop), .kpop(kpop), .kidx(kidx), .kwgo(kwgo), .kwn(kwn), .q({q_e, q_w}), .kw({kw_e, kw_w}));
endmodule

module qkd_seq_fan (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [27:0]   aqm,
    input  wire [511:0]  q,
    input  wire [22:0]   kwm,
    input  wire [1023:0] kw,
    input  wire [32:0]   kc_i,
    output wire [539:0]  aq,
    output wire [1046:0] kvn,
    output wire [32:0]   kc,
    input  wire          kvn_cr,
    input  wire          af,
    input  wire          mf,
    output wire          cr_o,
    output wire          af_o,
    output wire          mf_o
);
    wire rr;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr));
    ot_qkvd_seq_m_fan #(.HD(128)) u_body (.clk(ck), .rst_n(rr), .aqm(aqm), .q(q), .kwm(kwm), .kw(kw), .kc_i(kc_i),
        .aq(aq), .kvn(kvn), .kc(kc), .kvn_cr(kvn_cr), .af(af), .mf(mf), .cr_o(cr_o), .af_o(af_o), .mf_o(mf_o));
endmodule

// wires-only parent on the contract slot `seq`: no cell, no flop of its own
module qkd_seq (
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
    qkd_seq_core u_core (.ck(ck), .rst_n(rst_n), .x3_v(r_x3_d[523]), .x3_tag(r_x3_d[522:512]), .x3_cr(r_x3_cr), .r_sd(r_sd),
        .r_kvd(r_kvd), .t_ar_d(t_ar_d), .t_ar_cr(t_ar_cr), .t_ds(t_ds), .t_pw(t_pw),
        .s_qpop(s_qpop), .s_kpop(s_kpop), .s_kidx(s_kidx), .s_kwgo(s_kwgo), .s_kwn(s_kwn), .f_aqm_w(f_aqm[0]),
        .f_aqm_e(f_aqm[1]), .f_kwm_w(f_kwm[0]), .f_kwm_e(f_kwm[1]), .f_kc_w(f_kc[0]), .f_kc_e(f_kc[1]), .f_cr_w(f_cr[1:0]),
        .f_cr_e(f_cr[3:2]), .f_af_w(f_af[1:0]), .f_af_e(f_af[3:2]), .f_mf_w(f_mf[1:0]), .f_mf_e(f_mf[3:2]), .hs(hs), .ar(ar), .hf(hf), .hc(hc),
        .tk(tk), .kst(kst));
    genvar s, k;
    generate for (s = 0; s < 4; s = s + 1) begin : g_xs
        qkd_seq_xs u_xs (.ck(ck), .rst_n(rst_n), .x_v(r_x3_d[523]), .x_cls(r_x3_d[522:520]), .x_d(r_x3_d[128*s +: 128]),
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

// ---------------------------------------------------------------------------------------------------------------------
// qkd_rstseq: the die's power-up / reset sequencer beside the PLL hard macro (qkd_pll).  Body = ot_qwen_sys_rst_seq
// (NL = 4 link ends: the three package SerDes ports and the host SerDes; ND = 4: the four quadrant KV services).
// Every status input is captured at its pin (one stage), every output is a flop at its pin (one stage; the reset
// outputs are replicated per consumer and clear asynchronously with the power-on reset):
//   rso_c    die logic reset of the KV centre            = die_rst_n
//   rso_fwd  die logic reset forwarded to the ROM clk_rx = die_rst_n
//   rso_<q>  the quadrant's HBM / KV-service reset       = hbm_rst_n   (boot_go_<q> starts its HBM round-trip check)
//   rso_host host-side reset (first out)                 = host_rst_n
//   rso_link link-layer reset                            = link_rst_n
//   rst_st[41:0] {sys_ready, boot_fault, boot_state 4, boot_err 4, boot_cycles 32} to the host CSRs
// ---------------------------------------------------------------------------------------------------------------------
module qkd_rstseq (
    input  wire         ck,
    input  wire         por_n,
    input  wire         soft_rst,
    input  wire [3:0]   link_up,
    input  wire [3:0]   boot_done,
    input  wire [3:0]   boot_ok,
    (* keep = "true", dont_touch = "true" *) output reg rso_c,
    (* keep = "true", dont_touch = "true" *) output reg rso_fwd,
    (* keep = "true", dont_touch = "true" *) output reg rso_WS,
    (* keep = "true", dont_touch = "true" *) output reg rso_WN,
    (* keep = "true", dont_touch = "true" *) output reg rso_ES,
    (* keep = "true", dont_touch = "true" *) output reg rso_EN,
    output reg          rso_host,
    output reg          rso_link,
    (* keep = "true", dont_touch = "true" *) output reg [3:0] boot_go,
    output reg  [41:0]  rst_st
);
    wire        host_rst_n, link_rst_n, hbm_rst_n, go, die_rst_n, sys_ready, boot_fault;
    wire [3:0]  boot_state, boot_err;
    wire [31:0] boot_cycles;
    reg         sr;
    reg  [3:0]  lu, bd, bk;
    // inputs captured at the pins (the body's own conditioned reset clears them)
    always @(posedge ck or negedge host_rst_n)
        if (!host_rst_n) begin sr <= 1'b0; lu <= 4'd0; bd <= 4'd0; bk <= 4'd0; end
        else begin sr <= soft_rst; lu <= link_up; bd <= boot_done; bk <= boot_ok; end
    ot_qwen_sys_rst_seq #(.NL(4), .ND(4), .T_LINK(20000), .T_HBM(20000), .T_SETTLE(4)) u_body (
        .clk(ck), .por_n(por_n), .soft_rst(sr), .link_up(lu), .boot_done(bd), .boot_ok(bk), .host_rst_n(host_rst_n),
        .link_rst_n(link_rst_n), .hbm_rst_n(hbm_rst_n), .boot_go(go), .die_rst_n(die_rst_n), .sys_ready(sys_ready),
        .boot_fault(boot_fault), .boot_state(boot_state), .boot_err(boot_err), .boot_cycles(boot_cycles));
`ifdef OT_QKD_RSTSEQ_MUT
    wire q_rst = die_rst_n;
`else
    wire q_rst = hbm_rst_n;
`endif
    always @(posedge ck or negedge por_n)
        if (!por_n) begin
            rso_c <= 1'b0; rso_fwd <= 1'b0; rso_WS <= 1'b0; rso_WN <= 1'b0; rso_ES <= 1'b0; rso_EN <= 1'b0;
            rso_host <= 1'b0; rso_link <= 1'b0; boot_go <= 4'd0; rst_st <= 42'd0;
        end else begin
            rso_c <= die_rst_n; rso_fwd <= die_rst_n; rso_WS <= q_rst; rso_WN <= q_rst; rso_ES <= q_rst; rso_EN <= q_rst;
            rso_host <= host_rst_n; rso_link <= link_rst_n; boot_go <= {4{go}};
            rst_st <= {sys_ready, boot_fault, boot_state, boot_err, boot_cycles};
        end
endmodule
