`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-SVC (2026-10-17, S81-DV p4h regional service slice dsdv_svc_rs x16): dsdv_svc_sx, the SCORE EXCHANGE of one
// slice.  One master for all 16 slices; the slice-id strap sid selects its row of the generated role ROM
// (dsdv_svc_sx_roles.svh, tools/s81_dv/svc_rs/svc_rs_embed.py).
//
// Golden (dsfd_svc_c): the q.k score of a row is the BALANCED tree over the 16 TD = 32 head-dim tiles, in dim order
// (D = 128 engine heap tree per quadrant, then ot_s81_svch_comb ((Q0 + Q1) + (Q2 + Q3))).  FP32 adds do not associate,
// so the slices carry that tree: every slice injects its tile partial and hosts at most ONE tree node (64 x
// ot_hdc_v41x_qaddf); operands travel neighbour-only over N / E / S / W; each directed link carries at most one lane
// (25 link hops).  The complete beat appears at the root slice (rt_*) and is SCATTERED back down the same tree; the leaf
// of tile t taps head t (t_*).  Static schedule, no credit / ready; sticky fault on misalignment / tag / stray valid.
//
// S81U-SVCX (2026-10-17) SPLIT FORM.  The monolith (97c52bae0) was one tile with 6,420 lane pins per face (unkittable).
// It is now:
//   * 4 x dsdv_svc_sx_row, the hardened-once CENTRE LEAF: one score row each (16 qaddf + the gather / scatter
//     crossbars), every pin registered; the 4 rows are independent (no lane mixes rows), so this is bit-identical;
//   * closed relay stations dsfd_dvrly_276_<in><out> (S81-B: CLOSED, native PASS) on every face lane:
//     per face and row, gather 534 b = 2 stations, scatter 270 b = 1 station; OUT lanes NR + 1 stations deep
//     (A at ~1/4 of the hop, B at the slice edge), IN lanes NR deep (C at ~3/4).  NR = 1 keeps the monolith's
//     5-cycle hop (centre reg, A, B | C, leaf pin flop): ZERO added cycles, the role ROM offsets are unchanged.
//     Hop geometry (p4h 1,222 x 1,338 um slices): leaf pin -> A -> B -> C -> leaf pin spans at most one slice pitch
//     (pins at the slice centre line, the inner faces of the 2 x 2 leaf cluster), 4 segments of <= 335 um <= 405.
// The slice-face ports keep the monolith's lane format (pure wiring: row r = tag[5r +: 5], y lanes 16r .. 16r + 15,
// flags 16r .. 16r + 15; scatter slot bits 128 + r and 32r); relay spare bits (18 per gather pair, 6 per scatter
// station) are constant 0.
// MUT (bench negative controls): bit 0 = the right operand's flags are not ORed in; bit 1 = right scatter split off by
// one head slot.  DSDV_SX_MUT_ORDER (define) = role ROM of a tree whose tiles 0..3 sum as a chain (((t0+t1)+t2)+t3).
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_svc_sx #(
    parameter integer MUT = 0,
    parameter integer NR = 1,              // relay stations per hop half (IN: NR, OUT: NR + 1)
    parameter integer FX = 5,
    parameter integer F12 = 1
) (
    input  wire              ck,
    input  wire              rst,
    input  wire [3:0]        sid,
    input  wire              l_v,
    input  wire [2131:0]     l_d,
    input  wire [3:0]        gi_v,
    input  wire [4*2132-1:0] gi_d,
    output wire [3:0]        go_v,
    output wire [4*2132-1:0] go_d,
    input  wire [3:0]        si_v,
    input  wire [4*1076-1:0] si_d,
    output wire [3:0]        so_v,
    output wire [4*1076-1:0] so_d,
    output wire              rt_v,
    output wire [2131:0]     rt_d,
    output wire              t_v,
    output wire [19:0]       t_tag,
    output wire [127:0]      t_y,
    output wire [3:0]        t_f,
    output wire              fault
);
    localparam integer W = 2132, SW = 1076, RW = 533, RSW = 269;
    genvar r, f, j;
    // beat <-> row lane (pure wiring)
    function automatic [RW-1:0] g_row(input [W-1:0] b, input integer rr);
        g_row = {b[2112 + 5*rr +: 5], b[64 + 512*rr +: 512], b[16*rr +: 16]};
    endfunction
    function automatic [RSW-1:0] s_row(input [SW-1:0] b, input integer rr);
        s_row[RSW-1 -: 5] = b[1056 + 5*rr +: 5];
        for (int h = 0; h < 8; h++) s_row[33*h +: 33] = {b[132*h + 128 + rr], b[132*h + 32*rr +: 32]};
    endfunction
    wire [3:0] rrt_v, rt_vv, rflt;
    wire [RW:0] rrt [0:3]; wire [38:0] rt [0:3];

    generate for (r = 0; r < 4; r = r + 1) begin : g_r
        wire [RW:0] lgi [0:3], lgo [0:3]; wire [RSW:0] lsi [0:3], lso [0:3];   // leaf face ports, f = N, E, S, W
        for (f = 0; f < 4; f = f + 1) begin : g_f
            // ---- IN stations (C): face f -> leaf; NR deep ----
            wire [551:0] gin [0:NR]; wire [275:0] sin [0:NR];
            assign gin[0] = {18'd0, gi_v[f], g_row(gi_d[W*f +: W], r)};
            assign sin[0] = {6'd0, si_v[f], s_row(si_d[SW*f +: SW], r)};
            for (j = 0; j < NR; j = j + 1) begin : g_c
                dsdv_sx_rly_in #(.F(f)) u_g0 (.ck(ck), .rs(rst), .i(gin[j][275:0]),   .o(gin[j+1][275:0]));
                dsdv_sx_rly_in #(.F(f)) u_g1 (.ck(ck), .rs(rst), .i(gin[j][551:276]), .o(gin[j+1][551:276]));
                dsdv_sx_rly_in #(.F(f)) u_s  (.ck(ck), .rs(rst), .i(sin[j]),          .o(sin[j+1]));
            end
            assign lgi[f] = gin[NR][RW:0]; assign lsi[f] = sin[NR][RSW:0];
            // ---- OUT stations (A, B): leaf -> face f; NR + 1 deep ----
            wire [551:0] gout [0:NR+1]; wire [275:0] sout [0:NR+1];
            assign gout[0] = {18'd0, lgo[f]};
            assign sout[0] = {6'd0, lso[f]};
            for (j = 0; j <= NR; j = j + 1) begin : g_ab
                dsdv_sx_rly_out #(.F(f)) u_g0 (.ck(ck), .rs(rst), .i(gout[j][275:0]),   .o(gout[j+1][275:0]));
                dsdv_sx_rly_out #(.F(f)) u_g1 (.ck(ck), .rs(rst), .i(gout[j][551:276]), .o(gout[j+1][551:276]));
                dsdv_sx_rly_out #(.F(f)) u_s  (.ck(ck), .rs(rst), .i(sout[j]),          .o(sout[j+1]));
            end
        end
        dsdv_svc_sx_row #(.MUT(MUT), .FX(FX), .F12(F12)) u_row (.ck(ck), .rst(rst), .sid(sid),
            .l_i({l_v, g_row(l_d, r)}),
            .gi_n(lgi[0]), .gi_e(lgi[1]), .gi_s(lgi[2]), .gi_w(lgi[3]),
            .go_n(lgo[0]), .go_e(lgo[1]), .go_s(lgo[2]), .go_w(lgo[3]),
            .si_n(lsi[0]), .si_e(lsi[1]), .si_s(lsi[2]), .si_w(lsi[3]),
            .so_n(lso[0]), .so_e(lso[1]), .so_s(lso[2]), .so_w(lso[3]),
            .rt_o(rrt[r]), .t_o(rt[r]), .fault(rflt[r]));
        assign rrt_v[r] = rrt[r][RW]; assign rt_vv[r] = rt[r][38];
        assign t_tag[5*r +: 5] = rt[r][37:33]; assign t_f[r] = rt[r][32]; assign t_y[32*r +: 32] = rt[r][31:0];
        assign rt_d[2112 + 5*r +: 5] = rrt[r][RW-1 -: 5];
        assign rt_d[64 + 512*r +: 512] = rrt[r][16 +: 512];
        assign rt_d[16*r +: 16] = rrt[r][15:0];
    end endgenerate
    // slice-face lanes (pure wiring of the 4 rows' last OUT stations)
    generate for (f = 0; f < 4; f = f + 1) begin : g_face
        assign go_v[f] = g_r[0].g_f[f].gout[NR+1][RW] & g_r[1].g_f[f].gout[NR+1][RW] & g_r[2].g_f[f].gout[NR+1][RW]
                         & g_r[3].g_f[f].gout[NR+1][RW];
        assign so_v[f] = g_r[0].g_f[f].sout[NR+1][RSW] & g_r[1].g_f[f].sout[NR+1][RSW] & g_r[2].g_f[f].sout[NR+1][RSW]
                         & g_r[3].g_f[f].sout[NR+1][RSW];
        for (r = 0; r < 4; r = r + 1) begin : g_rr
            wire [RW-1:0] gd = g_r[r].g_f[f].gout[NR+1][RW-1:0];
            wire [RSW-1:0] sd = g_r[r].g_f[f].sout[NR+1][RSW-1:0];
            assign go_d[W*f + 2112 + 5*r +: 5] = gd[RW-1 -: 5];
            assign go_d[W*f + 64 + 512*r +: 512] = gd[16 +: 512];
            assign go_d[W*f + 16*r +: 16] = gd[15:0];
            assign so_d[SW*f + 1056 + 5*r +: 5] = sd[RSW-1 -: 5];
            for (j = 0; j < 8; j = j + 1) begin : g_h
                assign so_d[SW*f + 132*j + 128 + r] = sd[33*j + 32];
                assign so_d[SW*f + 132*j + 32*r +: 32] = sd[33*j +: 32];
            end
        end
    end endgenerate
    // the 4 rows share the static schedule, so their valids are equal by construction.  The monolith-format ports carry
    // ONE valid: it is the AND of the 4 rows' (a row that disagreed drops the beat and the bench counts it); physically
    // each row lane keeps its own valid bit.
    assign rt_v = &rrt_v;
    assign t_v = &rt_vv;
    assign fault = |rflt;
endmodule

// face f in {N, E, S, W} = 0..3 -> the closed dsfd_dvrly_276 master named by its lane direction <in face><out face>
module dsdv_sx_rly_in #(parameter integer F = 0) (input wire ck, input wire rs, input wire [275:0] i, output wire [275:0] o);
    // IN lane through face F travels away from face F: N in -> NS, E in -> EW, S in -> SN, W in -> WE
    generate
        if (F == 0) begin : g_ns dsfd_dvrly_276_NS u (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o()); end
        else if (F == 1) begin : g_ew dsfd_dvrly_276_EW u (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o()); end
        else if (F == 2) begin : g_sn dsfd_dvrly_276_SN u (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o()); end
        else begin : g_we dsfd_dvrly_276_WE u (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o()); end
    endgenerate
endmodule
module dsdv_sx_rly_out #(parameter integer F = 0) (input wire ck, input wire rs, input wire [275:0] i, output wire [275:0] o);
    // OUT lane through face F travels toward face F: N out -> SN, E out -> WE, S out -> NS, W out -> EW
    generate
        if (F == 0) begin : g_sn dsfd_dvrly_276_SN u (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o()); end
        else if (F == 1) begin : g_we dsfd_dvrly_276_WE u (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o()); end
        else if (F == 2) begin : g_ns dsfd_dvrly_276_NS u (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o()); end
        else begin : g_ew dsfd_dvrly_276_EW u (.ck(ck), .rs(rs), .i(i), .o(o), .ck_o()); end
    endgenerate
endmodule
