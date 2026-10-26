`timescale 1ns/1ps
`default_nettype none
module ot_hbm_sm_attn_tile #(
    parameter integer SUB = 4,
    parameter integer RPT = 2,
    parameter integer LBS = 2,
    parameter integer LSB = 16,
    parameter integer NC  = 8,
    parameter integer IL  = 8,
    parameter integer TAGW = 16,
    parameter integer XD  = 128,
    parameter integer NBEAT = 13,
    parameter integer TCK = 1,
    parameter integer NMG = 32,             // mask bits per one-hot replica
    parameter integer A1B = 9,              // strap bits of the block-dot field offset (its low 11 - A1B bits are 0)
    parameter integer A2B = 7,              // strap bits of the BF16 field offset
    parameter integer PT4 = 1               // hbm-blocks 2026-10-07 (m3h): a FOURTH pass-through register on the x-write beat
                                            //   and on every row bundle (m3f tile_w: u_bldm -> u_bld2 -44.13 / u_bld -> u_bldm
                                            //   -42.11 / u_rpm -> u_rp2 -27.24, 4-5 levels of wire): +1 per tile hop on both
) (
    input  wire                     clk,
    input wire rst_n,
    input wire [2:0] attn_column,input wire [1:0] attn_rowbase,
    input  wire [RPT*A1B-1:0]       xs_a1,
    input  wire [RPT*5-1:0]         xs_g1,
    input  wire [RPT*A2B-1:0]       xs_a2,
    input  wire [RPT*5-1:0]         xs_g2,
    input  wire [RPT*(6+TAGW+LBS*266+LSB*16+1+$clog2(XD))-1:0] rin,
    input  wire [1+$clog2(XD)+NBEAT+2048-1:0]                  bin,
    output wire [RPT*(6+TAGW+LBS*266+LSB*16+1+$clog2(XD))-1:0] rout,
    output wire [1+$clog2(XD)+NBEAT+2048-1:0]                  bout,
    input  wire [(SUB-RPT)*(2+32+TAGW)-1:0]                    gin,
    output wire [SUB*(2+32+TAGW)-1:0]                          gout
);
    localparam integer SLW = LBS * 266 + LSB * 16;
    localparam integer WSW = SLW;
    localparam integer XW  = $clog2(XD);
    localparam integer CW  = 6 + TAGW;
    localparam integer RBW = CW + WSW + 1 + XW;
    localparam integer BBW = 1 + XW + NBEAT + 2048;
    localparam integer GLW = 2 + 32 + TAGW;
    localparam integer NG  = (LBS * 266 + NMG - 1) / NMG + (LSB * 16 + NMG - 1) / NMG;   // mask groups per leaf
    // el1011-hbm-smh OT_SMH_HIER: the tile as hardened sub-elements (pt_w, pt_e, and per leaf xs + bdc + tcc = 2 tcl + tct);
    // the top keeps the gather launch (u_gov / u_god), the pass-through G1 lanes and the leaf G1 select (leafh).
`ifndef SYNTHESIS
    initial if (RPT != 2 || SUB != 4) $error("OT_SMH_HIER: built for RPT 2, SUB 4");
`endif
    // per-consumer resets: g1 / g2 / go = leaf j's own-row gather relays (at the leaf, mid-tile, at the S-edge gout pins),
    // p1 / p2 / p3 = the pass-through G1 lanes (N edge, mid-tile, S edge), ptw / pte / lh = the hard children
    wire [RPT-1:0] r_g1, r_g2, r_go, r_lh;
    wire r_p1, r_p2, r_p3, r_ptw, r_pte;
`ifdef OT_SMH_RSTPIN
    // el1013-smh-r11 OT_SMH_RSTPIN (SM tile cluster r10 CTS diagnosis B1): the rst_n PORT lands in ONE pin flop on the tile
    // clock and nothing else; a registered tree (ot_hbm_accel_smh_rst_tree, <= ~350 um a stage, uniform depth 5) carries it
    // to the north leaf, the pass-through band and the south leaf, and each band's final copies reset only that band.
    // Leaf 0 is the north leaf, leaf 1 the south leaf (floorplan); the gather relays take the copy of the band they sit in.
    wire rt_gn, rt_lhn, rt_gm, rt_ptw, rt_pte, rt_gs, rt_lhs;
    ot_hbm_accel_smh_rst_tree u_rt (.clk(clk), .rst_n(rst_n), .gn(rt_gn), .lhn(rt_lhn), .gm(rt_gm), .ptw(rt_ptw),
                                    .pte(rt_pte), .gs(rt_gs), .lhs(rt_lhs));
    assign r_g1 = {rt_gs, rt_gn}; assign r_g2 = {rt_gs, rt_gm}; assign r_go = {rt_gs, rt_gs};
    assign r_lh = {rt_lhs, rt_lhn};
    assign r_p1 = rt_gn; assign r_p2 = rt_gm; assign r_p3 = rt_gs; assign r_ptw = rt_ptw; assign r_pte = rt_pte;
`else
    wire [RPT+1:0] rr;
`ifdef OT_SMH_RSTRELAY
    ot_rst_relay #(.REGIONS(RPT + 2)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
`else
    assign rr = {(RPT + 2){rst_n}};
`endif
    assign r_g1 = rr[RPT-1:0]; assign r_g2 = rr[RPT-1:0]; assign r_go = rr[RPT-1:0]; assign r_lh = {RPT{rst_n}};
    assign r_p1 = rr[RPT+1]; assign r_p2 = rr[RPT+1]; assign r_p3 = rr[RPT+1]; assign r_ptw = rst_n; assign r_pte = rst_n;
`endif
    wire [BBW-1:0] bk1_n, bk1_s, bm;
    wire [NBEAT-1:0] ohl1_n, ohl1_s;
    wire [RPT*RBW-1:0] rpm;
    wire [RBW-1:0] rl1_n, rl1_s;
    // el1013-smh-r14 OT_SMH_PINREG (SM tile cluster r13 post-CTS diagnosis, el1011-hbm-smh.log 10-13): the cluster had no
    // boundary register of its own on the row bundles and the x-write beat: rin / bin ports fed pt_w's pins, and pt_w
    // spends 240-530 ps from a pin to its landing flops (every bin bit lands in 3-5 flops: the pass copy and the N / S
    // leaf copies; ETM setup arc -345..+5 ps against a 526 ps insertion), more than the 223 ps receiver share of the
    // die link on all 3,705 bits (post-CTS TT -419 worst / -157 mean at 770 ps).  One register per bit at the tile's
    // own rin / bin pins: port -> flop is the tile's receiver share, flop -> pt_w a full internal cycle.  +1 cycle per
    // tile hop on the row bundles AND the x-write beat (in step: the x-write margin is unchanged); a column's results
    // arrive 1 more cycle per hop, taken by the front's result deskew (ot_hbm_accel_smh_front_s: 5 + PT4 + 1 a hop).
    wire [RPT*RBW-1:0] rin_l;
    wire [BBW-1:0]     bin_l;
`ifdef OT_SMH_PINREG
    genvar pj;
    generate for (pj = 0; pj < RPT; pj = pj + 1) begin : g_pin
        ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_r (.clk(clk), .rst_n(r_ptw),
            .d(rin[pj*RBW +: RBW]), .q(rin_l[pj*RBW +: RBW]));
    end endgenerate
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_pbv (.clk(clk), .rst_n(r_ptw), .en(1'b1), .d(bin[BBW-1]), .q(bin_l[BBW-1]));
    ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_pbd (.clk(clk), .rst_n(r_ptw), .en(1'b1), .d(bin[BBW-2:0]), .q(bin_l[BBW-2:0]));
`else
    assign rin_l = rin;
    assign bin_l = bin;
`endif
`ifdef OT_SMH_COMPACT_PT
    ot_hbm_smh_compact_pt_w
`else
    ot_hbm_accel_smh_pt_w
`endif
`ifndef SYNTHESIS
        #(.TAGW(TAGW), .NBEAT(NBEAT))
`endif
        u_ptw (.clk(clk), .rst_a(r_ptw), .rin(rin_l), .bin(bin_l), .rpm(rpm), .bm(bm), .rl1_n(rl1_n),
        .bk1_n(bk1_n), .ohl1_n(ohl1_n), .rl1_s(rl1_s), .bk1_s(bk1_s), .ohl1_s(ohl1_s));
`ifdef OT_SMH_COMPACT_PT
    ot_hbm_smh_compact_pt_e
`else
    ot_hbm_accel_smh_pt_e
`endif
`ifndef SYNTHESIS
        #(.TAGW(TAGW), .NBEAT(NBEAT))
`endif
        u_pte (.clk(clk), .rst_a(r_pte), .rpm(rpm), .bm(bm), .rout(rout), .bout(bout));
    genvar j, ln;
    generate for (j = 0; j < RPT; j = j + 1) begin : g_lf
        wire gv, gf; wire [31:0] gy; wire [TAGW-1:0] gt;
        ot_hbm_sm_attn_leafh #(.LBS(LBS), .LSB(LSB), .IL(IL), .TAGW(TAGW), .XD(XD), .NBEAT(NBEAT), .TCK(TCK),
                                 .NMG(NMG), .A1B(A1B), .A2B(A2B)) u_lh (
            .clk(clk), .rst_n(r_lh[j]), .attn_column(attn_column), .attn_row(attn_rowbase+2'(j)), .xs_a1(xs_a1[j*A1B +: A1B]), .xs_g1(xs_g1[j*5 +: 5]),
            .xs_a2(xs_a2[j*A2B +: A2B]), .xs_g2(xs_g2[j*5 +: 5]), .rl1(j == 0 ? rl1_n : rl1_s),
            .bk1(j == 0 ? bk1_n : bk1_s), .ohl1(j == 0 ? ohl1_n : ohl1_s), .gv(gv), .gf(gf), .gy(gy), .gt(gt));
        // (physical spec round 3) the hierarchical tile is 1,080 um tall: leaf 0's result travels ~1,000 um to the
        // S-edge gout pins -> two relay registers on EVERY own-row lane of every tile (uniform: the back end's deskew
        // is unchanged; +2 cycles on every result), <= ~360 um of wire per stage
        wire [GLW-1:0] g1, g2;
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_grv1 (.clk(clk), .rst_n(r_g1[j]), .en(1'b1), .d({gv, gf}), .q(g1[GLW-2 +: 2]));
        ot_hbm_accel_smh_kreg #(.W(GLW-2)) u_grd1 (.clk(clk), .rst_n(r_g1[j]), .en(1'b1), .d({gy, gt}), .q(g1[0 +: GLW-2]));
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_grv2 (.clk(clk), .rst_n(r_g2[j]), .en(1'b1), .d(g1[GLW-2 +: 2]), .q(g2[GLW-2 +: 2]));
        ot_hbm_accel_smh_kreg #(.W(GLW-2)) u_grd2 (.clk(clk), .rst_n(r_g2[j]), .en(1'b1), .d(g1[0 +: GLW-2]), .q(g2[0 +: GLW-2]));
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_gov (.clk(clk), .rst_n(r_go[j]), .en(1'b1), .d(g2[GLW-2 +: 2]),
            .q(gout[(RPT-1-j)*GLW + GLW - 2 +: 2]));
        ot_hbm_accel_smh_kreg #(.W(GLW-2)) u_god (.clk(clk), .rst_n(r_go[j]), .en(1'b1), .d(g2[0 +: GLW-2]),
            .q(gout[(RPT-1-j)*GLW +: GLW-2]));
    end
    for (ln = RPT; ln < SUB; ln = ln + 1) begin : g_gl
        wire [GLW-1:0] gm;
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_v (.clk(clk), .rst_n(r_p1), .en(1'b1),
            .d(gin[(ln-RPT)*GLW + GLW - 2 +: 2]), .q(gm[GLW-2 +: 2]));
        ot_hbm_accel_smh_kreg #(.W(GLW-2)) u_d (.clk(clk), .rst_n(r_p1), .en(1'b1),
            .d(gin[(ln-RPT)*GLW +: GLW-2]), .q(gm[0 +: GLW-2]));
        wire [GLW-1:0] gn;                    // (round 5) a third register: 510 um is more than two spans
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_v2 (.clk(clk), .rst_n(r_p2), .en(1'b1),
            .d(gm[GLW-2 +: 2]), .q(gn[GLW-2 +: 2]));
        ot_hbm_accel_smh_kreg #(.W(GLW-2)) u_d2 (.clk(clk), .rst_n(r_p2), .en(1'b1),
            .d(gm[0 +: GLW-2]), .q(gn[0 +: GLW-2]));
        ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_v3 (.clk(clk), .rst_n(r_p3), .en(1'b1),
            .d(gn[GLW-2 +: 2]), .q(gout[ln*GLW + GLW - 2 +: 2]));
        ot_hbm_accel_smh_kreg #(.W(GLW-2)) u_d3 (.clk(clk), .rst_n(r_p3), .en(1'b1),
            .d(gn[0 +: GLW-2]), .q(gout[ln*GLW +: GLW-2]));
    end endgenerate

endmodule
`default_nettype wire
