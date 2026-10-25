`timescale 1ns/1ps
// Selected72 actual unhardened MU assembly. Original existing LP transport retained;
// CAP5 normal source has its real 10 clock roots, externally supplied here.
// No old parent CLOSED alias.
// STW-S81-LAND 10-21 (STEWARD-S81 decision): every lane u_ln<i> is its own clock region N<i> (die root ck_N<i>, reset
// leaf u_lpr_N<i> from lpr_root, same DEPTH-3 age as K), and every lep <-> lane net is landed by ot_s81_mu72_lnland
// (two ot_s81_mu72_land, exactly +3 destination edges each way: lo_v/lo_d/li_r/rxv K->N, li_v/li_d/lo_r/flt/st N->K).
// Credit round trips +6 -> lep #(.CRED(12), .DR(12)) with lanes #(.CORE_CRED(12)) (no beat-rate loss: TX 12/14 > the
// 0.764 off-die cap, RX 12/12).  Die ports tx<i>/rx<i> belong to region N<i>.  MUT 5/6/7 = landing mutants (bench).
// Original LP +3 crossings and +2 fault output stages remain unchanged.
// G3 (LEAD-S81-G3 10-21): u_sl = ot_s81sl_slice_c1x_k8_cap5r_lp (capc5r + fixed-depth CAP reset forests, one release edge).
// S81/PORTFIX-FLT 10-25: lane landings = ot_s81_mu72_lnland_nst (no PHY status k_st: it had no consumer in this lep;
// the PHY fault bit reaches the lep fault collector through the lane flt[2] -> the 1-bit `fault` output).
// S81/PORTFIX-DEAD D-MURT (10-25): u_lep = ot_s81sl_lep_mu_a_nrt, no mu_rt port (TP end: no MU tag return lane).
// S81/PORTFIX-DEAD D-CAPEND (10-25): row-end (6-frame) slice: rt 420 b, u_sl = ot_s81sl_slice_c1x_k8_cap5r_lp_e6 (capc5r_e6).
// S81/IDXNET 10-25: s_0S: u_lep = ot_s81sl_lep_mu_a_tpr (+ topk_final step-2 RX from d-1, pair A: tp_o -> s_0N_LP tm); every other cycle unchanged.
module ot_s81sl_slice_lepw_mu_72 #(
    parameter integer MUT = 0
) (
    input wire rst_n,
    input wire [3:0] sid,
    input wire [1103:0] ri_e,
    output wire [1103:0] ro_e,
    input wire [275:0] vi,
    output wire [275:0] vo,
    input wire [1103:0] bi,
    output wire [512:0] bo,
    output wire [4*1104-1:0] xc,
    input wire [6*70-1:0] rt,               // PORTFIX-DEAD D-CAPEND: 6 frames (lanes 6, 7 had none: tied 0 on the as-built die)
    output wire [15:0] ck_line,
    output wire [1:0] ck_v,
    output wire [15:0] ck_xc,
    output wire [7:0] ck_rt,
    input wire ch_b,
    output wire [511:0] tx0,
    output wire [511:0] tx1,
    input wire [513:0] rx0,
    input wire [513:0] rx1,
    input wire [33:0] mu_c,
    input wire [10:0] mu_rc,
    output wire fault,
    input wire ck_S,
    input wire ck_K, ck_ML,
    input wire ck_N0, ck_N1,
    input wire ck_L0, ck_L1, ck_L3, ck_L4,
    input wire ck_CAP_RT, ck_CAP_CW, ck_CAP_CE, ck_CAP_RN, ck_CAP_RS,
    // S81/IDXNET 10-25 (region K, pin flops in u_lep)
    output wire [275:0] tp_o
);
    wire  fault__o;   // out_regs: flat driver of fault
    wire [1103:0] lro, lri; wire sf;
    wire l0v, l0r, l1v, l1r, i0v, i0r, i1v, i1r; wire [552:0] l0d, l1d, i0d, i1d; wire [2:0] f0, f1; wire [1:0] rxv;
    wire [514:0] lrx0, lrx1;
    wire mwv, mrv, mf; wire [1103:0] mwd, mrd;
    wire n0rxk = rxv[0];
    wire n0lv, n0lr, n0iv, n0ir, n0rxv; wire [552:0] n0ld, n0id; wire [2:0] n0f;
    wire n1rxk = rxv[1];
    wire n1lv, n1lr, n1iv, n1ir, n1rxv; wire [552:0] n1ld, n1id; wire [2:0] n1f;
    assign lrx0 = {rx0[512], rx0[513], rx0[511:0], n0rxv};
    assign lrx1 = {rx1[512], rx1[513], rx1[511:0], n1rxv};
    // ---- OUTPUT REGISTER fault: +2 edge(s) in region K (out_regs; port offset +2)
    ot_pl_pad #(.W(1), .N(2)) u_lpo_fault (.ck(ck_K), .d(fault__o), .q(fault));
    // ---- regional reset runs (1-bit plain hops: they define the landing epochs; region S holds the root)
    wire lpr_root;  ot_pl_pad #(.W(1), .N(1)) u_lpr_root (.ck(ck_S), .d(rst_n), .q(lpr_root));
    localparam integer LPR_LEAVES_S = 1+(((((1103) - (0) + 1))+8-1)/8)+(((((1103) - (0) + 1))+8-1)/8)+(((1)+8-1)/8);
    localparam integer LPR_LEAVES_K = 1+(((((1103) - (0) + 1))+8-1)/8)+(((((1103) - (0) + 1))+8-1)/8)+(((1)+8-1)/8);
    wire [LPR_LEAVES_S-1:0] lpr_S_leaves; wire lpr_S = lpr_S_leaves[0];
    ot_pl_land_reset_forest #(.DEPTH(3), .LEAVES(LPR_LEAVES_S), .ROOT_LOADS(2)) u_lpr_S (.ck(ck_S), .d(lpr_root), .q(lpr_S_leaves)); // same reset age; physical reach unproved
    wire [LPR_LEAVES_K-1:0] lpr_K_leaves; wire lpr_K = lpr_K_leaves[0];
    ot_pl_land_reset_forest #(.DEPTH(3), .LEAVES(LPR_LEAVES_K), .ROOT_LOADS(2)) u_lpr_K (.ck(ck_K), .d(lpr_root), .q(lpr_K_leaves)); // same reset age; physical reach unproved
    // ---- LANDING 0: lri K -> S, 1104 b (u_sl.ri_w)
    wire [4*((1103) - (0) + 1)-1:0] lpl_0_bank;  wire [11:0] lpl_0_epo;  wire [4*(((((1103) - (0) + 1))+8-1)/8)-1:0] lpl_0_vld;  wire [1103:0] lri__l_S, lpl_0_o;
    ot_pl_land_vector_reset_kw_w #(.W(((1103) - (0) + 1)), .D(4), .CHUNK_BITS(8)) u_lpl_0_w (.ck(ck_K), .rsi(lpr_K_leaves[(1) +: (((((1103) - (0) + 1))+8-1)/8)]), .i(lri), .bank(lpl_0_bank), .epo(lpl_0_epo), .vld(lpl_0_vld));
    ot_pl_land_vector_reset_r #(.W(((1103) - (0) + 1)), .D(4), .K((MUT == 2) ? 3 : 2), .CHUNK_BITS(8)) u_lpl_0_r (.ck(ck_S), .rsi(lpr_S_leaves[(1) +: (((((1103) - (0) + 1))+8-1)/8)]), .bank(lpl_0_bank), .epo(lpl_0_epo), .vld(lpl_0_vld), .o(lpl_0_o));
    assign lri__l_S = (MUT == 1) ? lri : lpl_0_o;
    // ---- LANDING 1: lro S -> K, 1104 b (u_lep.ro)
    wire [4*((1103) - (0) + 1)-1:0] lpl_1_bank;  wire [11:0] lpl_1_epo;  wire [4*(((((1103) - (0) + 1))+8-1)/8)-1:0] lpl_1_vld;  wire [1103:0] lro__l_K, lpl_1_o;
    ot_pl_land_vector_reset_kw_w #(.W(((1103) - (0) + 1)), .D(4), .CHUNK_BITS(8)) u_lpl_1_w (.ck(ck_S), .rsi(lpr_S_leaves[(1+(((((1103) - (0) + 1))+8-1)/8)) +: (((((1103) - (0) + 1))+8-1)/8)]), .i(lro), .bank(lpl_1_bank), .epo(lpl_1_epo), .vld(lpl_1_vld));
    ot_pl_land_vector_reset_r #(.W(((1103) - (0) + 1)), .D(4), .K(2), .CHUNK_BITS(8)) u_lpl_1_r (.ck(ck_K), .rsi(lpr_K_leaves[(1+(((((1103) - (0) + 1))+8-1)/8)) +: (((((1103) - (0) + 1))+8-1)/8)]), .bank(lpl_1_bank), .epo(lpl_1_epo), .vld(lpl_1_vld), .o(lpl_1_o));
    assign lro__l_K = lpl_1_o;
    // ---- LANDING 2: sf S -> K, 1 b (u_lep.sl_f)
    wire [4*1-1:0] lpl_2_bank;  wire [11:0] lpl_2_epo;  wire [4*(((1)+8-1)/8)-1:0] lpl_2_vld;  wire  sf__l_K, lpl_2_o;
    ot_pl_land_vector_reset_kw_w #(.W(1), .D(4), .CHUNK_BITS(8)) u_lpl_2_w (.ck(ck_S), .rsi(lpr_S_leaves[(1+(((((1103) - (0) + 1))+8-1)/8)+(((((1103) - (0) + 1))+8-1)/8)) +: (((1)+8-1)/8)]), .i(sf), .bank(lpl_2_bank), .epo(lpl_2_epo), .vld(lpl_2_vld));
    ot_pl_land_vector_reset_r #(.W(1), .D(4), .K(2), .CHUNK_BITS(8)) u_lpl_2_r (.ck(ck_K), .rsi(lpr_K_leaves[(1+(((((1103) - (0) + 1))+8-1)/8)+(((((1103) - (0) + 1))+8-1)/8)) +: (((1)+8-1)/8)]), .bank(lpl_2_bank), .epo(lpl_2_epo), .vld(lpl_2_vld), .o(lpl_2_o));
    assign sf__l_K = lpl_2_o;
    wire lpr_c_u_sl;  ot_pl_pad #(.W(1), .N((MUT == 4) ? 1 : 0)) u_lprc_u_sl (.ck(ck_S), .d(lpr_S), .q(lpr_c_u_sl));   // t(u_sl) = 0
    wire [0:0] lpr_N0_v;  ot_pl_land_reset_forest #(.DEPTH(3), .LEAVES(1), .ROOT_LOADS(2)) u_lpr_N0 (.ck(ck_N0), .d(lpr_root), .q(lpr_N0_v));
    wire lpr_c_u_ln0 = lpr_N0_v[0];   // t(u_ln0) = 0, region N0 (same DEPTH-3 age as K)
    wire [0:0] lpr_N1_v;  ot_pl_land_reset_forest #(.DEPTH(3), .LEAVES(1), .ROOT_LOADS(2)) u_lpr_N1 (.ck(ck_N1), .d(lpr_root), .q(lpr_N1_v));
    wire lpr_c_u_ln1 = lpr_N1_v[0];   // t(u_ln1) = 0, region N1 (same DEPTH-3 age as K)
    wire lpr_c_u_lep;  ot_pl_pad #(.W(1), .N(0)) u_lprc_u_lep (.ck(ck_K), .d(lpr_K), .q(lpr_c_u_lep));   // t(u_lep) = 0
    wire [0:0] lpr_ML_v;
    ot_pl_land_reset_forest #(.DEPTH(3),.LEAVES(1),.ROOT_LOADS(2)) u_lpr_ML(
        .ck(ck_ML),.d(lpr_root),.q(lpr_ML_v));
    wire lpr_c_u_land=lpr_ML_v[0];
    // Real endpoint K -> memory ML transport. Every valid shares its data age.
    wire mwv_ml, mrv_ml, mf_ml;
    wire [1103:0] mwd_ml, mrd_ml;
    wire [10:0] mu_rc_ml;
    ot_s81_mu72_land #(.W(1105)) u_ml_wr (.ck_w(ck_K),.ck_r(ck_ML),
        .rs_w(lpr_K),.rs_r(lpr_c_u_land),.i({mwv,mwd}),.o({mwv_ml,mwd_ml}));
    ot_s81_mu72_land #(.W(11)) u_ml_cmd (.ck_w(ck_K),.ck_r(ck_ML),
        .rs_w(lpr_K),.rs_r(lpr_c_u_land),.i(mu_rc),.o(mu_rc_ml));
    ot_s81_mu72_land #(.W(1106)) u_ml_ret (.ck_w(ck_ML),.ck_r(ck_K),
        .rs_w(lpr_c_u_land),.rs_r(lpr_K),.i({mf_ml,mrv_ml,mrd_ml}),.o({mf,mrv,mrd}));
    // ---- children (clock pins -> their region root; reset pins -> their reset run; landed / padded inputs)
    ot_s81sl_slice_c1x_k8_cap5r_lp_e6 #(.DLK0(1), .DLK1(1), .DLK2(4), .DLK3(1), .DLK4(1), .DLF0(0), .DLF1(0), .DLF2(0), .DLF3(0), .DLF4(0)) u_sl (.ck_C(ck_S), .ck_L0(ck_L0), .ck_L1(ck_L1), .ck_L3(ck_L3), .ck_L4(ck_L4),
        .ck_CAP_RT(ck_CAP_RT), .ck_CAP_CW(ck_CAP_CW), .ck_CAP_CE(ck_CAP_CE), .ck_CAP_RN(ck_CAP_RN), .ck_CAP_RS(ck_CAP_RS), .rst_n(lpr_c_u_sl), .sid(sid), .ri_w(lri__l_S), .ri_e(ri_e), .ro_e(ro_e), .ro_w(lro), .vi(vi), .vo(vo), .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc), .ck_rt(ck_rt), .fault(sf));   // region S, t = 0
    ot_s81_mu72_lnland_nst #(.MUT((MUT == 5) ? 1 : (MUT == 7) ? 3 : 0)) u_lnl0 (.ck_k(ck_K), .ck_n(ck_N0), .rs_k(lpr_K), .rs_n(lpr_c_u_ln0),
        .k_lo_v(l0v), .k_lo_d(l0d), .k_lo_r(l0r), .k_li_v(i0v), .k_li_d(i0d), .k_li_r(i0r), .k_rxv(n0rxk), .k_flt(f0),
        .n_lo_v(n0lv), .n_lo_d(n0ld), .n_lo_r(n0lr), .n_li_v(n0iv), .n_li_d(n0id), .n_li_r(n0ir), .n_rxv(n0rxv), .n_flt(n0f));   // K <-> N0, +3 each way
    dsfd_coll_lane_w_safe8_ntf #(.CORE_CRED(12)) u_ln0 (.ck(ck_N0), .rs(lpr_c_u_ln0), .chb(ch_b), .rx(lrx0), .tx(tx0), .lo_v(n0lv), .lo_r(n0lr), .lo_d(n0ld), .li_v(n0iv), .li_r(n0ir), .li_d(n0id), .flt(n0f));   // region N0, t = 0
    ot_s81_mu72_lnland_nst #(.MUT((MUT == 6) ? 2 : 0)) u_lnl1 (.ck_k(ck_K), .ck_n(ck_N1), .rs_k(lpr_K), .rs_n(lpr_c_u_ln1),
        .k_lo_v(l1v), .k_lo_d(l1d), .k_lo_r(l1r), .k_li_v(i1v), .k_li_d(i1d), .k_li_r(i1r), .k_rxv(n1rxk), .k_flt(f1),
        .n_lo_v(n1lv), .n_lo_d(n1ld), .n_lo_r(n1lr), .n_li_v(n1iv), .n_li_d(n1id), .n_li_r(n1ir), .n_rxv(n1rxv), .n_flt(n1f));   // K <-> N1, +3 each way
    dsfd_coll_lane_w_safe8_ntf #(.CORE_CRED(12)) u_ln1 (.ck(ck_N1), .rs(lpr_c_u_ln1), .chb(ch_b), .rx(lrx1), .tx(tx1), .lo_v(n1lv), .lo_r(n1lr), .lo_d(n1ld), .li_v(n1iv), .li_r(n1ir), .li_d(n1id), .flt(n1f));   // region N1, t = 0
    ot_s81sl_lep_mu_a_tpr #(.CRED(12), .DR(12), .RX_SRAM(1), .IN_PIPE(1), .NATIVE32(1)) u_lep (.clk(ck_K), .rst_n(lpr_c_u_lep), .ro(lro__l_K), .ri(lri), .lo0_v(l0v), .lo0_r(l0r), .lo0_d(l0d), .lo1_v(l1v), .lo1_r(l1r), .lo1_d(l1d), .li0_v(i0v), .li0_r(i0r), .li0_d(i0d), .li1_v(i1v), .li1_r(i1r), .li1_d(i1d), .rxv(rxv), .sl_f(sf__l_K), .l0_f(f0), .l1_f(f1), .mu_c(mu_c), .ml_wv(mwv), .ml_wd(mwd), .ml_rv(mrv), .ml_rd(mrd), .ml_f(mf), .fault(fault__o), .tp_o(tp_o));   // region K, t = 0
    dsdv_mu_land #(.W(1104), .NB(80), .NS(1), .SRAM(1)) u_land (.clk(ck_ML), .rst_n(lpr_c_u_land), .wv(mwv_ml), .wd(mwd_ml), .rc(mu_rc_ml), .rv(mrv_ml), .rd(mrd_ml), .fault(mf_ml)); // region ML
endmodule
