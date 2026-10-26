`timescale 1ns/1ps
// PL-SLICE (10-18), BENCH ONLY: ot_s81sl_slice (C1 port list) implemented by the LANDED slice ot_s81sl_slice_c1x_lp, every
// region clock tied to clk, so the existing slice golden benches (tb_s81sl_slice_eng) run unchanged on the landed parent.
// Compile with the original ot_s81sl_slice.sv whose 'module ot_s81sl_slice #(' is renamed (tools/s81_slice/pl_slice/
// pl_slice_bench.sh does it).  DL must be 4: the landed leaves use DLK = DL - 3 (the landing's E + 1 edges).
module ot_s81sl_slice #(
    parameter integer HB = 0, parameter integer DL = 4, parameter integer DR = 6, parameter integer DX = 6,
    parameter integer VQ_XMEM = 2, parameter integer VS_MUT = 0
) (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire [1103:0] ri_w, input wire [1103:0] ri_e, output wire [1103:0] ro_e, output wire [1103:0] ro_w,
    input  wire [275:0] vi, output wire [275:0] vo, input wire [1103:0] bi, output wire [512:0] bo,
    output wire [4415:0] xc, input wire [559:0] rt,
    output wire [15:0] ck_line, output wire [1:0] ck_v, output wire [15:0] ck_xc, output wire [7:0] ck_rt, output wire fault
);
    ot_s81sl_slice_c1x_lp #(.DLK0(DL - 3), .DLK1(DL - 3), .DLK2(DL), .DLK3(DL - 3), .DLK4(DL - 3), .DR(DR), .DX(DX),
        .VQ_XMEM(VQ_XMEM), .VS_MUT(VS_MUT)) u_lp (.ck_C(clk), .ck_L0(clk), .ck_L1(clk), .ck_L3(clk), .ck_L4(clk), .rst_n(rst_n),
        .sid(sid), .ri_w(ri_w), .ri_e(ri_e), .ro_e(ro_e), .ro_w(ro_w), .vi(vi), .vo(vo), .bi(bi), .bo(bo), .xc(xc), .rt(rt),
        .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc), .ck_rt(ck_rt), .fault(fault));
`ifndef SYNTHESIS
    initial if (HB != 0) $fatal(1, "ot_s81sl_slice_lpwrap: C1 only");
`endif
endmodule
