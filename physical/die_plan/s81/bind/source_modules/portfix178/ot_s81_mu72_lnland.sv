`timescale 1ns/1ps
// STW-S81-LAND 10-21 (steward STEWARD-S81 decision: L0/L1 lane regions + CRED12): fixed-latency landing of ONE
// lep <-> lane bundle of a MU72 end parent.  The lane tile sits in its own clock region N (die root ck_N<i>, reset
// leaf from lpr_root) instead of sharing ck_K with u_lep (lane insertion ~200 ps later than lep, bundles 480 um..1 mm).
// Every lep <-> lane net crosses through the existing ot_s81_mu72_land (chunk-8 D4/K2 transport, exactly +3
// destination edges, reset on epochs/valid only):
//   K -> N  {li_r credit, rxv, lo_v, lo_d[552:0]}            556 b  +3 edges
//   N -> K  {st[1:0], flt[2:0], lo_r credit, li_v, li_d}      559 b  +3 edges
// Both data directions are credit links (lane ot_link_credit_rx_b64 DEPTH = CORE_CRED / ot_link_credit_tx_rc
// CRED = CORE_CRED; lep CRED / DR): the landing preserves every valid and every credit pulse (fixed latency, no
// drop), it adds +6 edges to each credit round trip.  Round trips TX ~8 -> ~14, RX ~6 -> ~12 edges: the MU72 tops
// therefore pair lep #(.CRED(12), .DR(12)) with lane #(.CORE_CRED(12)) (CRED12 lane view CLOSED E dscoll_lane_e_s12g);
// TX 12/14 = 0.857 beats/cycle > the 0.764 off-die lane cap, RX 12/12 = full rate -> no beat-rate loss.
// st = the PHY lane status {live, fault} of the die rx port, which now enters in region N: landed to the lep (host
// plane f_lf only, s_7N) with the same +3.
// MUT (bench only): 1 = K -> N bundle wired straight across (missing landing edge), 2 = N -> K bundle straight,
// 3 = credit li_r skips the landing (credit pulse 3 edges early vs its contract).
module ot_s81_mu72_lnland #(parameter integer MUT = 0) (
    input  wire         ck_k, ck_n, rs_k, rs_n,
    // K side (u_lep)
    input  wire         k_lo_v,  input  wire [552:0] k_lo_d, output wire k_lo_r,
    output wire         k_li_v,  output wire [552:0] k_li_d, input  wire k_li_r,
    input  wire         k_rxv,   output wire [2:0]   k_flt,  output wire [1:0] k_st,
    // N side (u_ln)
    output wire         n_lo_v,  output wire [552:0] n_lo_d, input  wire n_lo_r,
    input  wire         n_li_v,  input  wire [552:0] n_li_d, output wire n_li_r,
    output wire         n_rxv,   input  wire [2:0]   n_flt,  input  wire [1:0] n_st
);
    wire [555:0] kn_i = {k_li_r, k_rxv, k_lo_v, k_lo_d}, kn_o;
    wire [558:0] nk_i = {n_st, n_flt, n_lo_r, n_li_v, n_li_d}, nk_o;
    ot_s81_mu72_land #(.W(556)) u_kn (.ck_w(ck_k), .ck_r(ck_n), .rs_w(rs_k), .rs_r(rs_n), .i(kn_i), .o(kn_o));
    ot_s81_mu72_land #(.W(559)) u_nk (.ck_w(ck_n), .ck_r(ck_k), .rs_w(rs_n), .rs_r(rs_k), .i(nk_i), .o(nk_o));
    wire [555:0] kn = (MUT == 1) ? kn_i : (MUT == 3) ? {kn_i[555], kn_o[554:0]} : kn_o;
    wire [558:0] nk = (MUT == 2) ? nk_i : nk_o;
    assign {n_li_r, n_rxv, n_lo_v, n_lo_d} = kn;
    assign {k_st, k_flt, k_lo_r, k_li_v, k_li_d} = nk;
endmodule

// S81/PORTFIX-FLT 10-25 (D-FNET, S81 DECISION 4): ot_s81_mu72_lnland_nst = ot_s81_mu72_lnland WITHOUT the PHY lane status
// landing (no n_st in, no k_st out; N -> K bundle 557 b), for the lane ends whose lep has no host plane (s_0N, s_0S,
// s_7S: k_st had no consumer there, an open output of the LP partition).  k_st = {live, fault} of the die rx port is
// pure status for the fault network: its fault bit rx[512] already enters the lane (lane rx[514] -> flt[2], sticky in the
// lep's fault collector via l<i>_f -> the slice's 1-bit `fault`), and live is status.  Same landing, same +3 each way;
// s_7N keeps ot_s81_mu72_lnland (its k_st feeds the host plane f_lf).  MUT as ot_s81_mu72_lnland.
module ot_s81_mu72_lnland_nst #(parameter integer MUT = 0) (
    input  wire         ck_k, ck_n, rs_k, rs_n,
    // K side (u_lep)
    input  wire         k_lo_v,  input  wire [552:0] k_lo_d, output wire k_lo_r,
    output wire         k_li_v,  output wire [552:0] k_li_d, input  wire k_li_r,
    input  wire         k_rxv,   output wire [2:0]   k_flt,
    // N side (u_ln)
    output wire         n_lo_v,  output wire [552:0] n_lo_d, input  wire n_lo_r,
    input  wire         n_li_v,  input  wire [552:0] n_li_d, output wire n_li_r,
    output wire         n_rxv,   input  wire [2:0]   n_flt
);
    wire [555:0] kn_i = {k_li_r, k_rxv, k_lo_v, k_lo_d}, kn_o;
    wire [556:0] nk_i = {n_flt, n_lo_r, n_li_v, n_li_d}, nk_o;
    ot_s81_mu72_land #(.W(556)) u_kn (.ck_w(ck_k), .ck_r(ck_n), .rs_w(rs_k), .rs_r(rs_n), .i(kn_i), .o(kn_o));
    ot_s81_mu72_land #(.W(557)) u_nk (.ck_w(ck_n), .ck_r(ck_k), .rs_w(rs_n), .rs_r(rs_k), .i(nk_i), .o(nk_o));
    wire [555:0] kn = (MUT == 1) ? kn_i : (MUT == 3) ? {kn_i[555], kn_o[554:0]} : kn_o;
    wire [556:0] nk = (MUT == 2) ? nk_i : nk_o;
    assign {n_li_r, n_rxv, n_lo_v, n_lo_d} = kn;
    assign {k_flt, k_lo_r, k_li_v, k_li_d} = nk;
endmodule
