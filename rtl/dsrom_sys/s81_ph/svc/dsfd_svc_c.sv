`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_svc_c (s81-svceng-1011; hierarchical compute s81die-1011/ctrl svch 2026-10-11): the scan-service SLAB MASTER
// (one per HBM stack ST; die name svc_<st>), engine 4 of ADAPTER_CONTRACT_1011 through dsfd_svc_join.
// Composition (physical/s81_ph_views/svc/composition.json + the job tile):
//   u_job  dsfd_svcio_job (closed)             q pin -> gated q -> u_io; END taps of the output tiles
//   u_io   ot_s81ph_svc_io_t (closed tiles)    dsfd_svcio_q / _od / _ad / _x at their pin groups
//   u_pc   32 x dsfd_svc_pc (closed)           rd / rq / rk / wd, abutting ctrl_<st>'s PC tiles
//   u_q    4 x dsfd_svc_quad #(QID)            a QUARTER of the attention (head_dim split, dims 128 g ..) + its 8 PCs'
//                                              own pipelined arbiter; quadrant 2 also hosts the window source, the
//                                              owned-row fetch, the G router and the od / a0 result emitter
//   u_x    dsfd_svc_idx                        index reader (unchanged ot_s81_svcq_idx), A lanes into the quadrants
//   u_r*   dsfd_svch_rly / dsfd_svch_xstn      relay stations of every seam (<= ~450 um a stage)
// Replaces the flat ot_s81_svcq_slab (owner textbook audit 10-11: class 1/4 single clock tree + pin wires over the
// 8.5-mm stack, class 5 single-cycle 14-source x 32-PC arbiter).  Seam relay counts (stage <= ~450 um, from the
// composition: quadrants 2,125 um wide side by side, idx tile in the upper band over the Q1 / Q2 boundary, hub N-E):
//   NRH  Q2 <-> Q0 / Q1 / Q3 = 9 / 5 / 5       B / G / window / fetched-row / p.v / fault lanes
//   NRI  idx <-> Q0 / Q1 / Q2 / Q3 = 7 / 3 / 3 / 8   A lanes
//   NRS  Q0 -> Q1, Q1 -> Q2, Q3 -> Q2 = 5       q.k partial-score lanes
//   NRQ  u_io q copy 0 -> idx = 6 (valid-only); NRX idx x -> u_io = 6 skid stations; NRHW host hw / hc <-> Q2 = 4
// Host writes (hw / hc, dsfd_host_sd contract): KV / RoPE sector -> this stack's HBM sector addr[29:0] through the home's
// G port 12 (PC by the PHY map), credit cr per word taken, ack = completed host sector writes per cycle.
// Quadrant od / a0 links keep the composition's station chains (u_stn_q0/1/2, latency-insensitive, generated with the
// slab floorplan; not instantiated here).  SVC FRAME PROTOCOL v1.1 unchanged: one result source (id 0) on a0 / od.
// ---------------------------------------------------------------------------------------------------------------
module dsfd_svc_c #(parameter integer MUT = 0, parameter integer DIE_ID = 0, parameter integer ST = 0,
                    parameter bit SRAM_MACRO = 0, parameter bit NATIVE_FP32_PV = 0) (
    input  wire [0:0]     ck,
    input  wire [0:0]     rst,
    input  wire [32:0]    j,
    output wire [1:0]     jd,
    input  wire [514:0]   q,
    output wire [513:0]   od, output wire [0:0] of,
    output wire [513:0]   xd, output wire [0:0] xf,
    output wire [1025:0]  ad, output wire [0:0] af,
    output wire [0:0]     fault,
    // HBM controller (ctrl_<st>) per-PC faces
    output wire [32*341-1:0] rq,
    input  wire [31:0]    rk, wd, rv,
    input  wire [32*256-1:0] r_data,
    input  wire [32*17-1:0]  r_tag,
    input  wire [32*4-1:0]   r_beat,
    // per-stack host write face (dsfd_host_sd hw<s> / hc<s>): {cls 2, we, addr 32, d 256, v} in, {ack 8, cr} out
    input  wire [291:0]   hw,
    output wire [8:0]     hc,
    // s81-die-rtl-bind 2026-10-14 (die bus st_<st>, composition.json nets.status): the stack's HBM controller status
    // hs = {fault, live} of dsfd_ctrl.st.  A controller fault, or the controller dropping live after it came up, fails
    // the svc closed: sticky, folded into the job-done fault jd[1] (-> dsfd_svc_join c_st -> sequencer s4) and into
    // fault.  Issue needs no live gate: the controller returns no PC credit (rk) before it is live.
    input  wire [1:0]     hs
);
    localparam integer NRH0 = 9, NRH1 = 5, NRH3 = 5, NRS = 5, NRQ = 6, NRX = 6;
    localparam integer NRI0 = 7, NRI1 = 3, NRI2 = 3, NRI3 = 8;
    localparam integer NG = 13, NRHW = 4;   // NRHW: N-E host pins <-> quadrant 2
    function automatic integer nrh(input integer d); nrh = (d == 0) ? NRH0 : (d == 1) ? NRH1 : (d == 3) ? NRH3 : 0; endfunction
    function automatic integer rq_(input integer d); rq_ = (d < 2) ? d : 2; endfunction   // remote-quadrant index (0, 1, 3)
    function automatic integer nri(input integer d); nri = (d == 0) ? NRI0 : (d == 1) ? NRI1 : (d == 2) ? NRI2 : NRI3; endfunction

    wire [514:0] qg, q_native; wire [2059:0] q_q;
    wire probability_fault;
    generate if (NATIVE_FP32_PV) begin : g_native_pv
        ot_s81_svc_probability_frame u_pv_pack (.clk(ck[0]), .rst_n(rst[0]), .q(q), .q_o(q_native), .fault(probability_fault));
    end else begin : g_legacy_pv
        assign q_native = q; assign probability_fault = 1'b0;
    end endgenerate
    wire [3:0] od_v, od_r, a0_v, a0_r; wire [2047:0] od_d, a0_d; wire a1_v, a1_r, x_v, x_r; wire [511:0] a1_d, x_d;
    wire [1:0] jd_j; wire fault_io;
    dsfd_svc_hs #(.MUT(MUT)) u_hs (.ck(ck[0]), .rst(rst[0]), .hs(hs), .jd_i(jd_j | {probability_fault,1'b0}), .flt_i(fault_io | probability_fault), .jd_o(jd), .flt_o(fault[0]));
    dsfd_svcio_job #(.MUT(MUT)) u_job (.ck(ck), .rst(rst), .j(j), .jd(jd_j), .q(q_native), .q_o(qg),
        .t_a0({ad[492:481], ad[508:496], ad[0]}), .t_a1({ad[1005:994], ad[1021:1009], ad[513]}),
        .t_x({xd[493:482], xd[509:497], xd[1]}), .t_od({od[493:482], od[509:497], od[1]}));
    ot_s81ph_svc_io_t u_io (.ck(ck[0]), .rst(rst[0]), .q(qg), .od(od), .xd(xd), .ad(ad), .fault(fault_io), .q_q(q_q),
        .od_v(od_v), .od_d(od_d), .od_r(od_r), .a0_v(a0_v), .a0_d(a0_d), .a0_r(a0_r), .a1_v(a1_v), .a1_d(a1_d), .a1_r(a1_r),
        .x_v(x_v), .x_d(x_d), .x_r(x_r), .of(of[0]), .xf(xf[0]), .af(af[0]));
    wire [32*341-1:0] qrq; wire [31:0] qrk, qwd, qrv; wire [32*256-1:0] qr_data; wire [32*17-1:0] qr_tag; wire [32*4-1:0] qr_beat;
    genvar p, g;
    generate for (p = 0; p < 32; p = p + 1) begin : g_pc
        dsfd_svc_pc u_pc (.ck(ck), .rst(rst), .qrq(qrq[341*p +: 341]), .rq(rq[341*p +: 341]), .rk(rk[p]), .qrk(qrk[p]),
            .wd(wd[p]), .qwd(qwd[p]), .rv(rv[p]), .r_data(r_data[256*p +: 256]), .r_tag(r_tag[17*p +: 17]),
            .r_beat(r_beat[4*p +: 4]), .qrv(qrv[p]), .qr_data(qr_data[256*p +: 256]), .qr_tag(qr_tag[17*p +: 17]),
            .qr_beat(qr_beat[4*p +: 4]));
    end endgenerate

    // ---------------- quadrant-side bundles ----------------
    wire [31:0] aq_v, aq_c, ar_v, ar_c, bq_v, bq_c, br_v, br_c;
    wire [32*50-1:0] aq_d; wire [32*276-1:0] ar_d; wire [32*46-1:0] bq_d; wire [32*272-1:0] br_d;
    wire [3:0] gq_v, gq_c, gr_v, gr_c, wb_v, wb_c, fb_v, so_v, so_c, sa_v, sa_c, sb_v, sb_c, po_v, po_c, fo;
    wire [4*344-1:0] gq_d; wire [4*276-1:0] gr_d; wire [4*NG-1:0] gwd; wire [4*4228-1:0] wb_d; wire [4*607-1:0] fb_d;
    wire [4*2132-1:0] so_d, sa_d, sb_d; wire [4*513-1:0] po_d;
    // home ends (quadrant 2)
    wire [23:0] h_bq_v, h_bq_c, h_br_v, h_br_c; wire [24*46-1:0] h_bq_d; wire [24*272-1:0] h_br_d;
    wire [2:0] h_gq_v, h_gq_c, h_gr_v, h_gr_c, h_wb_v, h_wb_c, h_fb_v, h_pv_v, h_pv_c, h_flt;
    wire [3*344-1:0] h_gq_d; wire [3*276-1:0] h_gr_d; wire [3*NG-1:0] h_gwd; wire [3*4228-1:0] h_wb_d;
    wire [3*607-1:0] h_fb_d; wire [3*513-1:0] h_pv_d;
    wire [23:0] hq_bq_v [0:3]; wire [24*46-1:0] hq_bq_d [0:3]; wire [23:0] hq_br_c [0:3];
    wire [2:0] hq_gq_v [0:3], hq_gr_c [0:3], hq_wb_v [0:3], hq_fb_v [0:3], hq_pv_c [0:3];
    wire [3*344-1:0] hq_gq_d [0:3]; wire [3*4228-1:0] hq_wb_d [0:3]; wire [3*607-1:0] hq_fb_d [0:3];
    wire hwq_v; wire [290:0] hwq_d; wire [8:0] hq_hc [0:3];
    dsfd_svch_rly #(.W(291), .NR(NRHW)) u_hw (.ck(ck), .rst(rst), .i_v(hw[0]), .i_d(hw[291:1]), .o_v(hwq_v), .o_d(hwq_d));
    dsfd_svch_rly #(.W(1), .NR(NRHW), .V(9)) u_hc (.ck(ck), .rst(rst), .i_v(hq_hc[2]), .i_d(1'b0), .o_v(hc), .o_d());
    // index-reader ends
    wire [31:0] x_aq_v, x_aq_c, x_ar_v, x_ar_c; wire [32*50-1:0] x_aq_d; wire [32*276-1:0] x_ar_d;

    generate for (g = 0; g < 4; g = g + 1) begin : g_q
        // non-home quadrants have 1-bit h_* / unused score ports (tied off inside); quadrant 2 has the full bundles
        dsfd_svc_quad #(.QID(g), .DIE_ID(DIE_ID), .ST(ST), .SRAM_MACRO(SRAM_MACRO), .NRH0(NRH0), .NRH1(NRH1), .NRH3(NRH3), .NRI(nri(g)), .NRS(NRS),
                        .NG(NG)) u_q (
            .ck(ck), .rst(rst), .q(q_q[515*g +: 515]),
            .od_v(od_v[g]), .od_d(od_d[512*g +: 512]), .od_r(od_r[g]), .a0_v(a0_v[g]), .a0_d(a0_d[512*g +: 512]), .a0_r(a0_r[g]),
            .qrq(qrq[341*8*g +: 341*8]), .qrk(qrk[8*g +: 8]), .qwd(qwd[8*g +: 8]), .qrv(qrv[8*g +: 8]),
            .qr_data(qr_data[256*8*g +: 256*8]), .qr_tag(qr_tag[17*8*g +: 17*8]), .qr_beat(qr_beat[4*8*g +: 4*8]),
            .aq_v(aq_v[8*g +: 8]), .aq_d(aq_d[50*8*g +: 50*8]), .aq_c(aq_c[8*g +: 8]),
            .ar_v(ar_v[8*g +: 8]), .ar_d(ar_d[276*8*g +: 276*8]), .ar_c(ar_c[8*g +: 8]),
            .bq_v(bq_v[8*g +: 8]), .bq_d(bq_d[46*8*g +: 46*8]), .bq_c(bq_c[8*g +: 8]),
            .br_v(br_v[8*g +: 8]), .br_d(br_d[272*8*g +: 272*8]), .br_c(br_c[8*g +: 8]),
            .gq_v(gq_v[g]), .gq_d(gq_d[344*g +: 344]), .gq_c(gq_c[g]), .gr_v(gr_v[g]), .gr_d(gr_d[276*g +: 276]),
            .gr_c(gr_c[g]), .gwd(gwd[NG*g +: NG]),
            .wb_v(wb_v[g]), .wb_d(wb_d[4228*g +: 4228]), .wb_c(wb_c[g]), .fb_v(fb_v[g]), .fb_d(fb_d[607*g +: 607]),
            .so_v(so_v[g]), .so_d(so_d[2132*g +: 2132]), .so_c(so_c[g]),
            .sa_v(sa_v[g]), .sa_d(sa_d[2132*g +: 2132]), .sa_c(sa_c[g]),
            .sb_v(sb_v[g]), .sb_d(sb_d[2132*g +: 2132]), .sb_c(sb_c[g]),
            .po_v(po_v[g]), .po_d(po_d[513*g +: 513]), .po_c(po_c[g]), .fo(fo[g]),
            .h_bq_v(hq_bq_v[g]), .h_bq_d(hq_bq_d[g]), .h_bq_c(h_bq_c), .h_br_v(h_br_v), .h_br_d(h_br_d), .h_br_c(hq_br_c[g]),
            .h_gq_v(hq_gq_v[g]), .h_gq_d(hq_gq_d[g]), .h_gq_c(h_gq_c), .h_gr_v(h_gr_v), .h_gr_d(h_gr_d), .h_gr_c(hq_gr_c[g]),
            .h_gwd(h_gwd), .h_wb_v(hq_wb_v[g]), .h_wb_d(hq_wb_d[g]), .h_wb_c(h_wb_c), .h_fb_v(hq_fb_v[g]), .h_fb_d(hq_fb_d[g]),
            .h_pv_v(h_pv_v), .h_pv_d(h_pv_d), .h_pv_c(hq_pv_c[g]), .h_flt(h_flt),
            .h_hw_v(hwq_v), .h_hw_d(hwq_d), .h_hc(hq_hc[g]));
    end endgenerate
    assign h_bq_v = hq_bq_v[2]; assign h_bq_d = hq_bq_d[2]; assign h_br_c = hq_br_c[2];
    assign h_gq_v = hq_gq_v[2]; assign h_gq_d = hq_gq_d[2]; assign h_gr_c = hq_gr_c[2];
    assign h_wb_v = hq_wb_v[2]; assign h_wb_d = hq_wb_d[2]; assign h_fb_v = hq_fb_v[2]; assign h_fb_d = hq_fb_d[2];
    assign h_pv_c = hq_pv_c[2];

    // ---------------- seams: relay stations ----------------
    generate for (g = 0; g < 4; g = g + 1) begin : g_s
        if (g != 2) begin : g_hs
            localparam integer N = nrh(g), R = rq_(g), K = 8 * rq_(g);
            // B lanes (requests home -> quadrant, credits back; responses quadrant -> home, credits back)
            dsfd_svch_rly #(.W(8*46), .NR(N), .V(8)) u_bq (.ck(ck), .rst(rst), .i_v(h_bq_v[K +: 8]), .i_d(h_bq_d[46*K +: 46*8]),
                .o_v(bq_v[8*g +: 8]), .o_d(bq_d[46*8*g +: 46*8]));
            dsfd_svch_rly #(.W(1), .NR(N), .V(8)) u_bqc (.ck(ck), .rst(rst), .i_v(bq_c[8*g +: 8]), .i_d(1'b0), .o_v(h_bq_c[K +: 8]), .o_d());
            dsfd_svch_rly #(.W(8*272), .NR(N), .V(8)) u_br (.ck(ck), .rst(rst), .i_v(br_v[8*g +: 8]), .i_d(br_d[272*8*g +: 272*8]),
                .o_v(h_br_v[K +: 8]), .o_d(h_br_d[272*K +: 272*8]));
            dsfd_svch_rly #(.W(1), .NR(N), .V(8)) u_brc (.ck(ck), .rst(rst), .i_v(h_br_c[K +: 8]), .i_d(1'b0), .o_v(br_c[8*g +: 8]), .o_d());
            // G lane
            dsfd_svch_rly #(.W(344), .NR(N)) u_gq (.ck(ck), .rst(rst), .i_v(h_gq_v[R]), .i_d(h_gq_d[344*R +: 344]),
                .o_v(gq_v[g]), .o_d(gq_d[344*g +: 344]));
            dsfd_svch_rly #(.W(1), .NR(N)) u_gqc (.ck(ck), .rst(rst), .i_v(gq_c[g]), .i_d(1'b0), .o_v(h_gq_c[R]), .o_d());
            dsfd_svch_rly #(.W(276), .NR(N), .V(1 + NG)) u_gr (.ck(ck), .rst(rst), .i_v({gwd[NG*g +: NG], gr_v[g]}), .i_d(gr_d[276*g +: 276]),
                .o_v({h_gwd[NG*R +: NG], h_gr_v[R]}), .o_d(h_gr_d[276*R +: 276]));
            dsfd_svch_rly #(.W(1), .NR(N)) u_grc (.ck(ck), .rst(rst), .i_v(h_gr_c[R]), .i_d(1'b0), .o_v(gr_c[g]), .o_d());
            // window beats, fetched rows, p.v, fault
            dsfd_svch_rly #(.W(4228), .NR(N)) u_wb (.ck(ck), .rst(rst), .i_v(h_wb_v[R]), .i_d(h_wb_d[4228*R +: 4228]),
                .o_v(wb_v[g]), .o_d(wb_d[4228*g +: 4228]));
            dsfd_svch_rly #(.W(1), .NR(N)) u_wbc (.ck(ck), .rst(rst), .i_v(wb_c[g]), .i_d(1'b0), .o_v(h_wb_c[R]), .o_d());
            dsfd_svch_rly #(.W(607), .NR(N)) u_fb (.ck(ck), .rst(rst), .i_v(h_fb_v[R]), .i_d(h_fb_d[607*R +: 607]),
                .o_v(fb_v[g]), .o_d(fb_d[607*g +: 607]));
            dsfd_svch_rly #(.W(513), .NR(N), .V(2)) u_pv (.ck(ck), .rst(rst), .i_v({fo[g], po_v[g]}), .i_d(po_d[513*g +: 513]),
                .o_v({h_flt[R], h_pv_v[R]}), .o_d(h_pv_d[513*R +: 513]));
            dsfd_svch_rly #(.W(1), .NR(N)) u_pvc (.ck(ck), .rst(rst), .i_v(h_pv_c[R]), .i_d(1'b0), .o_v(po_c[g]), .o_d());
        end else begin : g_hl
            // quadrant 2's own lanes are internal to its tile
            assign bq_v[16 +: 8] = 8'd0; assign bq_d[46*16 +: 46*8] = '0; assign br_c[16 +: 8] = 8'd0;
            assign gq_v[2] = 1'b0; assign gq_d[344*2 +: 344] = '0; assign gr_c[2] = 1'b0;
            assign wb_v[2] = 1'b0; assign wb_d[4228*2 +: 4228] = '0;
            assign fb_v[2] = 1'b0; assign fb_d[607*2 +: 607] = '0; assign po_c[2] = 1'b0;
        end
        // A lanes (index reader <-> quadrant g)
        localparam integer NI = nri(g);
        dsfd_svch_rly #(.W(8*50), .NR(NI), .V(8)) u_aq (.ck(ck), .rst(rst), .i_v(x_aq_v[8*g +: 8]), .i_d(x_aq_d[50*8*g +: 50*8]),
            .o_v(aq_v[8*g +: 8]), .o_d(aq_d[50*8*g +: 50*8]));
        dsfd_svch_rly #(.W(1), .NR(NI), .V(8)) u_aqc (.ck(ck), .rst(rst), .i_v(aq_c[8*g +: 8]), .i_d(1'b0), .o_v(x_aq_c[8*g +: 8]), .o_d());
        dsfd_svch_rly #(.W(8*276), .NR(NI), .V(8)) u_ar (.ck(ck), .rst(rst), .i_v(ar_v[8*g +: 8]), .i_d(ar_d[276*8*g +: 276*8]),
            .o_v(x_ar_v[8*g +: 8]), .o_d(x_ar_d[276*8*g +: 276*8]));
        dsfd_svch_rly #(.W(1), .NR(NI), .V(8)) u_arc (.ck(ck), .rst(rst), .i_v(x_ar_c[8*g +: 8]), .i_d(1'b0), .o_v(ar_c[8*g +: 8]), .o_d());
    end endgenerate
    // q.k partial-score lanes: Q0 -> Q1 (a), Q1 -> Q2 (a), Q3 -> Q2 (b)
    dsfd_svch_rly #(.W(2132), .NR(NRS)) u_s01 (.ck(ck), .rst(rst), .i_v(so_v[0]), .i_d(so_d[0 +: 2132]), .o_v(sa_v[1]), .o_d(sa_d[2132*1 +: 2132]));
    dsfd_svch_rly #(.W(1), .NR(NRS)) u_s01c (.ck(ck), .rst(rst), .i_v(sa_c[1]), .i_d(1'b0), .o_v(so_c[0]), .o_d());
    dsfd_svch_rly #(.W(2132), .NR(NRS)) u_s12 (.ck(ck), .rst(rst), .i_v(so_v[1]), .i_d(so_d[2132*1 +: 2132]), .o_v(sa_v[2]), .o_d(sa_d[2132*2 +: 2132]));
    dsfd_svch_rly #(.W(1), .NR(NRS)) u_s12c (.ck(ck), .rst(rst), .i_v(sa_c[2]), .i_d(1'b0), .o_v(so_c[1]), .o_d());
    dsfd_svch_rly #(.W(2132), .NR(NRS)) u_s32 (.ck(ck), .rst(rst), .i_v(so_v[3]), .i_d(so_d[2132*3 +: 2132]), .o_v(sb_v[2]), .o_d(sb_d[2132*2 +: 2132]));
    dsfd_svch_rly #(.W(1), .NR(NRS)) u_s32c (.ck(ck), .rst(rst), .i_v(sb_c[2]), .i_d(1'b0), .o_v(so_c[3]), .o_d());
    assign sa_v[0] = 1'b0; assign sa_d[0 +: 2132] = '0; assign sa_v[3] = 1'b0; assign sa_d[2132*3 +: 2132] = '0;
    assign sb_v[0] = 1'b0; assign sb_d[0 +: 2132] = '0; assign sb_v[1] = 1'b0; assign sb_d[2132*1 +: 2132] = '0;
    assign sb_v[3] = 1'b0; assign sb_d[2132*3 +: 2132] = '0; assign so_c[2] = 1'b0;

    // ---------------- index reader ----------------
    wire xq_v; wire [513:0] xq_d;
    dsfd_svch_rly #(.W(514), .NR(NRQ)) u_xq (.ck(ck), .rst(rst), .i_v(q_q[0]), .i_d(q_q[514:1]), .o_v(xq_v), .o_d(xq_d));
    wire ix_v, ix_r; wire [511:0] ix_d; wire ix_f;
    dsfd_svc_idx #(.ST(ST), .NRI0(NRI0), .NRI1(NRI1), .NRI2(NRI2), .NRI3(NRI3)) u_x (.ck(ck), .rst(rst), .q({xq_d, xq_v}),
        .a1_v(a1_v), .a1_d(a1_d), .a1_r(a1_r), .x_v(ix_v), .x_d(ix_d), .x_r(ix_r),
        .aq_v(x_aq_v), .aq_d(x_aq_d), .aq_c(x_aq_c), .ar_v(x_ar_v), .ar_d(x_ar_d), .ar_c(x_ar_c), .fo(ix_f));
    wire [NRX:0] xs_v, xs_r; wire [512*(NRX+1)-1:0] xs_d;
    assign xs_v[0] = ix_v; assign xs_d[511:0] = ix_d; assign ix_r = xs_r[0];
    generate for (g = 0; g < NRX; g = g + 1) begin : g_xs
        dsfd_svch_xstn u_s (.ck(ck), .rst(rst), .i_v(xs_v[g]), .i_d(xs_d[512*g +: 512]), .i_r(xs_r[g]),
            .o_v(xs_v[g+1]), .o_d(xs_d[512*(g+1) +: 512]), .o_r(xs_r[g+1]));
    end endgenerate
    assign x_v = xs_v[NRX]; assign x_d = xs_d[512*NRX +: 512]; assign xs_r[NRX] = x_r;
endmodule

// dsfd_svc_hs (s81-die-rtl-bind 2026-10-14): the HBM controller status face of the svc slab.  hs = {fault, live} from
// dsfd_ctrl (its own flops, stream domain, 2-flop synchronised here all the same: the slab's ck root is not the
// controller's).  hf (sticky until reset): the controller's fault, or live falling after it was seen high.
// jd_o = jd_i with the fault bit ORed with hf, flt_o = flt_i | hf: both launched from flops (+1 cycle on the svc job
// done / fault, priced 0 against the 2,951-cycle idx.score op).  MUT bit 3 (negative control): hf never reaches jd / fault.
module dsfd_svc_hs #(parameter integer MUT = 0) (
    input  wire       ck, rst,
    input  wire [1:0] hs, jd_i,
    input  wire       flt_i,
    output reg  [1:0] jd_o,
    output reg        flt_o
);
    reg [1:0] rs_q;
    always @(posedge ck or negedge rst) if (!rst) rs_q <= 2'b00; else rs_q <= {rs_q[0], 1'b1};
    wire rn = rs_q[1];
    (* async_reg = "true" *) reg [1:0] s0, s1;
    reg up, hf;
    always @(posedge ck or negedge rn)
        if (!rn) begin s0 <= 2'b00; s1 <= 2'b00; up <= 1'b0; hf <= 1'b0; jd_o <= 2'b00; flt_o <= 1'b0; end
        else begin
            s0 <= hs; s1 <= s0;
            if (s1[0]) up <= 1'b1;
            if (s1[1] || (up && !s1[0])) hf <= 1'b1;
            jd_o  <= {jd_i[1] | (hf & !MUT[3]), jd_i[0]};
            flt_o <= flt_i | (hf & !MUT[3]);
        end
endmodule
