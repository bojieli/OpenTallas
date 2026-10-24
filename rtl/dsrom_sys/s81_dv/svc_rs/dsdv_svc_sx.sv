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
// S81U-SVCX4 (2026-10-17): the one-row leaf (14.4k sinks) missed the clock rule (TT 326..415 ps / 89 ps spread), so the
// leaf is now HALF a row.  The slice is:
//   * 8 x dsdv_svc_sx_hrow, the hardened-once CENTRE LEAF (strap hb): row r, half b = heads 2 i + b of that row
//     (8 qaddf + the gather / scatter crossbars), every pin registered.  Rows never mix, heads never mix in the gather,
//     and the scatter's head-slot shifts keep slot parity except at the pair nodes, which no longer shift (the leaf taps
//     local slot 0 of half head[0]; see dsdv_svc_sx_hrow), so nothing crosses halves and the result is bit-identical;
//   * closed relay stations dsfd_dvrly_276_<in><out> (S81-B: CLOSED, native PASS) on every face lane:
//     per face and row, gather = 2 stations (one per half, 270 b each), scatter = 1 station (the 2 halves' 138 b);
//     OUT lanes NR + 1 stations deep (A at ~1/4 of the hop, B at the slice edge), IN lanes NR deep (C at ~3/4).
//     NR = 1 keeps the monolith's 5-cycle hop (centre reg, A, B | C, leaf pin flop): ZERO added cycles, the role ROM
//     offsets are unchanged.
//     Hop geometry (p4h 1,222 x 1,338 um slices): leaf pin -> A -> B -> C -> leaf pin spans at most one slice pitch
//     (pins at the slice centre line, the inner faces of the leaf cluster), 4 segments of <= 335 um <= 405.
// The slice-face ports keep the monolith's lane format and widths (pure wiring); below a pair node the scatter lane's slot
// order differs from the monolith's (internal to the exchange).  Output glue: valids AND, fault OR, the two halves' head
// tap OR (the non-owning half holds 0).  Relay spare bits (6 per gather station) are constant 0.
// MUT (bench negative controls): bit 0 = the right operand's flags are not ORed in; bit 1 = right scatter split off by
// one head slot.  DSDV_SX_MUT_ORDER (define) = role ROM of a tree whose tiles 0..3 sum as a chain (((t0+t1)+t2)+t3).
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_svc_sx #(
    parameter integer MUT = 0,
    parameter integer NR = 1,              // relay stations per hop half (IN: NR, OUT: NR + 1)
    parameter integer FX = 5,
    parameter integer F12 = 1,
    // S81-P9-FACE (10-23): gather / scatter face masks (bit f = face N / E / S / W; svc_rs_faces.py from the role ROM).
    // A face whose bit is 0 has no relay station: its IN lanes reach the half rows as constant 0 (the role ROM never
    // selects them, so the hardened half row reads nothing there) and its OUT lanes are constant 0 (port variant: absent).
    parameter logic [3:0] FM_GI = 4'hf, FM_GO = 4'hf, FM_SI = 4'hf, FM_SO = 4'hf
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
    localparam integer W = 2132, SW = 1076, HW = 269, HSW = 137;
    genvar r, f, j, b;
    // beat <-> half-row lane (pure wiring): half bb of row rr = heads h = 2 i + bb
    function automatic [HW-1:0] g_half(input [W-1:0] x, input integer rr, input integer bb);
        g_half[HW-1 -: 5] = x[2112 + 5*rr +: 5];
        for (int i = 0; i < 8; i++) begin
            g_half[8 + 32*i +: 32] = x[64 + 512*rr + 32*(2*i + bb) +: 32];
            g_half[i] = x[16*rr + 2*i + bb];
        end
    endfunction
    function automatic [HSW-1:0] s_half(input [SW-1:0] x, input integer rr, input integer bb);
        s_half[HSW-1 -: 5] = x[1056 + 5*rr +: 5];
        for (int i = 0; i < 4; i++) s_half[33*i +: 33] = {x[132*(2*i + bb) + 128 + rr], x[132*(2*i + bb) + 32*rr +: 32]};
    endfunction
    wire [7:0] rrt_v, rt_vv, rflt;

    generate for (r = 0; r < 4; r = r + 1) begin : g_r
        // leaf face ports, index 4 b + f (half b, face f = N, E, S, W)
        wire [HW:0] lgi [0:7], lgo [0:7]; wire [HSW:0] lsi [0:7], lso [0:7];
        wire [HW:0] rrt [0:1]; wire [38:0] trt [0:1]; wire [1:0] rf;
        for (f = 0; f < 4; f = f + 1) begin : g_f
            // ---- IN stations (C): face f -> leaf; NR deep.  Gather: one station per half; scatter: the 2 halves share one
            wire [551:0] gin [0:NR]; wire [275:0] sin [0:NR];
            if (FM_GI[f]) begin : g_gi
                assign gin[0] = {6'd0, gi_v[f], g_half(gi_d[W*f +: W], r, 1), 6'd0, gi_v[f], g_half(gi_d[W*f +: W], r, 0)};
                for (j = 0; j < NR; j = j + 1) begin : g_c
                    dsdv_sx_rly_in #(.F(f)) u_g0 (.ck(ck), .rs(rst), .i(gin[j][275:0]),   .o(gin[j+1][275:0]));
                    dsdv_sx_rly_in #(.F(f)) u_g1 (.ck(ck), .rs(rst), .i(gin[j][551:276]), .o(gin[j+1][551:276]));
                end
            end else begin : g_gi0
                for (j = 0; j <= NR; j = j + 1) begin : g_z assign gin[j] = '0; end
            end
            if (FM_SI[f]) begin : g_si
                assign sin[0] = {si_v[f], s_half(si_d[SW*f +: SW], r, 1), si_v[f], s_half(si_d[SW*f +: SW], r, 0)};
                for (j = 0; j < NR; j = j + 1) begin : g_c
                    dsdv_sx_rly_in #(.F(f)) u_s  (.ck(ck), .rs(rst), .i(sin[j]),          .o(sin[j+1]));
                end
            end else begin : g_si0
                for (j = 0; j <= NR; j = j + 1) begin : g_z assign sin[j] = '0; end
            end
            assign lgi[f] = gin[NR][HW:0]; assign lgi[4 + f] = gin[NR][276 +: HW + 1];
            assign lsi[f] = sin[NR][HSW:0]; assign lsi[4 + f] = sin[NR][HSW + 1 +: HSW + 1];
            // ---- OUT stations (A, B): leaf -> face f; NR + 1 deep ----
            wire [551:0] gout [0:NR+1]; wire [275:0] sout [0:NR+1];
            assign gout[0] = {6'd0, lgo[4 + f], 6'd0, lgo[f]};
            assign sout[0] = {lso[4 + f], lso[f]};
            if (FM_GO[f]) begin : g_go
                for (j = 0; j <= NR; j = j + 1) begin : g_ab
                    dsdv_sx_rly_out #(.F(f)) u_g0 (.ck(ck), .rs(rst), .i(gout[j][275:0]),   .o(gout[j+1][275:0]));
                    dsdv_sx_rly_out #(.F(f)) u_g1 (.ck(ck), .rs(rst), .i(gout[j][551:276]), .o(gout[j+1][551:276]));
                end
            end else begin : g_go0
                for (j = 1; j <= NR + 1; j = j + 1) begin : g_z assign gout[j] = '0; end
            end
            if (FM_SO[f]) begin : g_so
                for (j = 0; j <= NR; j = j + 1) begin : g_ab
                    dsdv_sx_rly_out #(.F(f)) u_s  (.ck(ck), .rs(rst), .i(sout[j]),          .o(sout[j+1]));
                end
            end else begin : g_so0
                for (j = 1; j <= NR + 1; j = j + 1) begin : g_z assign sout[j] = '0; end
            end
        end
        for (b = 0; b < 2; b = b + 1) begin : g_h
            `ifndef OT_SVC_RS_HARD
            dsdv_svc_sx_hrow #(.MUT(MUT), .FX(FX), .F12(F12)) u_hrow (
`else
            dsdv_svc_sx_hrow u_hrow (   // hardened view: no overrides (defaults = the hardened config)
`endif
            .ck(ck), .rst(rst), .sid(sid), .hb(b[0]),
                .l_i({l_v, g_half(l_d, r, b)}),
                .gi_n(lgi[4*b + 0]), .gi_e(lgi[4*b + 1]), .gi_s(lgi[4*b + 2]), .gi_w(lgi[4*b + 3]),
                .go_n(lgo[4*b + 0]), .go_e(lgo[4*b + 1]), .go_s(lgo[4*b + 2]), .go_w(lgo[4*b + 3]),
                .si_n(lsi[4*b + 0]), .si_e(lsi[4*b + 1]), .si_s(lsi[4*b + 2]), .si_w(lsi[4*b + 3]),
                .so_n(lso[4*b + 0]), .so_e(lso[4*b + 1]), .so_s(lso[4*b + 2]), .so_w(lso[4*b + 3]),
                .rt_o(rrt[b]), .t_o(trt[b]), .fault(rf[b]));
            assign rrt_v[2*r + b] = rrt[b][HW]; assign rflt[2*r + b] = rf[b];
            for (j = 0; j < 8; j = j + 1) begin : g_rh
                assign rt_d[64 + 512*r + 32*(2*j + b) +: 32] = rrt[b][8 + 32*j +: 32];
                assign rt_d[16*r + 2*j + b] = rrt[b][j];
            end
        end
        // the head tap: only the half that owns this slice's head (head bit 0) drives it, the other holds 0
        wire [38:0] rt = trt[0] | trt[1];
        assign rt_vv[2*r] = rt[38]; assign rt_vv[2*r + 1] = rt[38];
        assign t_tag[5*r +: 5] = rt[37:33]; assign t_f[r] = rt[32]; assign t_y[32*r +: 32] = rt[31:0];
        // the tag part rides in both halves (each checks its own operands); the face / root beat takes half 0's
        assign rt_d[2112 + 5*r +: 5] = rrt[0][HW-1 -: 5];
    end endgenerate
    // slice-face lanes (pure wiring of the 8 half rows' last OUT stations)
    generate for (f = 0; f < 4; f = f + 1) begin : g_face
        wire [7:0] gv, sv;
        for (r = 0; r < 4; r = r + 1) begin : g_rr
            wire [HW:0] g0 = g_r[r].g_f[f].gout[NR+1][HW:0], g1 = g_r[r].g_f[f].gout[NR+1][276 +: HW + 1];
            wire [HSW:0] s0 = g_r[r].g_f[f].sout[NR+1][HSW:0], s1 = g_r[r].g_f[f].sout[NR+1][HSW + 1 +: HSW + 1];
            assign gv[2*r] = g0[HW]; assign gv[2*r + 1] = g1[HW]; assign sv[2*r] = s0[HSW]; assign sv[2*r + 1] = s1[HSW];
            assign go_d[W*f + 2112 + 5*r +: 5] = g0[HW-1 -: 5];
            assign so_d[SW*f + 1056 + 5*r +: 5] = s0[HSW-1 -: 5];
            for (j = 0; j < 8; j = j + 1) begin : g_h
                assign go_d[W*f + 64 + 512*r + 32*(2*j) +: 32] = g0[8 + 32*j +: 32];
                assign go_d[W*f + 64 + 512*r + 32*(2*j + 1) +: 32] = g1[8 + 32*j +: 32];
                assign go_d[W*f + 16*r + 2*j] = g0[j]; assign go_d[W*f + 16*r + 2*j + 1] = g1[j];
            end
            for (j = 0; j < 4; j = j + 1) begin : g_s
                assign so_d[SW*f + 132*(2*j) + 128 + r] = s0[33*j + 32];
                assign so_d[SW*f + 132*(2*j) + 32*r +: 32] = s0[33*j +: 32];
                assign so_d[SW*f + 132*(2*j + 1) + 128 + r] = s1[33*j + 32];
                assign so_d[SW*f + 132*(2*j + 1) + 32*r +: 32] = s1[33*j +: 32];
            end
        end
        assign go_v[f] = &gv; assign so_v[f] = &sv;
    end endgenerate
    // the 8 half rows share the static schedule, so their valids are equal by construction.  The monolith-format ports
    // carry ONE valid: it is the AND of the 8 halves' (a half that disagreed drops the beat and the bench counts it);
    // physically each half-row lane keeps its own valid bit.
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
