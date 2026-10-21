`timescale 1ns/1ps
// =====================================================================================================================
// QW2-VM8P4 10-21 (Q.STA.SLICE.2) VM8 leaf group P4 FLAT parent (wires-only input of tools/landed_parent/lp.py).
// The landed top qfd_dv_s5_vm8r (rtl/qwen_dv/s5/p4/lp/) is generated from this file + tools/landed_parent/specs/qfd_dv_s5_vm8r.json.
// Why: P3 qfd_dv_s5_vm8q (ONE clock root over 1.43 mm) failed post-CTS setup -460/-522 ps SS on ~9.6k endpoints at ep6 (parent
// flop clock arrival 1.2..2.2 ns vs hard-child insertion 333-485 ps; repair inserted 0 buffers = skew).  P4 = landed regions:
// one CTS root per leaf column + S-face regions, every cross-region net a fixed-latency lp landing, regional reset runs.
// Same ports and datapath as P3 (per-leaf kept relay copies, d_out relays, S-face capture registers), except:
//   * no per-leaf reset relays: every leaf rst_n pin is fed by its region's lp reset run (lp delays it by the leaf's offset);
//   * cr_q is captured by ONE 512-b register u_ocr (S-face region fc) instead of two 256-b halves;
//   * no MUT parameter (lp generates the landing / reset mutants).
// =====================================================================================================================
module qfd_dv_s5_vm8rf (

    input  wire            ck,
    input  wire            rst_n,
    input  wire [7:0]      a_re, b_re, c_re,
    input  wire [8*24-1:0] a_addr, b_addr, c_addr,
    output wire [8*32-1:0] a_q, b_q, c_q,
    input  wire [7:0]      cr_re,
    input  wire [8*24-1:0] cr_addr,
    output wire [8*64-1:0] cr_q,
    input  wire            bs_re,
    input  wire [23:0]     bs_addr,
    output wire [255:0]    bs_q,
    input  wire            p_re,
    input  wire [8:0]      p_idx,
    output wire [456:0]    p_q,
    input  wire [7:0]      vm_we,
    input  wire [8*24-1:0] vm_waddr,
    input  wire [8*32-1:0] vm_wdata,
    input  wire            w16_we,
    input  wire [23:0]     w16_addr,
    input  wire [511:0]    w16_data,
    input  wire            w1_we,
    input  wire [23:0]     w1_addr,
    input  wire [31:0]     w1_data,
    input  wire            tw_we,
    input  wire [1:0]      tw_kind,
    input  wire [23:0]     tw_addr,
    input  wire [1023:0]   tw_data,
    output wire            f_va, f_vb, f_vc, f_crl, f_crh, f_bt
);
    // ---- VM tier: per-replica read relay + write copy ----
    wire [1049:0] vwa, vwb, vwc;
    wire [199:0]  rda, rdb, rdc;
    qfd_dv_s5_vm8q_vwr u_vwa (.ck(ck), .d({vm_we, vm_waddr, vm_wdata, w16_we, w16_addr, w16_data, w1_we, w1_addr, w1_data}), .q(vwa));
    qfd_dv_s5_vm8q_vwr u_vwb (.ck(ck), .d({vm_we, vm_waddr, vm_wdata, w16_we, w16_addr, w16_data, w1_we, w1_addr, w1_data}), .q(vwb));
    qfd_dv_s5_vm8q_vwr u_vwc (.ck(ck), .d({vm_we, vm_waddr, vm_wdata, w16_we, w16_addr, w16_data, w1_we, w1_addr, w1_data}), .q(vwc));
    qfd_dv_s5_vm8q_vrd u_rda (.ck(ck), .d({a_re, a_addr}), .q(rda));
    qfd_dv_s5_vm8q_vrd u_rdb (.ck(ck), .d({b_re, b_addr}), .q(rdb));
    qfd_dv_s5_vm8q_vrd u_rdc (.ck(ck), .d({c_re, c_addr}), .q(rdc));
    wire [255:0] qa, qb, qc;
    wire         fa, fb, fc;
    qfd_dv_s8x_vmr u_va (.ck(ck), .rst_n(rst_n), .re(rda[199:192]), .addr(rda[191:0]), .q(qa),
        .vm_we(vwa[1049:1042]), .vm_waddr(vwa[1041:850]), .vm_wdata(vwa[849:594]), .w16_we(vwa[593]),
        .w16_addr(vwa[592:569]), .w16_data(vwa[568:57]), .w1_we(vwa[56]), .w1_addr(vwa[55:32]), .w1_data(vwa[31:0]),
        .fault(fa));
    qfd_dv_s8x_vmr u_vb (.ck(ck), .rst_n(rst_n), .re(rdb[199:192]), .addr(rdb[191:0]), .q(qb),
        .vm_we(vwb[1049:1042]), .vm_waddr(vwb[1041:850]), .vm_wdata(vwb[849:594]), .w16_we(vwb[593]),
        .w16_addr(vwb[592:569]), .w16_data(vwb[568:57]), .w1_we(vwb[56]), .w1_addr(vwb[55:32]), .w1_data(vwb[31:0]),
        .fault(fb));
    qfd_dv_s8x_vmr u_vc (.ck(ck), .rst_n(rst_n), .re(rdc[199:192]), .addr(rdc[191:0]), .q(qc),
        .vm_we(vwc[1049:1042]), .vm_waddr(vwc[1041:850]), .vm_wdata(vwc[849:594]), .w16_we(vwc[593]),
        .w16_addr(vwc[592:569]), .w16_data(vwc[568:57]), .w1_we(vwc[56]), .w1_addr(vwc[55:32]), .w1_data(vwc[31:0]),
        .fault(fc));
    // ---- BTAB ----
    wire [24:0] rbs;
    qfd_dv_s5_vm8q_rly #(.W(25)) u_rbs (.ck(ck), .d({bs_re, bs_addr}), .q(rbs));
    wire [1033:0] twb;
    qfd_dv_s5_vm8q_twb u_twb (.ck(ck), .d({tw_we, tw_kind, tw_addr[8:2], tw_data}), .q(twb));
    wire [255:0] qbs;  wire fbt;
    qfd_dv_s8x_btab u_bt (.ck(ck), .rst_n(rst_n), .bs_re(rbs[24]), .bs_addr(rbs[23:0]), .bs_q(qbs),
        .tw_we(twb[1033]), .tw_kind(twb[1032:1031]), .tw_addr(twb[1030:1024]), .tw_data(twb[1023:0]), .fault(fbt));
    // ---- PROG (no reset pin) ----
    wire [9:0] rpg;
    qfd_dv_s5_vm8q_rly #(.W(10)) u_rpg (.ck(ck), .d({p_re, p_idx}), .q(rpg));
    wire [924:0] twp;
    qfd_dv_s5_vm8q_twp u_twp (.ck(ck), .d({tw_we, tw_kind, tw_addr[7:0], tw_data[456:0], tw_data[968:512]}), .q(twp));
    wire [456:0] qpg;
    qfd_dv_s8x_prog u_pg (.ck(ck), .p_re(rpg[9]), .p_idx(rpg[8:0]), .p_q(qpg),
        .tw_we(twp[924]), .tw_kind(twp[923:922]), .tw_addr(twp[921:914]), .tw_d0(twp[913:457]), .tw_d1(twp[456:0]));
    // ---- CROM halves: per-half read relays (2), per-half table-write chains (2) ----
    wire [538:0] twl1, twl2, twh1, twh2;
    qfd_dv_s5_vm8q_twc u_twl1 (.ck(ck), .d({tw_we, tw_kind, tw_addr, tw_data[991:960],tw_data[927:896],tw_data[863:832],tw_data[799:768],tw_data[735:704],tw_data[671:640],tw_data[607:576],tw_data[543:512],tw_data[479:448],tw_data[415:384],tw_data[351:320],tw_data[287:256],tw_data[223:192],tw_data[159:128],tw_data[95:64],tw_data[31:0]}), .q(twl1));
    qfd_dv_s5_vm8q_twc u_twl2 (.ck(ck), .d(twl1), .q(twl2));
    qfd_dv_s5_vm8q_twc u_twh1 (.ck(ck), .d({tw_we, tw_kind, tw_addr, tw_data[1023:992],tw_data[959:928],tw_data[895:864],tw_data[831:800],tw_data[767:736],tw_data[703:672],tw_data[639:608],tw_data[575:544],tw_data[511:480],tw_data[447:416],tw_data[383:352],tw_data[319:288],tw_data[255:224],tw_data[191:160],tw_data[127:96],tw_data[63:32]}), .q(twh1));
    qfd_dv_s5_vm8q_twc u_twh2 (.ck(ck), .d(twh1), .q(twh2));
    wire [199:0] crl1, crl2, crh1, crh2;
    qfd_dv_s5_vm8q_vrd u_crl1 (.ck(ck), .d({cr_re, cr_addr}), .q(crl1));
    qfd_dv_s5_vm8q_vrd u_crl2 (.ck(ck), .d(crl1), .q(crl2));
    qfd_dv_s5_vm8q_vrd u_crh1 (.ck(ck), .d({cr_re, cr_addr}), .q(crh1));
    qfd_dv_s5_vm8q_vrd u_crh2 (.ck(ck), .d(crh1), .q(crh2));
    wire [255:0] qlo, qhi;  wire fcl, fch;
    qfd_dv_s8x_crh u_cl (.ck(ck), .rst_n(rst_n), .cr_re(crl2[199:192]), .cr_addr(crl2[191:0]), .q(qlo),
        .tw_we(twl2[538]), .tw_kind(twl2[537:536]), .tw_addr(twl2[535:512]), .tw_d(twl2[511:0]), .fault(fcl));
    qfd_dv_s8x_crh u_ch (.ck(ck), .rst_n(rst_n), .cr_re(crh2[199:192]), .cr_addr(crh2[191:0]), .q(qhi),
        .tw_we(twh2[538]), .tw_kind(twh2[537:536]), .tw_addr(twh2[535:512]), .tw_d(twh2[511:0]), .fault(fch));
    // ---- answers: d_out relays (BTAB / PROG 1, CROM 2) in the leaf region, then the S-face capture registers ----
    wire [256:0] rabs, racl, rach;  wire [456:0] qpg1;
    qfd_dv_s5_vm8q_rly #(.W(257), .N(1)) u_rabs (.ck(ck), .d({fbt, qbs}), .q(rabs));
    qfd_dv_s5_vm8q_rly #(.W(457), .N(1)) u_rapg (.ck(ck), .d(qpg), .q(qpg1));
    qfd_dv_s5_vm8q_rly #(.W(257), .N(2)) u_racl (.ck(ck), .d({fcl, qlo}), .q(racl));
    qfd_dv_s5_vm8q_rly #(.W(257), .N(2)) u_rach (.ck(ck), .d({fch, qhi}), .q(rach));
    wire [255:0] qlo2, qhi2;
    assign qlo2 = racl[255:0];
    assign qhi2 = rach[255:0];
    qfd_dv_s5_vm8out #(.W(256)) u_oa (.ck(ck), .d(qa), .q(a_q));
    qfd_dv_s5_vm8out #(.W(256)) u_ob (.ck(ck), .d(qb), .q(b_q));
    qfd_dv_s5_vm8out #(.W(256)) u_oc (.ck(ck), .d(qc), .q(c_q));
    qfd_dv_s5_vm8out #(.W(512)) u_ocr (.ck(ck), .d({qhi2[255:224], qlo2[255:224],qhi2[223:192], qlo2[223:192],qhi2[191:160], qlo2[191:160],qhi2[159:128], qlo2[159:128],qhi2[127:96], qlo2[127:96],qhi2[95:64], qlo2[95:64],qhi2[63:32], qlo2[63:32],qhi2[31:0], qlo2[31:0]}), .q(cr_q));
    qfd_dv_s5_vm8out #(.W(256)) u_obs (.ck(ck), .d(rabs[255:0]), .q(bs_q));
    qfd_dv_s5_vm8out #(.W(457)) u_opg (.ck(ck), .d(qpg1), .q(p_q));
    qfd_dv_s5_vm8out #(.W(1)) u_ofa (.ck(ck), .d(fa), .q(f_va));
    qfd_dv_s5_vm8out #(.W(1)) u_ofb (.ck(ck), .d(fb), .q(f_vb));
    qfd_dv_s5_vm8out #(.W(1)) u_ofc (.ck(ck), .d(fc), .q(f_vc));
    qfd_dv_s5_vm8out #(.W(1)) u_ofcl (.ck(ck), .d(racl[256]), .q(f_crl));
    qfd_dv_s5_vm8out #(.W(1)) u_ofch (.ck(ck), .d(rach[256]), .q(f_crh));
    qfd_dv_s5_vm8out #(.W(1)) u_ofbt (.ck(ck), .d(rabs[256]), .q(f_bt));
endmodule
