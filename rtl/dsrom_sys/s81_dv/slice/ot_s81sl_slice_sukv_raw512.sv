`timescale 1ns/1ps
// Exact configured SUKV source successor; external slice ABI preserved.
// Raw CN/IK/pool source at 75c077ec9; optional hardened RQ is not selected.
// Distinct physical master prevents a default-off ot_s81sl_slice view from qualifying KV_ENABLE1.
// UNBOUND: native/full-slice physical qualification and producer/transport programme remain owed.
module ot_s81sl_slice_sukv_raw512 (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      sid,
    // tier line (4 x 276-b lanes each) and V rung
    input  wire [1103:0]   ri_w, input wire [1103:0] ri_e, output wire [1103:0] ro_e, output wire [1103:0] ro_w,
    input  wire [275:0]    vi,   output wire [275:0] vo,
    // band port (C3)
    input  wire [1103:0]   bi,   output wire [512:0] bo,
    // x chains: 0 / 1 = down (W / E frame of row 1), 2 / 3 = up (row 2)
    output wire [4*1104-1:0] xc,
    // frame return lanes (cfifo rd)
    input  wire [8*70-1:0] rt,
    // forwarded clocks: line E in/out, W in/out (4 lanes each), V in/out, x chains (4 x 4), returns (8)
    output wire [15:0]     ck_line,
    output wire [1:0]      ck_v,
    output wire [15:0]     ck_xc,
    output wire [7:0]      ck_rt,
    output wire            fault
);
    ot_s81sl_slice #(.HB(0), .DL(4), .DR(6), .DX(6), .VQ_XMEM(2), .KV_ENABLE(1), .KV_CNIK(1), .KV_CP(1), .VS_MUT(0)) u_slice (
        .clk(clk),
        .rst_n(rst_n),
        .sid(sid),
        .ri_w(ri_w),
        .ri_e(ri_e),
        .ro_e(ro_e),
        .ro_w(ro_w),
        .vi(vi),
        .vo(vo),
        .bi(bi),
        .bo(bo),
        .xc(xc),
        .rt(rt),
        .ck_line(ck_line),
        .ck_v(ck_v),
        .ck_xc(ck_xc),
        .ck_rt(ck_rt),
        .fault(fault)
    );
endmodule
