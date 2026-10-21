`timescale 1ns/1ps
// Selected72 actual unhardened MU assembly. Original existing LP transport retained;
// CAP5 normal source has its real 10 clock roots, externally supplied here.
// UNQUALIFIED: long K-domain lane/endpoint connections still owe actual
// relay/landing transport and protocol age alignment. No old parent CLOSED alias.
// Original LP +3 crossings and +2 fault output stages remain unchanged.
// G3 (LEAD-S81-G3 10-21): u_sl = ot_s81sl_slice_c1x_k8_cap5r_lp (capc5r + fixed-depth CAP reset forests, one release edge).
// S81-LINK5 (owner 10-21 06:00, 5th lane pair): s_0N copy-A/B end = ot_s81sl_slice_lepw_mu_72 with u_lep ->
// ot_s81sl_lep_mu_ab (AB_EN 1, HOST_EN 0; kit s81sl_lepmu) and pair B lanes u_ln2 / u_ln3 (same dsfd_coll_lane_w_safe8_ntf
// as u_ln0 / u_ln1, HF-3 CH_BOARD 700, strap ch_b) on new die ports tx2 / tx3 / rx2 / rx3 (die SerDes link_0_4 / link_0_5).
// Pair A = stage NEXT (user 0 + every un-windowed beat), pair B = stage PREV; fixed static circuits, no destination field.
// Same landings, reset forests, u_sl, MU landing as lepw_mu_72; no tied functional port.
module ot_s81sl_slice_lepw_mab_mu_72 #(
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
    input wire ck_L0, ck_L1, ck_L3, ck_L4,
    input wire ck_CAP_RT, ck_CAP_CW, ck_CAP_CE, ck_CAP_RN, ck_CAP_RS
);
    wire  fault__o;   // out_regs: flat driver of fault
    wire [1103:0] lro, lri; wire sf;
    wire l0v, l0r, l1v, l1r, i0v, i0r, i1v, i1r; wire [552:0] l0d, l1d, i0d, i1d; wire [2:0] f0, f1; wire [1:0] rxv;
    wire [514:0] lrx0, lrx1;
    wire l2v, l2r, l3v, l3r, i2v, i2r, i3v, i3r; wire [552:0] l2d, l3d, i2d, i3d; wire [2:0] f2, f3; wire [1:0] rxvb;
    wire [514:0] lrx2, lrx3;
    wire mwv, mrv, mf; wire [1103:0] mwd, mrd;
    assign lrx0 = {rx0[512], rx0[513], rx0[511:0], rxv[0]};
    assign lrx1 = {rx1[512], rx1[513], rx1[511:0], rxv[1]};
    assign lrx2 = {rx2[512], rx2[513], rx2[511:0], rxvb[0]};
    assign lrx3 = {rx3[512], rx3[513], rx3[511:0], rxvb[1]};
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
    wire lpr_c_u_ln0;  ot_pl_pad #(.W(1), .N(0)) u_lprc_u_ln0 (.ck(ck_K), .d(lpr_K), .q(lpr_c_u_ln0));   // t(u_ln0) = 0
    wire lpr_c_u_ln1;  ot_pl_pad #(.W(1), .N(0)) u_lprc_u_ln1 (.ck(ck_K), .d(lpr_K), .q(lpr_c_u_ln1));   // t(u_ln1) = 0
    wire lpr_c_u_ln2;  ot_pl_pad #(.W(1), .N(0)) u_lprc_u_ln2 (.ck(ck_K), .d(lpr_K), .q(lpr_c_u_ln2));   // t(u_ln2) = 0
    wire lpr_c_u_ln3;  ot_pl_pad #(.W(1), .N(0)) u_lprc_u_ln3 (.ck(ck_K), .d(lpr_K), .q(lpr_c_u_ln3));   // t(u_ln3) = 0
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
    dsfd_coll_lane_w_safe8_ntf u_ln0 (.ck(ck_K), .rs(lpr_c_u_ln0), .chb(ch_b), .rx(lrx0), .tx(tx0), .lo_v(l0v), .lo_r(l0r), .lo_d(l0d), .li_v(i0v), .li_r(i0r), .li_d(i0d), .flt(f0));   // region K, t = 0
    dsfd_coll_lane_w_safe8_ntf u_ln1 (.ck(ck_K), .rs(lpr_c_u_ln1), .chb(ch_b), .rx(lrx1), .tx(tx1), .lo_v(l1v), .lo_r(l1r), .lo_d(l1d), .li_v(i1v), .li_r(i1r), .li_d(i1d), .flt(f1));   // region K, t = 0
    dsfd_coll_lane_w_safe8_ntf u_ln2 (.ck(ck_K), .rs(lpr_c_u_ln2), .chb(ch_b), .rx(lrx2), .tx(tx2), .lo_v(l2v), .lo_r(l2r), .lo_d(l2d), .li_v(i2v), .li_r(i2r), .li_d(i2d), .flt(f2));   // region K, t = 0 (pair B)
    dsfd_coll_lane_w_safe8_ntf u_ln3 (.ck(ck_K), .rs(lpr_c_u_ln3), .chb(ch_b), .rx(lrx3), .tx(tx3), .lo_v(l3v), .lo_r(l3r), .lo_d(l3d), .li_v(i3v), .li_r(i3r), .li_d(i3d), .flt(f3));   // region K, t = 0 (pair B)
    ot_s81sl_lep_mu_ab u_lep (.clk(ck_K), .rst_n(lpr_c_u_lep), .ro(lro__l_K), .ri(lri), .lo0_v(l0v), .lo0_r(l0r), .lo0_d(l0d), .lo1_v(l1v), .lo1_r(l1r), .lo1_d(l1d), .li0_v(i0v), .li0_r(i0r), .li0_d(i0d), .li1_v(i1v), .li1_r(i1r), .li1_d(i1d), .rxv(rxv), .sl_f(sf__l_K), .l0_f(f0), .l1_f(f1), .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(mwv), .ml_wd(mwd), .ml_rv(mrv), .ml_rd(mrd), .ml_f(mf),
        .lo2_v(l2v), .lo2_r(l2r), .lo2_d(l2d), .lo3_v(l3v), .lo3_r(l3r), .lo3_d(l3d), .li2_v(i2v), .li2_r(i2r), .li2_d(i2d), .li3_v(i3v), .li3_r(i3r), .li3_d(i3d), .rxvb(rxvb), .l2_f(f2), .l3_f(f3), .fault(fault__o));   // region K, t = 0
    dsdv_mu_land #(.W(1104), .NB(80), .NS(1), .SRAM(1)) u_land (.clk(ck_ML), .rst_n(lpr_c_u_land), .wv(mwv_ml), .wd(mwd_ml), .rc(mu_rc_ml), .rv(mrv_ml), .rd(mrd_ml), .fault(mf_ml)); // region ML
endmodule
