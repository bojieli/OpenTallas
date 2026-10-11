`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_svc_c (s81-svceng-1011): the scan-service SLAB MASTER (one per HBM stack; die name svc_<st>), engine 4 of
// ADAPTER_CONTRACT_1011 through dsfd_svc_join.  Composition (physical/s81_ph_views/svc/composition.json + the job tile):
//   u_job  dsfd_svcio_job (this file)          q pin -> gated q -> u_io; END taps of the output tiles
//   u_io   ot_s81ph_svc_io_t (closed tiles)    dsfd_svcio_q / _od / _ad / _x at their pin groups
//   u_pc   32 x dsfd_svc_pc (closed)           rd / rq / rk / wd, abutting ctrl_<st>'s PC tiles
//   u_q    4 x dsfd_svc_quad  (s81-svcq-1011)  attention tiles + WINDOW share; q in, od / a0 out, 8 PCs each
//   u_x    dsfd_svc_idx       (s81-svcq-1011)  index reader: q in (quadrant 0's copy), a1 / x out
// Quadrant / index interfaces = SVC FRAME PROTOCOL v1.1 (s81-svceng-1011.log); the station chains of the
// composition (Q0 / Q1 / Q2: 34 / 22 / 11 dsfd_svc_stn) are latency-insensitive and sit inside the quadrant links
// (generated with the slab floorplan; not instantiated here).
// ---------------------------------------------------------------------------------------------------------------
module dsfd_svc_c #(parameter integer MUT = 0) (
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
    input  wire [32*4-1:0]   r_beat
);
    wire [514:0] qg; wire [2059:0] q_q;
    wire [3:0] od_v, od_r, a0_v, a0_r; wire [2047:0] od_d, a0_d; wire a1_v, a1_r, x_v, x_r; wire [511:0] a1_d, x_d;
    dsfd_svcio_job #(.MUT(MUT)) u_job (.ck(ck), .rst(rst), .j(j), .jd(jd), .q(q), .q_o(qg),
        .t_a0({ad[492:481], ad[508:496], ad[0]}), .t_a1({ad[1005:994], ad[1021:1009], ad[513]}),
        .t_x({xd[493:482], xd[509:497], xd[1]}), .t_od({od[493:482], od[509:497], od[1]}));
    ot_s81ph_svc_io_t u_io (.ck(ck[0]), .rst(rst[0]), .q(qg), .od(od), .xd(xd), .ad(ad), .fault(fault[0]), .q_q(q_q),
        .od_v(od_v), .od_d(od_d), .od_r(od_r), .a0_v(a0_v), .a0_d(a0_d), .a0_r(a0_r), .a1_v(a1_v), .a1_d(a1_d), .a1_r(a1_r),
        .x_v(x_v), .x_d(x_d), .x_r(x_r), .of(of[0]), .xf(xf[0]), .af(af[0]));
    wire [32*341-1:0] qrq; wire [31:0] qrk, qwd, qrv; wire [32*256-1:0] qr_data; wire [32*17-1:0] qr_tag; wire [32*4-1:0] qr_beat;
    genvar p, g;
    generate for (p = 0; p < 32; p = p + 1) begin : g_pc
        dsfd_svc_pc u_pc (.ck(ck), .rst(rst), .qrq(qrq[341*p +: 341]), .rq(rq[341*p +: 341]), .rk(rk[p]), .qrk(qrk[p]),
            .wd(wd[p]), .qwd(qwd[p]), .rv(rv[p]), .r_data(r_data[256*p +: 256]), .r_tag(r_tag[17*p +: 17]),
            .r_beat(r_beat[4*p +: 4]), .qrv(qrv[p]), .qr_data(qr_data[256*p +: 256]), .qr_tag(qr_tag[17*p +: 17]),
            .qr_beat(qr_beat[4*p +: 4]));
    end
    for (g = 0; g < 4; g = g + 1) begin : g_q
        dsfd_svc_quad #(.QID(g)) u_q (.ck(ck), .rst(rst), .q(q_q[515*g +: 515]),
            .od_v(od_v[g]), .od_d(od_d[512*g +: 512]), .od_r(od_r[g]), .a0_v(a0_v[g]), .a0_d(a0_d[512*g +: 512]), .a0_r(a0_r[g]),
            .qrq(qrq[341*8*g +: 341*8]), .qrk(qrk[8*g +: 8]), .qwd(qwd[8*g +: 8]), .qrv(qrv[8*g +: 8]),
            .qr_data(qr_data[256*8*g +: 256*8]), .qr_tag(qr_tag[17*8*g +: 17*8]), .qr_beat(qr_beat[4*8*g +: 4*8]));
    end endgenerate
    dsfd_svc_idx u_x (.ck(ck), .rst(rst), .q(q_q[514:0]), .a1_v(a1_v), .a1_d(a1_d), .a1_r(a1_r), .x_v(x_v), .x_d(x_d), .x_r(x_r));
endmodule
