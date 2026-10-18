`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-BK (2026-10-17): dsdv_bk_sel, the S81-DV index selector unit (plan p4h block bk_sel, column 4 V rung:
// s_4S <-> bk_sel <-> seqhost <-> s_4N), as THREE stacked near-square leaves, each flop-first / flop-last with its own
// regional clock root, abutted N-S (every leaf-to-leaf wire <= 50 um, registered at both ends):
//
//   leaf 0 (S, by s_4S)  dsdv_bksel_lq   quarter tiles 0 (SW) and 1 (SE): two UNCHANGED dsfd_selt_q2 (closed
//                                         configuration: SAFE line memory, CMP_RETIME, PIPE2, QIO, ILD, FRPR)
//   leaf 1 (middle)      dsdv_bksel_lm   the V-rung stop ot_dsdv_vstop (rung on the E / W faces), the V ingress
//                                         dsdv_bk_vin (4 lane words), the UNCHANGED select control dsfd_selt_c (MRG_PIPE,
//                                         RQPIPE, SLAT 4, XDX 1) and the V egress dsdv_bk_vout (drain windows)
//   leaf 2 (N)           dsdv_bksel_lq   quarter tiles 2 (NW) and 3 (NE) (same master as leaf 0)
//
// The quarter <-> control bundles (lane 288, command 66, credit 1, status 865, beats 354 per quarter) cross the leaf faces
// exactly as they crossed the closed tiles' abutted faces in ot_s81ph_sel_t (pin flop on each side, no die station), so
// the select arithmetic, its order, replays and fault bits are the native ones (the control's XD / SLAT / XDX waits
// already cover this hop).  The quarter -> control credit loop is INTERNAL to the unit (fixed 2-edge hop each way,
// deterministic, never visible on a unit port): the unit's ports carry no credit / ready / back-pressure.  The old
// slab's ctrl endpoint (dsfd_bk_selector_c / _c1: c_cmd / c_done job queue) is dropped: the selector is armed in band
// by its lane headers, and its DONE / REP / FAULT words leave on V in compiled drain windows like every other word.
// Lane word compaction across the leaf face: {fault, live, data[511:500], data[272:0], valid} = the only bits the quarter
// decoder ot_s81ph_sel_in reads.
// MUT (bench only) 1..4: dsdv_bk_vin / dsdv_bk_vout mutants (dsdv_bk_v.sv).
// ---------------------------------------------------------------------------------------------------------------------

// quarter leaf: two quarter tiles (a = lower index)
module dsdv_bksel_lq (
    input  wire [0:0]          ck,
    input  wire [0:0]          rst,
    input  wire [2*288-1:0]    ln,          // compact lane words {b, a}
    input  wire [2*66-1:0]     f_c,
    input  wire [1:0]          f_cr,
    output wire [2*865-1:0]    t_s,
    output wire [2*354-1:0]    t_o
);
    genvar g;
    generate for (g = 0; g < 2; g = g + 1) begin : g_q
        wire [287:0] c = ln[288 * g +: 288];
        wire [514:0] lane = {c[287], c[286], c[285:274], 227'd0, c[273:1], c[0]};
        dsfd_selt_q2 #(.DM(4), .CMP_RETIME(1), .PIPE2(1), .QIO(1), .ILD(1), .FRPR(1)) u_q (.ck(ck), .rst(rst), .lane(lane),
            .f_c(f_c[66 * g +: 66]), .f_cr(f_cr[g]), .t_s(t_s[865 * g +: 865]), .t_o(t_o[354 * g +: 354]));
    end endgenerate
endmodule

// middle leaf: vstop + V ingress + select control + V egress
module dsdv_bksel_lm #(
    parameter integer V   = 276,
    parameter integer MUT = 0
) (
    input  wire [0:0]          ck,
    input  wire [0:0]          rst,         // die reset net (active low)
    input  wire [7:0]          tap_k,       // straps (captured)
    input  wire [7:0]          sink_k,
    input  wire [2:0]          ik,
    input  wire [2:0]          ek,
    input  wire [7:0]          uid,
    input  wire [0:0]          eg_n,        // egress direction: 0 = southbound (vo_s), 1 = northbound (vo_n)
    input  wire [V-1:0]        vi_s,        // rung, S side
    output wire [V-1:0]        vo_s,
    input  wire [V-1:0]        vi_n,        // rung, N side
    output wire [V-1:0]        vo_n,
    // S face: quarter tiles 0 (SW) / 1 (SE) in leaf 0; N face: quarter tiles 2 (NW) / 3 (NE) in leaf 2
    output wire [2*288-1:0]    ln_s,        // compact lane words
    output wire [2*66-1:0]     tc_s,        // command bundles
    output wire [1:0]          tcr_s,       // landing credits (internal fixed-latency loop)
    input  wire [2*865-1:0]    fs_s,        // status bundles
    input  wire [2*354-1:0]    fo_s,        // selected beats
    output wire [2*288-1:0]    ln_n,
    output wire [2*66-1:0]     tc_n,
    output wire [1:0]          tcr_n,
    input  wire [2*865-1:0]    fs_n,
    input  wire [2*354-1:0]    fo_n,
    output reg  [0:0]          fault
);
    reg [1:0] rs;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rn = rs[1];
    reg [2:0] ik_c, ek_c; reg [7:0] uid_c; reg egn_c;
    always @(posedge ck[0]) begin ik_c <= ik; ek_c <= ek; uid_c <= uid; egn_c <= eg_n[0]; end
    wire dnv, dsv, inv_, isv; wire [V-1:0] dn, ds, ob; wire vs_f, vi_f, vo_f, ov;
    ot_dsdv_vstop #(.V(V)) u_vs (.clk(ck[0]), .rst_n(rn), .tap_k(tap_k), .sink_k(sink_k), .vi_s(vi_s), .vo_n(vo_n),
        .vi_n(vi_n), .vo_s(vo_s), .dl_nv(dnv), .dl_n(dn), .dl_sv(dsv), .dl_s(ds),
        .in_nv(ov && egn_c), .in_n(ob), .in_sv(ov && !egn_c), .in_s(ob), .fault(vs_f));
    wire [4*515-1:0] lw; wire drv; wire [7:0] drn, drd;
    dsdv_bk_vin #(.V(V), .MUT(MUT)) u_vin (.clk(ck[0]), .rst_n(rn), .ik(ik_c), .uid(uid_c), .dl_nv(dnv), .dl_n(dn),
        .dl_sv(dsv), .dl_s(ds), .lanes(lw), .dr_v(drv), .dr_n(drn), .dr_d(drd), .fault(vi_f));
    wire [4*288-1:0] ln;
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_l
        wire [514:0] w = lw[515 * g +: 515];
        assign ln[288 * g +: 288] = {w[514], w[513], w[512:501], w[273:1], w[0]};
    end endgenerate
    assign ln_s = ln[0 +: 576]; assign ln_n = ln[576 +: 576];
    wire [513:0] vd; wire vf_unused;
    dsfd_selt_c #(.SEARCH_PIPE(1), .DM(4), .PACE(2), .MRG_PIPE(1), .RQPIPE(1), .SLAT(4), .XDX(1)) u_c (.ck(ck), .rst(rst),
        .f_s({fs_n, fs_s}), .t_c({tc_n, tc_s}), .f_o({fo_n, fo_s}), .t_cr({tcr_n, tcr_s}), .vd(vd), .vf(vf_unused));
    dsdv_bk_vout #(.V(V), .MUT(MUT)) u_vout (.clk(ck[0]), .rst_n(rn), .ek(ek_c), .w_v(vd[1]), .w_d(vd[513:2]),
        .dr_v(drv), .dr_n(drn), .dr_d(drd), .o_v(ov), .o_b(ob), .fault(vo_f));
    always @(posedge ck[0] or negedge rn) if (!rn) fault <= 1'b0; else fault <= vs_f | vi_f | vo_f;
endmodule

// the unit: leaf 0 (S) - leaf 1 (middle, rung) - leaf 2 (N)
module dsdv_bk_sel #(
    parameter integer V   = 276,
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    tap_k,
    input  wire [7:0]    sink_k,
    input  wire [2:0]    ik,
    input  wire [2:0]    ek,
    input  wire [7:0]    uid,
    input  wire          eg_n,
    input  wire [V-1:0]  vi_s,
    output wire [V-1:0]  vo_n,
    input  wire [V-1:0]  vi_n,
    output wire [V-1:0]  vo_s,
    output wire          fault
);
    wire [4*288-1:0] ln; wire [4*66-1:0] tc; wire [3:0] tcr; wire [4*865-1:0] fs; wire [4*354-1:0] fo;
    dsdv_bksel_lq u_l0 (.ck(clk), .rst(rst_n), .ln(ln[0 +: 576]), .f_c(tc[0 +: 132]), .f_cr(tcr[1:0]),
        .t_s(fs[0 +: 1730]), .t_o(fo[0 +: 708]));
    dsdv_bksel_lm #(.V(V), .MUT(MUT)) u_l1 (.ck(clk), .rst(rst_n), .tap_k(tap_k), .sink_k(sink_k), .ik(ik), .ek(ek),
        .uid(uid), .eg_n(eg_n), .vi_s(vi_s), .vo_s(vo_s), .vi_n(vi_n), .vo_n(vo_n),
        .ln_s(ln[0 +: 576]), .tc_s(tc[0 +: 132]), .tcr_s(tcr[1:0]), .fs_s(fs[0 +: 1730]), .fo_s(fo[0 +: 708]),
        .ln_n(ln[576 +: 576]), .tc_n(tc[132 +: 132]), .tcr_n(tcr[3:2]), .fs_n(fs[1730 +: 1730]), .fo_n(fo[708 +: 708]),
        .fault(fault));
    dsdv_bksel_lq u_l2 (.ck(clk), .rst(rst_n), .ln(ln[576 +: 576]), .f_c(tc[132 +: 132]), .f_cr(tcr[3:2]),
        .t_s(fs[1730 +: 1730]), .t_o(fo[708 +: 708]));
endmodule
