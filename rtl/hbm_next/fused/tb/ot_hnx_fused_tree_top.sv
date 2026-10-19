`timescale 1ns/1ps
`default_nettype none
// Bench-only die-equivalent integration of the FUSED csum tree (LH-P3UNITS/FUSHUB 2026-10-19); the hardened parts are
// ot_hnx_fused_tnode / ot_hnx_fused_hub in rtl/hbm_next/fused/ot_hnx_fused_tree.sv.
// ---------------------------------------------------------------------------------------------------------------------
// ot_hnx_fused_tree_top: the die-equivalent integration for benches (NOT a hardened tile): the hub, 28 tree nodes and 32
// lanes wired as the DIE f4c_t9p3 graph, every link a fixed latency = the die's relay stations + landing.  Same ports
// as ot_hnx_fused_top, so tb / vectors are shared.
// Link cycles (E = landing handoff, LANDING-CONTRACT L4): ceil(hops / 2) at forwarded half-cycle 405-um hops, plus
// 1 (ring) + E on the 16 landed links.  Hops = plan_p4 f4c_t9p3 centre-to-centre through the plan's channel (lanes.json):
//   quadrant  q0 SW  q1 NW  q2 SE  q3 NE     (lid = 8 q + i)
//   L1  pair      2      2      2      2     (668 um, same region, not landed)
//   g1 -> g0      8     11      8      8     (landed)
//   g2 -> g3     11      8     11     11     (landed)
//   g0 -> g3     17     17     17     15     (landed)
//   q  -> hub    17     17     19     18     (landed)
// Every pad and the hub's WSC strap are derived from this table by the functions below (the die binder ties the same
// values); the initial block checks that every lane's scalar and chunk round trip is equal (else $fatal).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hnx_fused_link #(parameter integer W = 8, parameter integer N = 1) (
    input wire clk, input wire rst_n, input wire [W-1:0] d, output wire [W-1:0] q
);
    ot_hdc_delay #(.W(W), .D(N), .RESET(1)) u (.clk(clk), .rst_n(rst_n), .d(d), .q(q));
endmodule

module ot_hnx_fused_tree_top #(
    parameter integer D    = 5120,
    parameter integer KX   = 4,
    parameter integer RR   = 10,
    parameter integer RL   = 4,                 // unused (ot_hnx_fused_top compatibility)
    parameter integer NMAX = 8,
    parameter integer MUT  = 0,
    parameter integer E    = 2
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              job_v,
    input  wire [216:0]      job,
    output wire              done,
    output wire              fault,
    output wire              busy,
    output wire [31:0]       rq_v,
    output wire [32*16-1:0]  rq_s,
    input  wire [31:0]       rr_v,
    input  wire [32*256-1:0] rr_d,
    output wire [31:0]       wq_v,
    output wire [32*16-1:0]  wq_s,
    output wire [32*256-1:0] wq_d
);
    localparam integer UW = 271, DW = 173, LA = 6;
    function automatic integer hops(input integer q, input integer kind);   // kind 0 pair, 1 g1g0, 2 g2g3, 3 g0g3, 4 hub
        integer t [0:19];
        begin
            t[0] = 2; t[1] = 8;  t[2] = 11; t[3] = 17; t[4] = 17;
            t[5] = 2; t[6] = 11; t[7] = 8;  t[8] = 17; t[9] = 17;
            t[10] = 2; t[11] = 8; t[12] = 11; t[13] = 17; t[14] = 19;
            t[15] = 2; t[16] = 8; t[17] = 11; t[18] = 15; t[19] = 18;
            hops = t[5 * q + kind];
        end
    endfunction
    function automatic integer lk(input integer q, input integer kind);
        lk = (hops(q, kind) + 1) / 2 + ((kind >= 1) ? 1 + E : 0);
    endfunction
    // round trips (relative; equal node constants per level cancel) and pads
    function automatic integer rt1(input integer q); rt1 = 2 * lk(q, 0); endfunction
    function automatic integer rt2l(input integer q); rt2l = rt1(q) + 2 * lk(q, 1); endfunction
    function automatic integer rt2r(input integer q); rt2r = rt1(q) + 2 * lk(q, 2); endfunction
    function automatic integer rt3a(input integer q); rt3a = rt2l(q) + 2 * lk(q, 3); endfunction
    function automatic integer rt3(input integer q); rt3 = (rt3a(q) > rt2r(q)) ? rt3a(q) : rt2r(q); endfunction
    function automatic integer rtq(input integer q); rtq = rt3(q) + 2 * lk(q, 4); endfunction
    function automatic integer mx(input integer a, input integer b); mx = (a > b) ? a : b; endfunction
    function automatic integer ab(input integer a, input integer b); ab = (a > b) ? a - b : b - a; endfunction
    // per-lane scalar round trip from the hub's cv edge to the root up bus (for wsc), position i of quadrant q
    function automatic integer pad_on(input integer ra, input integer rb, input integer side);   // side 0 a, 1 b
        pad_on = (side == 0) ? ((ra < rb) ? rb - ra : 0) : ((rb < ra) ? ra - rb : 0);
    endfunction
    function automatic integer lane_rt(input integer q, input integer i);
        integer g, links, pads;
        begin
            g = i / 2;
            links = ((i % 2) ? lk(q, 0) : 0) + ((g == 1) ? lk(q, 1) : (g == 2) ? lk(q, 2) : 0)
                  + ((g <= 1) ? lk(q, 3) : 0) + lk(q, 4);
            pads = pad_on(0, rt1(q), i % 2)                                           // n1: a pads 2 lk0
                 + ((g <= 1) ? pad_on(rt1(q), rt1(q) + 2 * lk(q, 1), g % 2) : pad_on(rt1(q) + 2 * lk(q, 2), rt1(q), g % 2))
                 + pad_on(rt3a(q), rt2r(q), (g <= 1) ? 0 : 1)
                 + ((q <= 1) ? pad_on(rtq(0), rtq(1), q % 2) : pad_on(rtq(2), rtq(3), q % 2))
                 + pad_on(mx(rtq(0), rtq(1)), mx(rtq(2), rtq(3)), (q <= 1) ? 0 : 1);
            // hub cv -> pipe 1 -> 5 nodes x 2 -> links -> lane dv_q 1 -> rq_v 1 -> RR + 1 -> up_v 1
            // -> links -> 5 nodes x (pin 1 + align 1 + scalar 1 + out 1) + pads -> root bus
            lane_rt = 1 + 10 + links + 1 + 1 + RR + 1 + 1 + links + 20 + pads;
        end
    endfunction
    function automatic integer lane_rtc(input integer q, input integer i);   // chunk path: + (LA - 1) a node
        lane_rtc = lane_rt(q, i) + 5 * (LA - 1);
    endfunction
    localparam integer RTS = lane_rt(0, 0);
    localparam integer WSC = RTS + 2;           // check edge after the last scalar's scb write (+1 margin)

    // ---- lanes (lid order) and their tree positions
    wire [UW-1:0] lup [0:31]; wire [DW-1:0] ldn [0:31];
    genvar gl;
    generate for (gl = 0; gl < 32; gl = gl + 1) begin : g_ln
        wire uv, ut, fn, fl; wire [9:0] ux; wire [255:0] ud;
        ot_hnx_fused_lane #(.D(D), .KX(KX), .RR(RR), .MUT((MUT >= 1 && MUT <= 6 && MUT != 4) ? MUT : 0)) u_l (
            .clk(clk), .rst_n(rst_n), .lid(5'(gl)), .rq_v(rq_v[gl]), .rq_s(rq_s[gl*16 +: 16]), .rr_v(rr_v[gl]),
            .rr_d(rr_d[gl*256 +: 256]), .wq_v(wq_v[gl]), .wq_s(wq_s[gl*16 +: 16]), .wq_d(wq_d[gl*256 +: 256]),
            .dn_v(ldn[gl][172]), .dn_op(ldn[gl][171:169]), .dn_x(ldn[gl][168:161]), .dn_d(ldn[gl][160:33]),
            .r_v(ldn[gl][32]), .r_d(ldn[gl][31:0]),
            .up_v(uv), .up_t(ut), .up_x(ux), .up_d(ud), .fin(fn), .flt(fl));
        assign lup[gl] = {uv, ut, ux, fn, fn, fl, ud};
    end endgenerate
    // MUT 8: lanes 2 and 4 of quadrant 0 swap tree positions
    function automatic integer lid_at(input integer q, input integer i);
        lid_at = 8 * q + ((MUT == 8 && q == 0 && i == 2) ? 4 : (MUT == 8 && q == 0 && i == 4) ? 2 : i);
    endfunction

    // ---- quadrants
    wire [UW-1:0] uq [0:3]; wire [DW-1:0] dq [0:3], dho [0:3];
    genvar q, g;
    generate for (q = 0; q < 4; q = q + 1) begin : g_q
        wire [UW-1:0] u1 [0:3]; wire [DW-1:0] d1 [0:3];
        for (g = 0; g < 4; g = g + 1) begin : g_n1
            // lane 2g abutted (a), lane 2g + 1 over the stacked-pair link (b)
            wire [UW-1:0] ubl; wire [DW-1:0] dbl;
            ot_hnx_fused_link #(.W(UW), .N(lk(q, 0))) u_lu (.clk(clk), .rst_n(rst_n), .d(lup[lid_at(q, 2 * g + 1)]), .q(ubl));
            ot_hnx_fused_tnode u_n (.clk(clk), .rst_n(rst_n), .pad_k(6'(2 * lk(q, 0))), .pad_b(1'b0),
                .ua(lup[lid_at(q, 2 * g)]), .ub(ubl), .uo(u1[g]), .dn(d1[g]), .da(ldn[lid_at(q, 2 * g)]), .db(dbl));
            ot_hnx_fused_link #(.W(DW), .N(lk(q, 0))) u_ld (.clk(clk), .rst_n(rst_n), .d(dbl), .q(ldn[lid_at(q, 2 * g + 1)]));
        end
        // n2L at group 0: a = n1[0] local, b = n1[1] over g1 -> g0
        wire [UW-1:0] u10, u2l, u2r, u23, u03, u3; wire [DW-1:0] d2l, d2r, d10, d23, d03, d3a, d3b;
        ot_hnx_fused_link #(.W(UW), .N(lk(q, 1))) u_l10u (.clk(clk), .rst_n(rst_n), .d(u1[1]), .q(u10));
        ot_hnx_fused_tnode u_n2l (.clk(clk), .rst_n(rst_n), .pad_k(6'(2 * lk(q, 1) - ((MUT == 9 && q == 0) ? 1 : 0))),
            .pad_b(1'b0), .ua(u1[0]), .ub(u10), .uo(u2l), .dn(d03), .da(d1[0]), .db(d10));
        ot_hnx_fused_link #(.W(DW), .N(lk(q, 1))) u_l10d (.clk(clk), .rst_n(rst_n), .d(d10), .q(d1[1]));
        // n2R at group 3: a = n1[2] over g2 -> g3, b = n1[3] local
        ot_hnx_fused_link #(.W(UW), .N(lk(q, 2))) u_l23u (.clk(clk), .rst_n(rst_n), .d(u1[2]), .q(u23));
        ot_hnx_fused_tnode u_n2r (.clk(clk), .rst_n(rst_n), .pad_k(6'(2 * lk(q, 2))), .pad_b(1'b1),
            .ua(u23), .ub(u1[3]), .uo(u2r), .dn(d3b), .da(d23), .db(d1[3]));
        ot_hnx_fused_link #(.W(DW), .N(lk(q, 2))) u_l23d (.clk(clk), .rst_n(rst_n), .d(d23), .q(d1[2]));
        // n3 (quadrant node) at group 3: a = n2L over g0 -> g3, b = n2R local
        ot_hnx_fused_link #(.W(UW), .N(lk(q, 3))) u_l03u (.clk(clk), .rst_n(rst_n), .d(u2l), .q(u03));
        ot_hnx_fused_tnode u_n3 (.clk(clk), .rst_n(rst_n), .pad_k(6'(ab(rt3a(q), rt2r(q)))), .pad_b(rt2r(q) < rt3a(q)),
            .ua(u03), .ub(u2r), .uo(u3), .dn(dq[q]), .da(d3a), .db(d3b));
        ot_hnx_fused_link #(.W(DW), .N(lk(q, 3))) u_l03d (.clk(clk), .rst_n(rst_n), .d(d3a), .q(d03));
        // quadrant -> hub
        ot_hnx_fused_link #(.W(UW), .N(lk(q, 4))) u_lhu (.clk(clk), .rst_n(rst_n), .d(u3), .q(uq[q]));
        ot_hnx_fused_link #(.W(DW), .N(lk(q, 4))) u_lhd (.clk(clk), .rst_n(rst_n), .d(dho[q]), .q(dq[q]));
    end endgenerate
    ot_hnx_fused_hub #(.D(D), .RR(RR), .NMAX(NMAX), .MUT((MUT == 4 || MUT == 7) ? MUT : 0)) u_hub (.clk(clk), .rst_n(rst_n),
        .job_v(job_v), .job(job), .done(done), .fault(fault), .busy(busy), .wsc(8'(WSC)),
        .pk4a(6'(ab(rtq(0), rtq(1)))), .pk4b(6'(ab(rtq(2), rtq(3)))),
        .pk5(6'(ab(mx(rtq(0), rtq(1)), mx(rtq(2), rtq(3))))),
        .pb4a(rtq(1) < rtq(0)), .pb4b(rtq(3) < rtq(2)), .pb5(mx(rtq(2), rtq(3)) < mx(rtq(0), rtq(1))),
        .uq0(uq[0]), .uq1(uq[1]), .uq2(uq[2]), .uq3(uq[3]),
        .dq0(dho[0]), .dq1(dho[1]), .dq2(dho[2]), .dq3(dho[3]));

`ifndef SYNTHESIS
    // static schedule self-check: every lane's scalar and chunk round trip equal, every pad within the 32-edge ring
    initial begin
        integer qq, ii, r0;
        r0 = lane_rt(0, 0);
        for (qq = 0; qq < 4; qq = qq + 1) begin
            for (ii = 0; ii < 8; ii = ii + 1)
                if (lane_rt(qq, ii) != r0 || lane_rtc(qq, ii) != lane_rtc(0, 0))
                    $fatal(1, "HNX_TREE round trip q%0d i%0d = %0d != %0d", qq, ii, lane_rt(qq, ii), r0);
            if (2 * lk(qq, 1) > 32 || 2 * lk(qq, 2) > 32 || ab(rt3a(qq), rt2r(qq)) > 32)
                $fatal(1, "HNX_TREE pad > 32 in quadrant %0d", qq);
            $display("HNX_TREE q%0d links pair %0d g1g0 %0d g2g3 %0d g0g3 %0d hub %0d | pads n1 a%0d n2L a%0d n2R b%0d n3 %s%0d",
                     qq, lk(qq, 0), lk(qq, 1), lk(qq, 2), lk(qq, 3), lk(qq, 4), 2 * lk(qq, 0), 2 * lk(qq, 1),
                     2 * lk(qq, 2), (rt2r(qq) < rt3a(qq)) ? "b" : "a", ab(rt3a(qq), rt2r(qq)));
        end
        $display("HNX_TREE E=%0d hub pads t4a %0d t4b %0d t5 %0d | scalar round trip %0d (wsc %0d), chunk %0d, MUT=%0d",
                 E, ab(rtq(0), rtq(1)), ab(rtq(2), rtq(3)), ab(mx(rtq(0), rtq(1)), mx(rtq(2), rtq(3))), RTS, WSC,
                 lane_rtc(0, 0), MUT);
    end
`endif
endmodule
`default_nettype wire
