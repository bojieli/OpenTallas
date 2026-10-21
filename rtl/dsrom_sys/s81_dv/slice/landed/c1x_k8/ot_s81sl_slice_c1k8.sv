`timescale 1ns/1ps
// S81-SLICERTL (10-20): PARAMETER-FREE top of the landed C1 slice parent = ot_s81sl_slice_c1x_k8_lp with the kit
// parameters of s81dv_slice_lp_k8a / _k8b (DLK 1 / 1 / 4 / 1 / 1 = landed leaves 0, 1, 3, 4 use DL - (E + 1) relay stages,
// leaf 2 shares region C; DLF 0; DR 6, DX 6, VQ_XMEM 2, VS_MUT 0, MUT 0 = the lp.py defaults).  The die binds THIS module
// for the C1 slice master dsdv_slice (HB 0): a hard view whose top carries no parameters, so the die / bind netlist
// instantiates it without #() and elaborates exactly the closed netlist.  Ports = the lp top's (C1 still lists bi / bo:
// bi unread, bo = 0, die mode_unused 'hb0' as for ot_s81sl_slice); region clocks ck_C / ck_L0 / ck_L1 / ck_L3 / ck_L4 are
// separate roots (one die regional root each, or the slice's die region root on all five: bind clk ck_C + clk_extra).
// Cycle relation to ot_s81sl_slice #(.HB(0)): the lp record (results/rtl/drive_s81_slicep_1020/c1x_k8) offsets
// (reset +RB, per-port off_in / off_out, leaf fault +3); the kit is the same elaboration with params {}.
module ot_s81sl_slice_c1k8 (
    input  wire            rst_n,
    input  wire [3:0]      sid,
    input  wire [1103:0]   ri_w, input wire [1103:0] ri_e, output wire [1103:0] ro_e, output wire [1103:0] ro_w,
    input  wire [275:0]    vi,   output wire [275:0] vo,
    input  wire [1103:0]   bi,   output wire [512:0] bo,
    output wire [4415:0]   xc,
    input  wire [559:0]    rt,
    output wire [15:0]     ck_line,
    output wire [1:0]      ck_v,
    output wire [15:0]     ck_xc,
    output wire [7:0]      ck_rt,
    output wire            fault,
    input  wire            ck_C,
    input  wire            ck_L0,
    input  wire            ck_L1,
    input  wire            ck_L3,
    input  wire            ck_L4
);
    ot_s81sl_slice_c1x_k8_lp #(.DLK0(1), .DLK1(1), .DLK2(4), .DLK3(1), .DLK4(1),
        .DLF0(0), .DLF1(0), .DLF2(0), .DLF3(0), .DLF4(0), .DR(6), .DX(6), .VQ_XMEM(2), .VS_MUT(0), .MUT(0)) u_lp (
        .rst_n(rst_n), .sid(sid), .ri_w(ri_w), .ri_e(ri_e), .ro_e(ro_e), .ro_w(ro_w), .vi(vi), .vo(vo), .bi(bi), .bo(bo),
        .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc), .ck_rt(ck_rt), .fault(fault),
        .ck_C(ck_C), .ck_L0(ck_L0), .ck_L1(ck_L1), .ck_L3(ck_L3), .ck_L4(ck_L4));
endmodule
