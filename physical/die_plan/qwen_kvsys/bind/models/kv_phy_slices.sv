`timescale 1ns/1ps
`default_nettype none
// KV-P3b 10-23: plan-slice views of the two KV die PHY abstracts, for the as-built -> plan binder (asbuilt.substitute +
// dissolve).  Off-chip PHYs are modelled (owner 10-14: only PHY/off-chip signals modelled), so the slices are port
// models / blackboxes exactly like the as-built ones; the wrappers only re-partition the ports, they add no logic
// except the SerDes link-up join below.
//
// (1) qkd_hbm3e_phy_pc (32 PCs, one per quadrant as built) -> 8 slices u_s0..u_s7 of 4 PCs each = plan partitions
//     phy_<Q>_0..7 (census_map_v32 "phy_<Q>__s<k>").  Slice k owns PCs 4k..4k+3, clk and rst_n.
// (2) ot_qfd_serdes_112g_x12_phy (host link) -> two x6 halves u_W / u_E = plan partitions sys_SW / sys_SE
//     (plan_v31.fdi_fix: W = flit[521:0], E = flit[1042:522]).  Each half receives tx_v and returns rx_v; the link is
//     up when both halves are up (tx_up = W & E), rx_v = W.rx_v & E.rx_v.  Those two AND gates are the only logic and
//     belong to the host side (map them to hub_Wi).

(* blackbox *)
module qkd_hbm3e_phy_pc4 (
    input  wire         clk,
    input  wire         rst_n,
    output wire [288:0] pi0, output wire [288:0] pi1, output wire [288:0] pi2, output wire [288:0] pi3,
    input  wire [327:0] po0, input  wire [327:0] po1, input  wire [327:0] po2, input  wire [327:0] po3,
    output wire [3:0]   fh0, output wire [3:0]   fh1, output wire [3:0]   fh2, output wire [3:0]   fh3,
    output wire [3:0]   rh0, output wire [3:0]   rh1, output wire [3:0]   rh2, output wire [3:0]   rh3
);
endmodule

(* blackbox *)
module ot_qfd_serdes_112g_x6_phy #(parameter integer W = 522) (
    input  wire         clk,
    input  wire         rst_n,
    output wire         tx_up,
    input  wire         tx_v,
    input  wire [W-1:0] tx_flit,
    output wire         rx_v,
    output wire [W-1:0] rx_flit
);
endmodule

// structural: exactly the ports of the as-built qkd_hbm3e_phy_pc port model (kv_hard_models.sv), so asbuilt.substitute
// maps every port by name; slice k = u_s<k> owns PCs 4k..4k+3
module qkd_hbm3e_phy_pc_s8 (
    input  wire clk,
    input  wire rst_n,
    output wire [288:0] pi0,
    input  wire [327:0] po0,
    output wire [3:0] fh0,
    output wire [3:0] rh0,
    output wire [288:0] pi1,
    input  wire [327:0] po1,
    output wire [3:0] fh1,
    output wire [3:0] rh1,
    output wire [288:0] pi2,
    input  wire [327:0] po2,
    output wire [3:0] fh2,
    output wire [3:0] rh2,
    output wire [288:0] pi3,
    input  wire [327:0] po3,
    output wire [3:0] fh3,
    output wire [3:0] rh3,
    output wire [288:0] pi4,
    input  wire [327:0] po4,
    output wire [3:0] fh4,
    output wire [3:0] rh4,
    output wire [288:0] pi5,
    input  wire [327:0] po5,
    output wire [3:0] fh5,
    output wire [3:0] rh5,
    output wire [288:0] pi6,
    input  wire [327:0] po6,
    output wire [3:0] fh6,
    output wire [3:0] rh6,
    output wire [288:0] pi7,
    input  wire [327:0] po7,
    output wire [3:0] fh7,
    output wire [3:0] rh7,
    output wire [288:0] pi8,
    input  wire [327:0] po8,
    output wire [3:0] fh8,
    output wire [3:0] rh8,
    output wire [288:0] pi9,
    input  wire [327:0] po9,
    output wire [3:0] fh9,
    output wire [3:0] rh9,
    output wire [288:0] pi10,
    input  wire [327:0] po10,
    output wire [3:0] fh10,
    output wire [3:0] rh10,
    output wire [288:0] pi11,
    input  wire [327:0] po11,
    output wire [3:0] fh11,
    output wire [3:0] rh11,
    output wire [288:0] pi12,
    input  wire [327:0] po12,
    output wire [3:0] fh12,
    output wire [3:0] rh12,
    output wire [288:0] pi13,
    input  wire [327:0] po13,
    output wire [3:0] fh13,
    output wire [3:0] rh13,
    output wire [288:0] pi14,
    input  wire [327:0] po14,
    output wire [3:0] fh14,
    output wire [3:0] rh14,
    output wire [288:0] pi15,
    input  wire [327:0] po15,
    output wire [3:0] fh15,
    output wire [3:0] rh15,
    output wire [288:0] pi16,
    input  wire [327:0] po16,
    output wire [3:0] fh16,
    output wire [3:0] rh16,
    output wire [288:0] pi17,
    input  wire [327:0] po17,
    output wire [3:0] fh17,
    output wire [3:0] rh17,
    output wire [288:0] pi18,
    input  wire [327:0] po18,
    output wire [3:0] fh18,
    output wire [3:0] rh18,
    output wire [288:0] pi19,
    input  wire [327:0] po19,
    output wire [3:0] fh19,
    output wire [3:0] rh19,
    output wire [288:0] pi20,
    input  wire [327:0] po20,
    output wire [3:0] fh20,
    output wire [3:0] rh20,
    output wire [288:0] pi21,
    input  wire [327:0] po21,
    output wire [3:0] fh21,
    output wire [3:0] rh21,
    output wire [288:0] pi22,
    input  wire [327:0] po22,
    output wire [3:0] fh22,
    output wire [3:0] rh22,
    output wire [288:0] pi23,
    input  wire [327:0] po23,
    output wire [3:0] fh23,
    output wire [3:0] rh23,
    output wire [288:0] pi24,
    input  wire [327:0] po24,
    output wire [3:0] fh24,
    output wire [3:0] rh24,
    output wire [288:0] pi25,
    input  wire [327:0] po25,
    output wire [3:0] fh25,
    output wire [3:0] rh25,
    output wire [288:0] pi26,
    input  wire [327:0] po26,
    output wire [3:0] fh26,
    output wire [3:0] rh26,
    output wire [288:0] pi27,
    input  wire [327:0] po27,
    output wire [3:0] fh27,
    output wire [3:0] rh27,
    output wire [288:0] pi28,
    input  wire [327:0] po28,
    output wire [3:0] fh28,
    output wire [3:0] rh28,
    output wire [288:0] pi29,
    input  wire [327:0] po29,
    output wire [3:0] fh29,
    output wire [3:0] rh29,
    output wire [288:0] pi30,
    input  wire [327:0] po30,
    output wire [3:0] fh30,
    output wire [3:0] rh30,
    output wire [288:0] pi31,
    input  wire [327:0] po31,
    output wire [3:0] fh31,
    output wire [3:0] rh31
);
    qkd_hbm3e_phy_pc4 u_s0 (.clk(clk), .rst_n(rst_n), .pi0(pi0), .po0(po0), .fh0(fh0), .rh0(rh0), .pi1(pi1), .po1(po1), .fh1(fh1), .rh1(rh1), .pi2(pi2), .po2(po2), .fh2(fh2), .rh2(rh2), .pi3(pi3), .po3(po3), .fh3(fh3), .rh3(rh3));
    qkd_hbm3e_phy_pc4 u_s1 (.clk(clk), .rst_n(rst_n), .pi0(pi4), .po0(po4), .fh0(fh4), .rh0(rh4), .pi1(pi5), .po1(po5), .fh1(fh5), .rh1(rh5), .pi2(pi6), .po2(po6), .fh2(fh6), .rh2(rh6), .pi3(pi7), .po3(po7), .fh3(fh7), .rh3(rh7));
    qkd_hbm3e_phy_pc4 u_s2 (.clk(clk), .rst_n(rst_n), .pi0(pi8), .po0(po8), .fh0(fh8), .rh0(rh8), .pi1(pi9), .po1(po9), .fh1(fh9), .rh1(rh9), .pi2(pi10), .po2(po10), .fh2(fh10), .rh2(rh10), .pi3(pi11), .po3(po11), .fh3(fh11), .rh3(rh11));
    qkd_hbm3e_phy_pc4 u_s3 (.clk(clk), .rst_n(rst_n), .pi0(pi12), .po0(po12), .fh0(fh12), .rh0(rh12), .pi1(pi13), .po1(po13), .fh1(fh13), .rh1(rh13), .pi2(pi14), .po2(po14), .fh2(fh14), .rh2(rh14), .pi3(pi15), .po3(po15), .fh3(fh15), .rh3(rh15));
    qkd_hbm3e_phy_pc4 u_s4 (.clk(clk), .rst_n(rst_n), .pi0(pi16), .po0(po16), .fh0(fh16), .rh0(rh16), .pi1(pi17), .po1(po17), .fh1(fh17), .rh1(rh17), .pi2(pi18), .po2(po18), .fh2(fh18), .rh2(rh18), .pi3(pi19), .po3(po19), .fh3(fh19), .rh3(rh19));
    qkd_hbm3e_phy_pc4 u_s5 (.clk(clk), .rst_n(rst_n), .pi0(pi20), .po0(po20), .fh0(fh20), .rh0(rh20), .pi1(pi21), .po1(po21), .fh1(fh21), .rh1(rh21), .pi2(pi22), .po2(po22), .fh2(fh22), .rh2(rh22), .pi3(pi23), .po3(po23), .fh3(fh23), .rh3(rh23));
    qkd_hbm3e_phy_pc4 u_s6 (.clk(clk), .rst_n(rst_n), .pi0(pi24), .po0(po24), .fh0(fh24), .rh0(rh24), .pi1(pi25), .po1(po25), .fh1(fh25), .rh1(rh25), .pi2(pi26), .po2(po26), .fh2(fh26), .rh2(rh26), .pi3(pi27), .po3(po27), .fh3(fh27), .rh3(rh27));
    qkd_hbm3e_phy_pc4 u_s7 (.clk(clk), .rst_n(rst_n), .pi0(pi28), .po0(po28), .fh0(fh28), .rh0(rh28), .pi1(pi29), .po1(po29), .fh1(fh29), .rh1(rh29), .pi2(pi30), .po2(po30), .fh2(fh30), .rh2(rh30), .pi3(pi31), .po3(po31), .fh3(fh31), .rh3(rh31));
endmodule

module ot_qfd_serdes_112g_x12_phy_s2 (
    input  wire          clk,
    input  wire          rst_n,
    output wire          tx_up,
    input  wire          tx_v,
    input  wire [1042:0] tx_flit,
    output wire          rx_v,
    output wire [1042:0] rx_flit
);
    wire up_w, up_e, rv_w, rv_e;
    ot_qfd_serdes_112g_x6_phy #(.W(522)) u_W (.clk(clk), .rst_n(rst_n), .tx_up(up_w), .tx_v(tx_v),
        .tx_flit(tx_flit[521:0]), .rx_v(rv_w), .rx_flit(rx_flit[521:0]));
    ot_qfd_serdes_112g_x6_phy #(.W(521)) u_E (.clk(clk), .rst_n(rst_n), .tx_up(up_e), .tx_v(tx_v),
        .tx_flit(tx_flit[1042:522]), .rx_v(rv_e), .rx_flit(rx_flit[1042:522]));
    assign tx_up = up_w & up_e;
    assign rx_v  = rv_w & rv_e;
endmodule
`default_nettype wire
