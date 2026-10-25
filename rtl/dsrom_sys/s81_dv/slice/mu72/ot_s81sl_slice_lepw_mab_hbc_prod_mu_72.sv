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
// S81-LINK5B G7 (lead 10-21): u_lep #(.RX_SRAM(1), .IN_PIPE(1), .NATIVE32(1)) = the lepmu t5c/t5d kit params (claude/s81-link5-lepmu-1021
// @64ad9ca55 ot_s81sl_slice_lep.sv); IN_PIPE adds +1 cycle on ro and mu_c.
// S81/H4 10-24: u_lep = ot_s81sl_lep_mu_ab_idx (+ tree frames tl / ca / cb, IDX_EN 1); every other cycle unchanged.
// S81-LINK5 (owner 10-21 06:00, 5th lane pair): s_0N copy-A/B end = ot_s81sl_slice_lepw_mu_72 with u_lep ->
// ot_s81sl_lep_mu_ab (AB_EN 1, HOST_EN 0; kit s81sl_lepmu) and pair B lanes u_ln2 / u_ln3 (same dsfd_coll_lane_w_safe8_ntf
// as u_ln0 / u_ln1, HF-3 CH_BOARD 700, strap ch_b) on new die ports tx2 / tx3 / rx2 / rx3 (die SerDes link_0_4 / link_0_5).
// Pair A = stage NEXT (user 0 + every un-windowed beat), pair B = stage PREV; fixed static circuits, no destination field.
// Same landings, reset forests, u_sl, MU landing as lepw_mu_72; no tied functional port.
module ot_s81sl_slice_lepw_mab_hbc_prod_mu_72 #(
    parameter integer MUT = 0,
    // No production clock book is implied by physical source binding.
    // Enable only with the compiled identity, phase and return-arrival authority.
    parameter integer HBC_ENABLE=0,
    parameter integer HBC_LOCAL_STAGE=255,HBC_LOCAL_RANK=4,HBC_PHASE_BOUND=0,
    parameter [63:0] HBC_CLOCK_RESET_ID=0,
    parameter [47:0] HBC_BOOT_HEADER_EDGE=48'hffffffffffff,HBC_BOOT_COMMIT_EDGE=48'hffffffffffff,
    parameter [47:0] HBC_RETURN_ARRIVAL_DEADLINE=48'hffffffffffff
) (
    input wire [76:0] hb_status_t_host,input wire [53:0] hb_status_t_kd,
    input wire hb_starter_armed,
    output wire [514:0] hb_f_host,output wire [52:0] hb_ks,output wire [2:0] hb_ks_slot,
    output wire [5:0] hb_arm_mask,output wire hb_arm_commit,
    output wire [11:0] hb_fault,output wire [7:0] hb_hbc_fault,output wire [3:0] hb_return_fault,
    output wire hb_ctx_valid,
    input wire rst_n,
    input wire [3:0] sid,
    input wire [1103:0] ri_e,
    output wire [1103:0] ro_e,
    input wire [275:0] vi,
    output wire [275:0] vo,
    input wire [1103:0] bi,
    output wire [512:0] bo,
    output wire [4*1104-1:0] xc,
    input wire [8*70-1:0] rt,
    output wire [15:0] ck_line,
    output wire [1:0] ck_v,
    output wire [15:0] ck_xc,
    output wire [7:0] ck_rt,
    input wire ch_b,
    output wire [511:0] tx0,
    output wire [511:0] tx1,
    input wire [513:0] rx0,
    input wire [513:0] rx1,
    output wire [511:0] tx2,
    output wire [511:0] tx3,
    input wire [513:0] rx2,
    input wire [513:0] rx3,
    input wire [33:0] mu_c,
    input wire [10:0] mu_rc,
    output wire [31:0] mu_rt,
    output wire fault,
    input wire ck_S,
    input wire ck_K, ck_ML,
    input wire ck_N0, ck_N1, ck_N2, ck_N3,
    input wire ck_L0, ck_L1, ck_L3, ck_L4,
    input wire ck_CAP_RT, ck_CAP_CW, ck_CAP_CE, ck_CAP_RN, ck_CAP_RS,
    // S81/H4 10-24 (COORD H4 option A): the bk_sel index rank-tree lanes end at this lep (region K, pin flops in u_lep):
    // tl <- bk_sel tl_o (plan lane tl__bk_sel__s_0N_LP), ca / cb -> bk_sel ca / cb (ca__ / cb__s_0N_LP__bk_sel)
    input wire [275:0] tl,
    output wire [275:0] ca,
    output wire [275:0] cb
);
    wire  fault__o;   // out_regs: flat driver of fault
    wire [1103:0] lro, lri, lri_ep, lro_ep; wire sf;
    wire l0v, l0r, l1v, l1r, i0v, i0r, i1v, i1r; wire [552:0] l0d, l1d, i0d, i1d; wire [2:0] f0, f1; wire [1:0] rxv;
    wire [514:0] lrx0, lrx1;
    wire l2v, l2r, l3v, l3r, i2v, i2r, i3v, i3r; wire [552:0] l2d, l3d, i2d, i3d; wire [2:0] f2, f3; wire [1:0] rxvb;
    wire [514:0] lrx2, lrx3;
    wire mwv, mrv, mf; wire [1103:0] mwd, mrd;
    wire n0rxk = rxv[0];
    wire n0lv, n0lr, n0iv, n0ir, n0rxv; wire [552:0] n0ld, n0id; wire [2:0] n0f; wire [1:0] n0stk;
    wire n1rxk = rxv[1];
    wire n1lv, n1lr, n1iv, n1ir, n1rxv; wire [552:0] n1ld, n1id; wire [2:0] n1f; wire [1:0] n1stk;
    wire n2rxk = rxvb[0];
    wire n2lv, n2lr, n2iv, n2ir, n2rxv; wire [552:0] n2ld, n2id; wire [2:0] n2f; wire [1:0] n2stk;
    wire n3rxk = rxvb[1];
    wire n3lv, n3lr, n3iv, n3ir, n3rxv; wire [552:0] n3ld, n3id; wire [2:0] n3f; wire [1:0] n3stk;
    assign lrx0 = {rx0[512], rx0[513], rx0[511:0], n0rxv};
    assign lrx1 = {rx1[512], rx1[513], rx1[511:0], n1rxv};
    assign lrx2 = {rx2[512], rx2[513], rx2[511:0], n2rxv};
    assign lrx3 = {rx3[512], rx3[513], rx3[511:0], n3rxv};
    // ---- OUTPUT REGISTER fault: +2 edge(s) in region K (out_regs; port offset +2)
    ot_pl_pad #(.W(1), .N(2)) u_lpo_fault (.ck(ck_K), .d(fault__o), .q(fault));
    // ---- regional reset runs (1-bit plain hops: they define the landing epochs; region S holds the root)
    wire lpr_root;  ot_pl_pad #(.W(1), .N(1)) u_lpr_root (.ck(ck_S), .d(rst_n), .q(lpr_root));
    localparam integer LPR_LEAVES_S = 1+(((((1103) - (0) + 1))+8-1)/8)+(((((1103) - (0) + 1))+8-1)/8)+(((1)+8-1)/8);
    localparam integer LPR_LEAVES_K = 2+(((((1103) - (0) + 1))+8-1)/8)+(((((1103) - (0) + 1))+8-1)/8)+(((1)+8-1)/8);
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
    wire [0:0] lpr_N2_v;  ot_pl_land_reset_forest #(.DEPTH(3), .LEAVES(1), .ROOT_LOADS(2)) u_lpr_N2 (.ck(ck_N2), .d(lpr_root), .q(lpr_N2_v));
    wire lpr_c_u_ln2 = lpr_N2_v[0];   // t(u_ln2) = 0, region N2 (same DEPTH-3 age as K)
    wire [0:0] lpr_N3_v;  ot_pl_land_reset_forest #(.DEPTH(3), .LEAVES(1), .ROOT_LOADS(2)) u_lpr_N3 (.ck(ck_N3), .d(lpr_root), .q(lpr_N3_v));
    wire lpr_c_u_ln3 = lpr_N3_v[0];   // t(u_ln3) = 0, region N3 (same DEPTH-3 age as K)
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
    ot_s81sl_slice_c1x_k8_cap5r_lp #(.DLK0(1), .DLK1(1), .DLK2(4), .DLK3(1), .DLK4(1), .DLF0(0), .DLF1(0), .DLF2(0), .DLF3(0), .DLF4(0)) u_sl (.ck_C(ck_S), .ck_L0(ck_L0), .ck_L1(ck_L1), .ck_L3(ck_L3), .ck_L4(ck_L4),
        .ck_CAP_RT(ck_CAP_RT), .ck_CAP_CW(ck_CAP_CW), .ck_CAP_CE(ck_CAP_CE), .ck_CAP_RN(ck_CAP_RN), .ck_CAP_RS(ck_CAP_RS), .rst_n(lpr_c_u_sl), .sid(sid), .ri_w(lri__l_S), .ri_e(ri_e), .ro_e(ro_e), .ro_w(lro), .vi(vi), .vo(vo), .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc), .ck_rt(ck_rt), .fault(sf));   // region S, t = 0
    ot_s81_mu72_lnland #(.MUT((MUT == 5) ? 1 : (MUT == 7) ? 3 : 0)) u_lnl0 (.ck_k(ck_K), .ck_n(ck_N0), .rs_k(lpr_K), .rs_n(lpr_c_u_ln0),
        .k_lo_v(l0v), .k_lo_d(l0d), .k_lo_r(l0r), .k_li_v(i0v), .k_li_d(i0d), .k_li_r(i0r), .k_rxv(n0rxk), .k_flt(f0), .k_st(n0stk),
        .n_lo_v(n0lv), .n_lo_d(n0ld), .n_lo_r(n0lr), .n_li_v(n0iv), .n_li_d(n0id), .n_li_r(n0ir), .n_rxv(n0rxv), .n_flt(n0f), .n_st(rx0[513:512]));   // K <-> N0, +3 each way
    dsfd_coll_lane_w_safe8_ntf #(.CORE_CRED(12)) u_ln0 (.ck(ck_N0), .rs(lpr_c_u_ln0), .chb(ch_b), .rx(lrx0), .tx(tx0), .lo_v(n0lv), .lo_r(n0lr), .lo_d(n0ld), .li_v(n0iv), .li_r(n0ir), .li_d(n0id), .flt(n0f));   // region N0, t = 0
    ot_s81_mu72_lnland #(.MUT((MUT == 6) ? 2 : 0)) u_lnl1 (.ck_k(ck_K), .ck_n(ck_N1), .rs_k(lpr_K), .rs_n(lpr_c_u_ln1),
        .k_lo_v(l1v), .k_lo_d(l1d), .k_lo_r(l1r), .k_li_v(i1v), .k_li_d(i1d), .k_li_r(i1r), .k_rxv(n1rxk), .k_flt(f1), .k_st(n1stk),
        .n_lo_v(n1lv), .n_lo_d(n1ld), .n_lo_r(n1lr), .n_li_v(n1iv), .n_li_d(n1id), .n_li_r(n1ir), .n_rxv(n1rxv), .n_flt(n1f), .n_st(rx1[513:512]));   // K <-> N1, +3 each way
    dsfd_coll_lane_w_safe8_ntf #(.CORE_CRED(12)) u_ln1 (.ck(ck_N1), .rs(lpr_c_u_ln1), .chb(ch_b), .rx(lrx1), .tx(tx1), .lo_v(n1lv), .lo_r(n1lr), .lo_d(n1ld), .li_v(n1iv), .li_r(n1ir), .li_d(n1id), .flt(n1f));   // region N1, t = 0
    ot_s81_mu72_lnland #(.MUT(0)) u_lnl2 (.ck_k(ck_K), .ck_n(ck_N2), .rs_k(lpr_K), .rs_n(lpr_c_u_ln2),
        .k_lo_v(l2v), .k_lo_d(l2d), .k_lo_r(l2r), .k_li_v(i2v), .k_li_d(i2d), .k_li_r(i2r), .k_rxv(n2rxk), .k_flt(f2), .k_st(n2stk),
        .n_lo_v(n2lv), .n_lo_d(n2ld), .n_lo_r(n2lr), .n_li_v(n2iv), .n_li_d(n2id), .n_li_r(n2ir), .n_rxv(n2rxv), .n_flt(n2f), .n_st(rx2[513:512]));   // K <-> N2, +3 each way
    dsfd_coll_lane_w_safe8_ntf #(.CORE_CRED(12)) u_ln2 (.ck(ck_N2), .rs(lpr_c_u_ln2), .chb(ch_b), .rx(lrx2), .tx(tx2), .lo_v(n2lv), .lo_r(n2lr), .lo_d(n2ld), .li_v(n2iv), .li_r(n2ir), .li_d(n2id), .flt(n2f));   // region N2, t = 0
    ot_s81_mu72_lnland #(.MUT(0)) u_lnl3 (.ck_k(ck_K), .ck_n(ck_N3), .rs_k(lpr_K), .rs_n(lpr_c_u_ln3),
        .k_lo_v(l3v), .k_lo_d(l3d), .k_lo_r(l3r), .k_li_v(i3v), .k_li_d(i3d), .k_li_r(i3r), .k_rxv(n3rxk), .k_flt(f3), .k_st(n3stk),
        .n_lo_v(n3lv), .n_lo_d(n3ld), .n_lo_r(n3lr), .n_li_v(n3iv), .n_li_d(n3id), .n_li_r(n3ir), .n_rxv(n3rxv), .n_flt(n3f), .n_st(rx3[513:512]));   // K <-> N3, +3 each way
    dsfd_coll_lane_w_safe8_ntf #(.CORE_CRED(12)) u_ln3 (.ck(ck_N3), .rs(lpr_c_u_ln3), .chb(ch_b), .rx(lrx3), .tx(tx3), .lo_v(n3lv), .lo_r(n3lr), .lo_d(n3ld), .li_v(n3iv), .li_r(n3ir), .li_d(n3id), .flt(n3f));   // region N3, t = 0
    ot_s81sl_lep_mu_ab_idx #(.CRED(12), .DR(12), .RX_SRAM(1), .IN_PIPE(1), .NATIVE32(1)) u_lep (.clk(ck_K), .rst_n(lpr_c_u_lep), .ro(lro_ep), .ri(lri_ep), .lo0_v(l0v), .lo0_r(l0r), .lo0_d(l0d), .lo1_v(l1v), .lo1_r(l1r), .lo1_d(l1d), .li0_v(i0v), .li0_r(i0r), .li0_d(i0d), .li1_v(i1v), .li1_r(i1r), .li1_d(i1d), .rxv(rxv), .sl_f(sf__l_K), .l0_f(f0), .l1_f(f1), .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(mwv), .ml_wd(mwd), .ml_rv(mrv), .ml_rd(mrd), .ml_f(mf),
        .lo2_v(l2v), .lo2_r(l2r), .lo2_d(l2d), .lo3_v(l3v), .lo3_r(l3r), .lo3_d(l3d), .li2_v(i2v), .li2_r(i2r), .li2_d(i2d), .li3_v(i3v), .li3_r(i3r), .li3_d(i3d), .rxvb(rxvb), .l2_f(f2), .l3_f(f3), .fault(fault__o), .tl(tl), .ca(ca), .cb(cb));   // region K, t = 0 (S81/H4: + tree ports)
    // Production HBC receiver remains inside the existing K region; only the
    // real host/KS outputs and booked sequencer status cross the die boundary.
    // The unused external-return arm of RETURN_LOCAL=1 reads actual local_ro;
    // the selected return emitter exclusively captures the real landed status.
    wire [47:0] hb_receiver_edge,hb_boot_edge;
    dsdv_hostb_stage_hbc #(.ENABLE(HBC_ENABLE),.LOCAL_STAGE(HBC_LOCAL_STAGE),.LOCAL_RANK(HBC_LOCAL_RANK),
      .PHASE_BOUND(HBC_PHASE_BOUND),.CLOCK_RESET_ID(HBC_CLOCK_RESET_ID),
      .BOOT_HEADER_EDGE(HBC_BOOT_HEADER_EDGE),.BOOT_COMMIT_EDGE(HBC_BOOT_COMMIT_EDGE),
      .VARIABLE_WORDS(1),.ALLOW_RELOAD(1),.RETURN_LOCAL(1),.RETURN_REQUIRE_KIT(1),.RETURN_ARRIVAL_DEADLINE(HBC_RETURN_ARRIVAL_DEADLINE)) u_hbc(
      .ck(ck_K),.rst_n(lpr_K_leaves[LPR_LEAVES_K-1]),.job_active(hb_status_t_host[65]),.starter_armed(hb_starter_armed),
      .from_prev(lri_ep),.local_ro(lro__l_K),.return_ro(lro__l_K),
      .status_t_host(hb_status_t_host),.status_t_kd(hb_status_t_kd),.return_fault(hb_return_fault),
      .to_local(lri),.next_ro(lro_ep),.f_host(hb_f_host),.ks_descriptor(hb_ks),.ks_slot(hb_ks_slot),
      .arm_mask(hb_arm_mask),.arm_commit(hb_arm_commit),.fault(hb_fault),.context_valid(hb_ctx_valid),
      .receiver_edge(hb_receiver_edge),.boot_edge(hb_boot_edge),.hbc_fault(hb_hbc_fault));
    dsdv_mu_land #(.W(1104), .NB(80), .NS(1), .SRAM(1)) u_land (.clk(ck_ML), .rst_n(lpr_c_u_land), .wv(mwv_ml), .wd(mwd_ml), .rc(mu_rc_ml), .rv(mrv_ml), .rd(mrd_ml), .fault(mf_ml)); // region ML
endmodule
