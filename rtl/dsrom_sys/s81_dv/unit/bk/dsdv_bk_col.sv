`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-BK (2026-10-17): dsdv_bk_col, the S81-DV row collector unit (plan p4h block bk_col, column 1 V rung:
// s_1S <-> bk_col <-> s_1N).  ONE near-square hardened leaf (the leaf IS the unit; its own regional clock root):
//
//   the V-rung stop ot_dsdv_vstop (rung lanes on the W / E faces: northbound W, southbound E, as dv_plan's tvN / tvS),
//   the V ingress dsdv_bk_vin (4 lane words), four UNCHANGED lane tiles dsfd_colt_lane (RING 1: the closed ring-pointer
//   frame FIFO, 2 x 256x256 macros each, DEPTH 256), the UNCHANGED frame-atomic merger dsfd_colt_mrg (DM 12, PACE 2)
//   and the V egress dsdv_bk_vout (128 x 512 buffer, compiled drain windows).
//
// Why one leaf, not the plan's 6 x (680 x 697): the measured content is ~0.12 mm2 (10 macros 64.6k um2 + ~50k um2 std,
// closed tile areas), 4% of the 2.84 mm2 outline; split leaves would each be under the 35% fill floor and add a 4.1-kb
// leaf face (lane tiles <-> merger) for nothing.  Its only ports are the rung (2 x 2 x 276) and straps.
// The lane tile <-> merger bundles are internal (pin flop on each side, no station; ot_s81ph_col_t had HOPS 7 here, DM
// 12 covers the shorter round trip), so frames, per-stack order, the DONE join and the fault bits are the native ones.
// The lane -> merger credit loop is INTERNAL (fixed hop, deterministic, never on a unit port); the unit ports carry no
// credit / ready / back-pressure.  The old ctrl endpoint (dsfd_bk_collector_c / _c1: c_cmd / c_done job queue) is
// dropped: words, DONE and FAULT leave on V in compiled drain windows.  MUT (bench only) 1..4: dsdv_bk_v.sv mutants.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_bk_col #(
    parameter integer V   = 276,
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,       // die reset net (active low)
    input  wire [7:0]    tap_k,       // straps (captured)
    input  wire [7:0]    sink_k,
    input  wire [2:0]    ik,
    input  wire [2:0]    ek,
    input  wire [7:0]    uid,
    input  wire          eg_n,        // egress direction: 0 = southbound (vo_s), 1 = northbound (vo_n)
    input  wire [V-1:0]  vi_s,        // rung, S side (northbound arrivals)
    output wire [V-1:0]  vo_n,
    input  wire [V-1:0]  vi_n,        // rung, N side (southbound arrivals)
    output wire [V-1:0]  vo_s,
    output reg           fault
);
    reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rn = rs[1];
    reg [2:0] ik_c, ek_c; reg [7:0] uid_c; reg egn_c;
    always @(posedge clk) begin ik_c <= ik; ek_c <= ek; uid_c <= uid; egn_c <= eg_n; end
    wire dnv, dsv; wire [V-1:0] dn, ds, ob; wire vs_f, vi_f, vo_f, ov;
    ot_dsdv_vstop #(.V(V)) u_vs (.clk(clk), .rst_n(rn), .tap_k(tap_k), .sink_k(sink_k), .vi_s(vi_s), .vo_n(vo_n),
        .vi_n(vi_n), .vo_s(vo_s), .dl_nv(dnv), .dl_n(dn), .dl_sv(dsv), .dl_s(ds),
        .in_nv(ov && egn_c), .in_n(ob), .in_sv(ov && !egn_c), .in_s(ob), .fault(vs_f));
    wire [4*515-1:0] cl; wire drv; wire [7:0] drn, drd;
    dsdv_bk_vin #(.V(V), .MUT(MUT)) u_vin (.clk(clk), .rst_n(rn), .ik(ik_c), .uid(uid_c), .dl_nv(dnv), .dl_n(dn),
        .dl_sv(dsv), .dl_s(ds), .lanes(cl), .dr_v(drv), .dr_n(drn), .dr_d(drd), .fault(vi_f));
    wire [3:0] tcr; wire [4*513-1:0] fw; wire [4*4-1:0] ff;
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_l       // lane 0 SW, 1 SE, 2 NW, 3 NE
        dsfd_colt_lane #(.DEPTH(256), .RING(1), .DM(12)) u_l (.ck(clk), .rst(rst_n), .c_in(cl[515 * g +: 515]),
            .f_cr(tcr[g]), .t_w(fw[513 * g +: 513]), .t_f(ff[4 * g +: 4]));
    end endgenerate
    wire [513:0] vd; wire vf_unused;
    dsfd_colt_mrg #(.DM(12), .PACE(2)) u_m (.ck(clk), .rst(rst_n), .f_w(fw), .f_f(ff), .t_cr(tcr), .vd(vd), .vf(vf_unused));
    dsdv_bk_vout #(.V(V), .MUT(MUT)) u_vout (.clk(clk), .rst_n(rn), .ek(ek_c), .w_v(vd[1]), .w_d(vd[513:2]),
        .dr_v(drv), .dr_n(drn), .dr_d(drd), .o_v(ov), .o_b(ob), .fault(vo_f));
    always @(posedge clk or negedge rn) if (!rn) fault <= 1'b0; else fault <= vs_f | vi_f | vo_f;
endmodule
