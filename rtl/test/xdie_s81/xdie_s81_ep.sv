`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// TOKEN-XDIE-S81 (2026-10-18): ONE cross-die endpoint of an S81 p4l die, for the multi-die collective co-sim
// tb_xdie_s81.  Every module below is the current p4l RTL (claude/s81-die7-1018): only the PMA analog, the cable and the
// switch are outside this wrapper (they are the bench channel model).
//
// Default (EP mode): the on-path sub-modules of the end-slice die master, wired exactly as ot_s81sl_slice_lep wires them:
//   ot_s81sl_rstop       the end slice's ring stop (the only slice sub-leaf on the line path: line in -> line out
//                        2 edges; in ot_s81sl_slice the line ports reach ot_s81sl_xg's rstop with no glue)
//   ot_s81sl_lep / _nh   link-port leaf (TX landing SRAM, pair re-assembly, credit faces, fault collector)
//   dsfd_coll_lane_w/_e  x 2 hardened lane tiles (ot_s81ph_link_ep reliable link layer + ot_s81ph_link_gbx), LCR = 1
//   ot_pdie_ucie / ot_pdie_serdes  PHY digital per the p4l plan lane (serdes = KP4 RS(544,514) enc/dec + rate matcher)
// Off-path parts of the slice (beat leaves, xr, cap, xfin, eg, x streamer) do not touch a forwarded line beat; MASTER
// mode (+define+XDIE_MASTER) instantiates the full die masters ot_s81sl_slice_lepw / _lepe / _lepe_nh instead (slow:
// full slice clusters) to confirm the EP-mode cycles.
// Ports: ri_n / ro_n = the end slice's INWARD line port (die interior side): the co-sim boundary of the die run.
//        pma_* = the PHY macro pads (behavioural PMA inside the PHY macro, LAT cycles each way).
// LOVR = 1 (what-if, NOT the built RTL): the lane tile is ot_s81ph_coll_lane with CH_BOARD / CREDITS / SEQW overridden
//        (link layer sized for a switched crossing; SRAM 0 = flop arrays of the same cycle behaviour above 512 deep).
// ---------------------------------------------------------------------------------------------------------------------
module xdie_s81_ep #(
    parameter integer SIDE = 0,        // 0 = W end (outward = W), 1 = E end
    parameter integer HOST = 0,        // 1 = s_7N master (host plane present, inputs idle)
    parameter integer PHY0 = 1,        // lane 0 PHY: 0 = ot_pdie_ucie, 1 = ot_pdie_serdes
    parameter integer PHY1 = 1,        // lane 1 PHY
    parameter integer PLAT_S = 4,      // PMA model latency inside ot_pdie_serdes (its default)
    parameter integer PLAT_U = 2,      // PMA model latency inside ot_pdie_ucie (its default)
    parameter integer DMUT = 0,        // ot_pdie_serdes KP4 decoder mutant (bench only)
    parameter integer LOVR = 0,
    parameter integer CHB_OVR = 400, parameter integer CRED_OVR = 512, parameter integer SEQW_OVR = 10,
    parameter integer LSRAM = 1
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [3:0]    sid,
    input  wire          ch_b,
    input  wire [1103:0] ri_n,
    output wire [1103:0] ro_n,
    output wire [543:0]  pma_tx0, output wire [543:0] pma_tx1,
    input  wire [543:0]  pma_rx0, input  wire [543:0] pma_rx1,
    output wire          fault,
    output wire [1:0]    live
);
    wire [511:0] tx0, tx1, rx0, rx1; wire [1:0] st0, st1;
    assign live = {st1[1], st0[1]};
`ifdef XDIE_MASTER
    generate if (SIDE == 0) begin : g_mw
        ot_s81sl_slice_lepw u_m (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_e(ri_n), .ro_e(ro_n), .vi(276'd0), .vo(), .bi(1104'd0),
            .bo(), .xc(), .rt(560'd0), .ck_line(), .ck_v(), .ck_xc(), .ck_rt(), .ch_b(ch_b), .tx0(tx0), .tx1(tx1),
            .rx0({st0, rx0}), .rx1({st1, rx1}), .tf(), .fault(fault));
    end else if (HOST != 0) begin : g_meh
        ot_s81sl_slice_lepe u_m (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(ri_n), .ro_w(ro_n), .vi(276'd0), .vo(), .bi(1104'd0),
            .bo(), .xc(), .rt(560'd0), .ck_line(), .ck_v(), .ck_xc(), .ck_rt(), .ch_b(ch_b), .tx0(tx0), .tx1(tx1),
            .rx0({st0, rx0}), .rx1({st1, rx1}), .tf(), .t_host(77'd0), .t_kd(54'd0), .f_host(), .f_lf(), .f_ks(), .fault(fault));
    end else begin : g_men
        ot_s81sl_slice_lepe_nh u_m (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(ri_n), .ro_w(ro_n), .vi(276'd0), .vo(), .bi(1104'd0),
            .bo(), .xc(), .rt(560'd0), .ck_line(), .ck_v(), .ck_xc(), .ck_rt(), .ch_b(ch_b), .tx0(tx0), .tx1(tx1),
            .rx0({st0, rx0}), .rx1({st1, rx1}), .tf(), .fault(fault));
    end endgenerate
`else
    // ---- end slice ring stop (ot_s81sl_xg u_r): line ports only; V rung, own beats, xfin and control-plane inject idle
    wire [1103:0] lro, lri; wire sf;
    wire [1103:0] r_ri_w = (SIDE == 0) ? lri : ri_n;
    wire [1103:0] r_ri_e = (SIDE == 0) ? ri_n : lri;
    wire [1103:0] r_ro_e, r_ro_w;
    assign lro  = (SIDE == 0) ? r_ro_w : r_ro_e;
    assign ro_n = (SIDE == 0) ? r_ro_e : r_ro_w;
    ot_s81sl_rstop u_r (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(r_ri_w), .ri_e(r_ri_e), .ro_e(r_ro_e), .ro_w(r_ro_w),
        .vi(276'd0), .vo(), .xf_v(5'd0), .xf_s(5'd0), .xf({5*276{1'b0}}), .nx_wi(), .nx_ei(), .nx_eo(173'd0), .nx_wo(173'd0),
        .g_v(), .g_fam(), .g_idx(), .g_d(), .dl_ev(), .dl_e(), .dl_wv(), .dl_w(), .dl_vv(), .dl_vb(),
        .ci_dir(3'd0), .ci_b(1104'd0), .fault(sf));
    // ---- link lanes
    wire l0v, l0r, l1v, l1r, i0v, i0r, i1v, i1r; wire [552:0] l0d, l1d, i0d, i1d; wire [2:0] f0, f1; wire [1:0] rxv;
    wire [514:0] lrx0 = {st0[0], st0[1], rx0, rxv[0]};
    wire [514:0] lrx1 = {st1[0], st1[1], rx1, rxv[1]};
    generate if (LOVR != 0) begin : g_lo
        ot_s81ph_coll_lane #(.LCR(1), .CH_BOARD(CHB_OVR), .CREDITS(CRED_OVR), .SEQW(SEQW_OVR), .SRAM(LSRAM)) u_ln0 (.clk(clk), .rs_n(rst_n),
            .ch_b(ch_b), .rx(lrx0), .tx(tx0), .tf(), .lo_v(l0v), .lo_r(l0r), .lo_d(l0d), .li_v(i0v), .li_r(i0r), .li_d(i0d), .flt(f0));
        ot_s81ph_coll_lane #(.LCR(1), .CH_BOARD(CHB_OVR), .CREDITS(CRED_OVR), .SEQW(SEQW_OVR), .SRAM(LSRAM)) u_ln1 (.clk(clk), .rs_n(rst_n),
            .ch_b(ch_b), .rx(lrx1), .tx(tx1), .tf(), .lo_v(l1v), .lo_r(l1r), .lo_d(l1d), .li_v(i1v), .li_r(i1r), .li_d(i1d), .flt(f1));
    end else if (SIDE == 0) begin : g_lw
        dsfd_coll_lane_w #(.LCR(1)) u_ln0 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx(lrx0), .tx(tx0), .tf(),
            .lo_v(l0v), .lo_r(l0r), .lo_d(l0d), .li_v(i0v), .li_r(i0r), .li_d(i0d), .flt(f0));
        dsfd_coll_lane_w #(.LCR(1)) u_ln1 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx(lrx1), .tx(tx1), .tf(),
            .lo_v(l1v), .lo_r(l1r), .lo_d(l1d), .li_v(i1v), .li_r(i1r), .li_d(i1d), .flt(f1));
    end else begin : g_le
        dsfd_coll_lane_e #(.LCR(1)) u_ln0 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx(lrx0), .tx(tx0), .tf(),
            .lo_v(l0v), .lo_r(l0r), .lo_d(l0d), .li_v(i0v), .li_r(i0r), .li_d(i0d), .flt(f0));
        dsfd_coll_lane_e #(.LCR(1)) u_ln1 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx(lrx1), .tx(tx1), .tf(),
            .lo_v(l1v), .lo_r(l1r), .lo_d(l1d), .li_v(i1v), .li_r(i1r), .li_d(i1d), .flt(f1));
    end endgenerate
    generate if (HOST != 0) begin : g_h
        ot_s81sl_lep u_lep (.clk(clk), .rst_n(rst_n), .ro(lro), .ri(lri),
            .lo0_v(l0v), .lo0_r(l0r), .lo0_d(l0d), .lo1_v(l1v), .lo1_r(l1r), .lo1_d(l1d),
            .li0_v(i0v), .li0_r(i0r), .li0_d(i0d), .li1_v(i1v), .li1_r(i1r), .li1_d(i1d), .rxv(rxv),
            .sl_f(sf), .l0_f(f0), .l1_f(f1), .l0_st(st0), .l1_st(st1),
            .t_host(77'd0), .t_kd(54'd0), .f_host(), .f_lf(), .f_ks(), .fault(fault));
    end else begin : g_nh
        ot_s81sl_lep_nh u_lep (.clk(clk), .rst_n(rst_n), .ro(lro), .ri(lri),
            .lo0_v(l0v), .lo0_r(l0r), .lo0_d(l0d), .lo1_v(l1v), .lo1_r(l1r), .lo1_d(l1d),
            .li0_v(i0v), .li0_r(i0r), .li0_d(i0d), .li1_v(i1v), .li1_r(i1r), .li1_d(i1d), .rxv(rxv),
            .sl_f(sf), .l0_f(f0), .l1_f(f1), .fault(fault));
    end endgenerate
`endif
    // ---- PHY digital (die masters of the p4l plan lanes; the PMA model inside each macro)
    generate if (PHY0 != 0) begin : g_p0s
        ot_pdie_serdes #(.PMA_LAT(PLAT_S), .DMUT(DMUT)) u_p0 (.clk(clk), .rst(rst_n), .tx(tx0), .rx(rx0), .st(st0),
            .pma_tx(pma_tx0), .pma_tck(), .pma_rx(pma_rx0), .pma_rck(clk));
    end else begin : g_p0u
        wire [512:0] pt;
        ot_pdie_ucie #(.PMA_LAT(PLAT_U)) u_p0 (.clk(clk), .rst(rst_n), .tx(tx0), .rx(rx0), .st(st0),
            .pma_tx(pt), .pma_tck(), .pma_rx(pma_rx0[512:0]), .pma_rck(clk));
        assign pma_tx0 = {31'd0, pt};
    end endgenerate
    generate if (PHY1 != 0) begin : g_p1s
        ot_pdie_serdes #(.PMA_LAT(PLAT_S), .DMUT(DMUT)) u_p1 (.clk(clk), .rst(rst_n), .tx(tx1), .rx(rx1), .st(st1),
            .pma_tx(pma_tx1), .pma_tck(), .pma_rx(pma_rx1), .pma_rck(clk));
    end else begin : g_p1u
        wire [512:0] pt;
        ot_pdie_ucie #(.PMA_LAT(PLAT_U)) u_p1 (.clk(clk), .rst(rst_n), .tx(tx1), .rx(rx1), .st(st1),
            .pma_tx(pt), .pma_tck(), .pma_rx(pma_rx1[512:0]), .pma_rck(clk));
        assign pma_tx1 = {31'd0, pt};
    end endgenerate
endmodule

// The off-chip leg (MODELLED, owner 10-14: only PHY analog / cable / switch): one switch crossing per lane direction,
// a fixed D-cycle delay of the PMA word (one-tier multi-plane fabric: one switch chip per crossing, static circuits, so
// no contention model).  D = round(377.6 ns x 1.2 GHz) - 2 x the PHY macro's own PMA model latency.
// MUT_EXTRA adds cycles (bench schedule mutant: a late lane must trip the static-schedule deadline check).
// ERRP > 0 (SerDes lanes only): pad bit errors, one flipped bit every ERRP cycles at a rotating position (exercises the
// KP4 decoder's correction path; RS(544,514) corrects t = 15 symbols a codeword).
module xdie_s81_chan #(parameter integer W = 544, parameter integer D = 445, parameter integer ERRP = 0) (
    input wire clk, input wire [W-1:0] d, output wire [W-1:0] q
);
    localparam integer N = (D < 1) ? 1 : D;
    localparam integer AW = $clog2(N + 1);
    reg [W-1:0] m [0:N-1];
    reg [AW-1:0] p = 0;
    reg [W-1:0] q_r = 0;
    integer i;
    initial for (i = 0; i < N; i = i + 1) m[i] = 0;
    integer ec = 0;
    reg [W-1:0] em;
    always @(posedge clk) begin
        em = {W{1'b0}};
        if (ERRP > 0) begin
            ec <= (ec == ERRP - 1) ? 0 : ec + 1;
            if (ec == 0) em[(p * 37) % W] = 1'b1;
        end
        q_r <= m[p] ^ em;              // written D cycles ago (q is registered: total D cycles from d)
        m[p] <= d;
        p <= (p == N - 1) ? 0 : p + 1;
    end
    assign q = q_r;
endmodule
