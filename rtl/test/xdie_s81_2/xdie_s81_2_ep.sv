`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// XDIE-S81-2 (2026-10-19): ONE cross-die endpoint of the CURRENT S81 die (G8R2 bind p4m, claude/tok-s81-g8r2-1019
// 0e6b9b710) for tb_xdie_s81_2.  Successor of rtl/test/xdie_s81/xdie_s81_ep.sv (TOKEN-XDIE-S81 / S81-LINKTO gate_g5).
// What is new against gate_g5: the die's lane LEG between the end-slice master and the PHY macro, exactly as die.v of
// bind_p4m_g8r instantiates it on every one of the 8 lk lanes in both directions (lt_lk_* lane -> PHY, lr_lk_* PHY -> lane):
//   hop 0 clock gate (ICGx4 on the source region root, enable = the source region's released reset; LANDING-CONTRACT L3)
//   3 x dsfd_dvrlyh_<W>_<dir>  half-cycle forwarded-clock relay stations (ot_dvrly_st HC 1; W 512 out, 562 in)
//   dsfd_dvland_<W>            landing ring (ot_s81_land D 4) on the receiving region root, strap k = 3 (land_plan p4m E 3)
// The ICG is a standard cell (no RTL): xdie2_icg is its behavioural latch + AND (transparent while CK is low).
// Everything else is the current RTL: ot_s81sl_rstop (G8R2: sid = 2 col + tier), the end-slice lep leaf, the lane tiles
// dsfd_coll_lane_w / _e, ot_pdie_serdes (KP4 RS(544,514) + rate matcher; all 8 lanes SerDes, die straps ch_b 1).
// MU = 1: the multi-user copy A/B endpoint ot_s81sl_lep_mu_ab (MU-S81 kit s81sl_lepmu: MU_EN 1, AB_EN 1, HOST_EN 0) with
// 4 lane tiles, 4 lane legs and 4 PHY macros (pair A = lanes 0/1, pair B = lanes 2/3 = the copy-B static circuit).
// The die's clock regions (slice root, edge root) are one clock here: the landings make the leg latency independent of
// the phase (fixed E), so cycles are the die's; the landing fault (epoch check) is collected into `fault`.
// LEG = 0 removes the leg (gate_g5 form, for the comparison only).
// MU = 2 (XDIE-S81-MU 10-19): the MU release die's endpoints exactly as bind_p4l3_mu (mu3 ceaed19c4 / mu4 bind) instantiates
// them through ot_s81sl_slice_lep_mux: s_0S / s_0N / s_7S = ot_s81sl_lep_mu_a (MU_EN 1, AB_EN 0, HOST_EN 0; kit
// s81sl_lepmua), s_7N = ot_s81sl_lep_mu #(.HOST_EN(1), .AB_EN(0)) (host plane idle here); pair A only (2 lane tiles).
// MU = 1 stays the copy-A/B superset (ot_s81sl_lep_mu_ab at every endpoint, 4 lane tiles; the MAB die has it at s_0S).
// ---------------------------------------------------------------------------------------------------------------------
module xdie2_icg (input wire CLK, input wire ENA, output wire GCLK);
    reg en_l = 1'b0;
    always @(CLK or ENA) if (!CLK) en_l = ENA;     // latch, transparent while CLK is low
    assign GCLK = CLK & en_l;
endmodule

// one lane leg: source region (ck, rs_s) -> 3 half-cycle relays -> landing on the destination region (ck, rs_d)
module xdie2_leg #(parameter integer W = 512, parameter integer K = 3) (
    input  wire         ck,
    input  wire         rs_s,          // source region reset (released synchronously): opens the hop-0 clock gate
    input  wire         rs_r,          // relay station reset (die: the stations' own rs nets)
    input  wire         rs_d,          // destination region reset: landing read epoch
    input  wire [W-1:0] i,
    output wire [W-1:0] o,
    output wire         fault
);
    wire [3:0] fck; wire [W-1:0] r0, r1, r2;
    xdie2_icg u_g (.CLK(ck), .ENA(rs_s), .GCLK(fck[0]));
    generate if (W == 512) begin : g_512
        dsfd_dvrlyh_512_EW st0 (.i(i),  .o(r0), .ck(fck[0]), .ck_o(fck[1]), .rs(rs_r));
        dsfd_dvrlyh_512_EW st1 (.i(r0), .o(r1), .ck(fck[1]), .ck_o(fck[2]), .rs(rs_r));
        dsfd_dvrlyh_512_EW st2 (.i(r1), .o(r2), .ck(fck[2]), .ck_o(fck[3]), .rs(rs_r));
        dsfd_dvland_512 ld (.ck_f(fck[3]), .i(r2), .ck(ck), .rs(rs_d), .k(3'(K)), .o(o), .fault(fault));
    end else begin : g_562
        dsfd_dvrlyh_562_WE st0 (.i(i),  .o(r0), .ck(fck[0]), .ck_o(fck[1]), .rs(rs_r));
        dsfd_dvrlyh_562_WE st1 (.i(r0), .o(r1), .ck(fck[1]), .ck_o(fck[2]), .rs(rs_r));
        dsfd_dvrlyh_562_WE st2 (.i(r1), .o(r2), .ck(fck[2]), .ck_o(fck[3]), .rs(rs_r));
        dsfd_dvland_562 ld (.ck_f(fck[3]), .i(r2), .ck(ck), .rs(rs_d), .k(3'(K)), .o(o), .fault(fault));
    end endgenerate
endmodule

module xdie_s81_2_ep #(
    parameter integer SIDE = 0,        // 0 = W end (outward = W), 1 = E end
    parameter integer HOST = 0,        // 1 = s_7N (host plane present, inputs idle); MU endpoints carry none
    parameter integer MU = 0,          // 1 = ot_s81sl_lep_mu_ab + pair B; 2 = MU-die leaves (lep_mu_a / lep_mu host)
    parameter integer LEG = 1,         // 1 = the die's lane leg (relays + landing) between lane tile and PHY
    parameter integer PLAT_S = 4,
    parameter integer DMUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [3:0]    sid,
    input  wire          ch_b,
    input  wire [1103:0] ri_n,
    output wire [1103:0] ro_n,
    output wire [4*544-1:0] pma_tx,    // lane l at [544 l +: 544]; lanes 2 / 3 only at MU 1
    input  wire [4*544-1:0] pma_rx,
    input  wire [33:0]   mu_c,         // MU: TX tag window command (die: from dsdv_seq_host_mu)
    output wire [31:0]   mu_rt,        // MU: RX tag of the beat on the lep's ri
    output wire [1103:0] lep_ri,       // the lep's ri (bench tag check)
    output wire          fault,
    output wire [3:0]    live
);
    localparam integer NL = (MU == 1) ? 4 : 2;
    // regional resets (die: per-region synchronised trees; one released edge here: E = K + R0 - G with R0 = G)
    reg [1:0] rsy;
    always @(posedge clk or negedge rst_n) if (!rst_n) rsy <= 2'b00; else rsy <= {rsy[0], 1'b1};
    wire rs = rsy[1];
    // ---- end slice ring stop (ot_s81sl_xg u_r): line ports only
    wire [1103:0] lro, lri; wire sf;
    wire [1103:0] r_ri_w = (SIDE == 0) ? lri : ri_n;
    wire [1103:0] r_ri_e = (SIDE == 0) ? ri_n : lri;
    wire [1103:0] r_ro_e, r_ro_w;
    assign lro  = (SIDE == 0) ? r_ro_w : r_ro_e;
    assign ro_n = (SIDE == 0) ? r_ro_e : r_ro_w;
    assign lep_ri = lri;
    ot_s81sl_rstop u_r (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(r_ri_w), .ri_e(r_ri_e), .ro_e(r_ro_e), .ro_w(r_ro_w),
        .vi(276'd0), .vo(), .xf_v(5'd0), .xf_s(5'd0), .xf({5*276{1'b0}}), .nx_wi(), .nx_ei(), .nx_eo(173'd0), .nx_wo(173'd0),
        .g_v(), .g_fam(), .g_idx(), .g_d(), .dl_ev(), .dl_e(), .dl_wv(), .dl_w(), .dl_vv(), .dl_vb(),
        .ci_dir(3'd0), .ci_b(1104'd0), .fault(sf));
    // ---- lanes: lane tile <-> leg <-> PHY
    wire [3:0] lov, lor, liv, lir; wire [553*4-1:0] lod, lid; wire [11:0] lf; wire [3:0] rxv4;
    wire [3:0] lgf;                      // landing faults (lt + lr per lane)
    wire [7:0] lgf2;
    genvar l;
    generate for (l = 0; l < NL; l = l + 1) begin : g_l
        wire [511:0] tx_t, tx_p, rx_p, rx_t; wire [1:0] st_p, st_t; wire [561:0] rin, rout;
        wire [514:0] lrx = {st_t[0], st_t[1], rx_t, rxv4[l]};
        if (SIDE == 0) begin : g_w
            dsfd_coll_lane_w #(.LCR(1)) u_ln (.ck(clk), .rs(rst_n), .chb(ch_b), .rx(lrx), .tx(tx_t), .tf(),
                .lo_v(lov[l]), .lo_r(lor[l]), .lo_d(lod[553*l +: 553]), .li_v(liv[l]), .li_r(lir[l]), .li_d(lid[553*l +: 553]),
                .flt(lf[3*l +: 3]));
        end else begin : g_e
            dsfd_coll_lane_e #(.LCR(1)) u_ln (.ck(clk), .rs(rst_n), .chb(ch_b), .rx(lrx), .tx(tx_t), .tf(),
                .lo_v(lov[l]), .lo_r(lor[l]), .lo_d(lod[553*l +: 553]), .li_v(liv[l]), .li_r(lir[l]), .li_d(lid[553*l +: 553]),
                .flt(lf[3*l +: 3]));
        end
        assign rin = {48'd0, st_p, rx_p};
        if (LEG != 0) begin : g_leg
            xdie2_leg #(.W(512)) u_lt (.ck(clk), .rs_s(rs), .rs_r(rs), .rs_d(rs), .i(tx_t), .o(tx_p), .fault(lgf2[2*l]));
            xdie2_leg #(.W(562)) u_lr (.ck(clk), .rs_s(rs), .rs_r(rs), .rs_d(rs), .i(rin), .o(rout), .fault(lgf2[2*l+1]));
        end else begin : g_noleg
            assign tx_p = tx_t; assign rout = rin; assign lgf2[2*l +: 2] = 2'b00;
        end
        assign rx_t = rout[511:0]; assign st_t = rout[513:512];
        ot_pdie_serdes #(.PMA_LAT(PLAT_S), .DMUT(DMUT)) u_p (.clk(clk), .rst(rst_n), .tx(tx_p), .rx(rx_p), .st(st_p),
            .pma_tx(pma_tx[544*l +: 544]), .pma_tck(), .pma_rx(pma_rx[544*l +: 544]), .pma_rck(clk));
        assign live[l] = st_t[1];
    end
    if (NL == 2) begin : g_nb
        assign pma_tx[4*544-1:2*544] = '0; assign live[3:2] = 2'b00; assign lgf2[7:4] = 4'd0;
        assign lor[3:2] = 2'b00; assign liv[3:2] = 2'b00; assign lid[553*4-1:553*2] = '0; assign lf[11:6] = 6'd0;
    end endgenerate
    assign lgf = {|lgf2[7:6], |lgf2[5:4], |lgf2[3:2], |lgf2[1:0]};
    // ---- link-port leaf
    wire lepf;
    generate if (MU == 2 && HOST != 0) begin : g_muh      // s_7N of the MU die
        wire [1:0] st0 = {g_l[0].st_t[1], g_l[0].st_t[0]}, st1 = {g_l[1].st_t[1], g_l[1].st_t[0]};
        ot_s81sl_lep_mu #(.HOST_EN(1), .AB_EN(0)) u_lep (.clk(clk), .rst_n(rst_n), .ro(lro), .ri(lri),
            .lo0_v(lov[0]), .lo0_r(lor[0]), .lo0_d(lod[0 +: 553]), .lo1_v(lov[1]), .lo1_r(lor[1]), .lo1_d(lod[553 +: 553]),
            .li0_v(liv[0]), .li0_r(lir[0]), .li0_d(lid[0 +: 553]), .li1_v(liv[1]), .li1_r(lir[1]), .li1_d(lid[553 +: 553]),
            .rxv(rxv4[1:0]), .sl_f(sf), .l0_f(lf[2:0]), .l1_f(lf[5:3]), .l0_st(st0), .l1_st(st1),
            .t_host(77'd0), .t_kd(54'd0), .f_host(), .f_lf(), .f_ks(),
            .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(), .ml_wd(), .ml_rv(1'b0), .ml_rd(1104'd0), .ml_f(1'b0),
            .lo2_v(), .lo2_r(1'b0), .lo2_d(), .lo3_v(), .lo3_r(1'b0), .lo3_d(),
            .li2_v(1'b0), .li2_r(), .li2_d(553'd0), .li3_v(1'b0), .li3_r(), .li3_d(553'd0), .rxvb(),
            .l2_f(3'd0), .l3_f(3'd0), .fault(lepf));
        assign rxv4[3:2] = 2'b00;
    end else if (MU == 2) begin : g_mua                  // s_0S / s_0N / s_7S of the MU die
        ot_s81sl_lep_mu_a u_lep (.clk(clk), .rst_n(rst_n), .ro(lro), .ri(lri),
            .lo0_v(lov[0]), .lo0_r(lor[0]), .lo0_d(lod[0 +: 553]), .lo1_v(lov[1]), .lo1_r(lor[1]), .lo1_d(lod[553 +: 553]),
            .li0_v(liv[0]), .li0_r(lir[0]), .li0_d(lid[0 +: 553]), .li1_v(liv[1]), .li1_r(lir[1]), .li1_d(lid[553 +: 553]),
            .rxv(rxv4[1:0]), .sl_f(sf), .l0_f(lf[2:0]), .l1_f(lf[5:3]),
            .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(), .ml_wd(), .ml_rv(1'b0), .ml_rd(1104'd0), .ml_f(1'b0), .fault(lepf));
        assign rxv4[3:2] = 2'b00;
    end else if (MU != 0) begin : g_mu
        ot_s81sl_lep_mu_ab u_lep (.clk(clk), .rst_n(rst_n), .ro(lro), .ri(lri),
            .lo0_v(lov[0]), .lo0_r(lor[0]), .lo0_d(lod[0 +: 553]), .lo1_v(lov[1]), .lo1_r(lor[1]), .lo1_d(lod[553 +: 553]),
            .li0_v(liv[0]), .li0_r(lir[0]), .li0_d(lid[0 +: 553]), .li1_v(liv[1]), .li1_r(lir[1]), .li1_d(lid[553 +: 553]),
            .rxv(rxv4[1:0]), .sl_f(sf), .l0_f(lf[2:0]), .l1_f(lf[5:3]),
            .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(), .ml_wd(), .ml_rv(1'b0), .ml_rd(1104'd0), .ml_f(1'b0),
            .lo2_v(lov[2]), .lo2_r(lor[2]), .lo2_d(lod[1106 +: 553]), .lo3_v(lov[3]), .lo3_r(lor[3]), .lo3_d(lod[1659 +: 553]),
            .li2_v(liv[2]), .li2_r(lir[2]), .li2_d(lid[1106 +: 553]), .li3_v(liv[3]), .li3_r(lir[3]), .li3_d(lid[1659 +: 553]),
            .rxvb(rxv4[3:2]), .l2_f(lf[8:6]), .l3_f(lf[11:9]), .fault(lepf));
    end else if (HOST != 0) begin : g_h
        wire [1:0] st0 = {g_l[0].st_t[1], g_l[0].st_t[0]}, st1 = {g_l[1].st_t[1], g_l[1].st_t[0]};
        ot_s81sl_lep u_lep (.clk(clk), .rst_n(rst_n), .ro(lro), .ri(lri),
            .lo0_v(lov[0]), .lo0_r(lor[0]), .lo0_d(lod[0 +: 553]), .lo1_v(lov[1]), .lo1_r(lor[1]), .lo1_d(lod[553 +: 553]),
            .li0_v(liv[0]), .li0_r(lir[0]), .li0_d(lid[0 +: 553]), .li1_v(liv[1]), .li1_r(lir[1]), .li1_d(lid[553 +: 553]),
            .rxv(rxv4[1:0]), .sl_f(sf), .l0_f(lf[2:0]), .l1_f(lf[5:3]), .l0_st(st0), .l1_st(st1),
            .t_host(77'd0), .t_kd(54'd0), .f_host(), .f_lf(), .f_ks(), .fault(lepf));
        assign mu_rt = 32'd0; assign rxv4[3:2] = 2'b00;
    end else begin : g_nh
        ot_s81sl_lep_nh u_lep (.clk(clk), .rst_n(rst_n), .ro(lro), .ri(lri),
            .lo0_v(lov[0]), .lo0_r(lor[0]), .lo0_d(lod[0 +: 553]), .lo1_v(lov[1]), .lo1_r(lor[1]), .lo1_d(lod[553 +: 553]),
            .li0_v(liv[0]), .li0_r(lir[0]), .li0_d(lid[0 +: 553]), .li1_v(liv[1]), .li1_r(lir[1]), .li1_d(lid[553 +: 553]),
            .rxv(rxv4[1:0]), .sl_f(sf), .l0_f(lf[2:0]), .l1_f(lf[5:3]), .fault(lepf));
        assign mu_rt = 32'd0; assign rxv4[3:2] = 2'b00;
    end endgenerate
    // landing faults are die-level (land_fault[] -> die status); collected here so the bench sees them
    reg lgq;
    always @(posedge clk or negedge rst_n) if (!rst_n) lgq <= 1'b0; else if (|lgf) lgq <= 1'b1;
    assign fault = lepf | lgq;
endmodule

// The off-chip leg (MODELLED, owner 10-14: only PHY analog / cable / switch): one switch crossing per lane direction,
// fixed D-cycle delay of the PMA word; ERR > 0 at run time (+ERRP=n): one flipped pad bit every n cycles (SerDes KP4
// correction path).  EXTRA (+LATE=n on one lane, bench schedule mutant).  Same model as xdie_s81_chan (gate_g5).
module xdie2_chan #(parameter integer W = 544, parameter integer D = 445) (
    input wire clk, input wire [31:0] errp, input wire [31:0] extra, input wire [W-1:0] d, output wire [W-1:0] q
);
    localparam integer N = 1024;                 // ring >= D + any EXTRA
    reg [W-1:0] m [0:N-1];
    reg [9:0] p = 0;
    reg [W-1:0] q_r = 0;
    integer i, ec = 0;
    initial for (i = 0; i < N; i = i + 1) m[i] = 0;
    reg [W-1:0] em;
    wire [9:0] rp = p - 10'(D + extra);           // the slot written D + extra edges ago (read before this edge's write)
    always @(posedge clk) begin
        em = {W{1'b0}};
        if (errp > 0) begin
            ec <= (ec >= errp - 1) ? 0 : ec + 1;
            if (ec == 0) em[(p * 37) % W] = 1'b1;
        end
        q_r <= m[rp] ^ em;                       // written D + extra cycles before q (q registered)
        m[p] <= d;
        p <= p + 1'b1;
    end
    assign q = q_r;
endmodule
