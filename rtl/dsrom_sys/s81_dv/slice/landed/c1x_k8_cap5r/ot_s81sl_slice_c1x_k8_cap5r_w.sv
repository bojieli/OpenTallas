`timescale 1ns/1ps
// S81-SLICE/PARENT 10-21: PARAMETER-FREE die-bind wrapper of ot_s81sl_slice_c1x_k8_cap5r_lp (the hardened kit top s81dv_slice_lp_k8*):
// the kit parameters (DLK 1/1/4/1/1, DLF 0, DR 6, DX 6, VQ_XMEM 2, VS_MUT 0, MUT 0) fixed here, so the die binds one
// name with no paramod renaming.  Region clocks stay separate inputs (C, L0, L1, L3, L4, CAP_RT/CW/CE/RN/RS): the die
// feeds each from its own regional root (landed-regions standard); never tie them together in a die.
module ot_s81sl_slice_c1x_k8_cap5r_w #(parameter [19:0] LF_CS_HI_D = 20'h22222, parameter [19:0] LF_CS_HI_GS = 20'h22222, parameter [19:0] LF_CS_HO_D = 20'h22222, parameter [19:0] LF_CS_HO_GS = 20'h22222, parameter [19:0] LF_CS_H_G = 20'h44444, parameter [19:0] LF_CS_VNI_D = 20'h00000, parameter [19:0] LF_CS_VNO_D = 20'h00000, parameter [19:0] LF_CS_Y_D = 20'h00000, parameter [19:0] LF_CS_U_D = 20'h00000, parameter [19:0] LF_CS_SW_D = 20'h00000, parameter [19:0] LF_CS_SWR_D = 20'h00000, parameter [19:0] LF_CS_RA_D = 20'h00000, parameter [19:0] LF_CS_RAR_D = 20'h00000, parameter [19:0] LF_CS_VE_D = 20'h00000, parameter [19:0] LF_CS_VER_D = 20'h00000, parameter [19:0] LF_CS_PVS_D = 20'h00000, parameter [19:0] LF_CS_VSP_D = 20'h00000) (
    input wire rst_n,
    input wire [3:0] sid,
    input wire [1103:0] ri_w,
    input wire [1103:0] ri_e,
    output wire [1103:0] ro_e,
    output wire [1103:0] ro_w,
    input wire [275:0] vi,
    output wire [275:0] vo,
    input wire [1103:0] bi,
    output wire [512:0] bo,
    output wire [4415:0] xc,
    input wire [559:0] rt,
    output wire [15:0] ck_line,
    output wire [1:0] ck_v,
    output wire [15:0] ck_xc,
    output wire [7:0] ck_rt,
    output wire fault,

    input wire ck_CAP_RT, ck_CAP_CW, ck_CAP_CE, ck_CAP_RN, ck_CAP_RS,
    input wire ck_C,
    input wire ck_L0,
    input wire ck_L1,
    input wire ck_L3,
    input wire ck_L4
);
    ot_s81sl_slice_c1x_k8_cap5r_lp #(.DLK0(1), .DLK1(1), .DLK2(4), .DLK3(1), .DLK4(1), .DLF0(0), .DLF1(0), .DLF2(0), .DLF3(0), .DLF4(0), .LF_CS_HI_D(LF_CS_HI_D), .LF_CS_HI_GS(LF_CS_HI_GS), .LF_CS_HO_D(LF_CS_HO_D), .LF_CS_HO_GS(LF_CS_HO_GS), .LF_CS_H_G(LF_CS_H_G), .LF_CS_VNI_D(LF_CS_VNI_D), .LF_CS_VNO_D(LF_CS_VNO_D), .LF_CS_Y_D(LF_CS_Y_D), .LF_CS_U_D(LF_CS_U_D), .LF_CS_SW_D(LF_CS_SW_D), .LF_CS_SWR_D(LF_CS_SWR_D), .LF_CS_RA_D(LF_CS_RA_D), .LF_CS_RAR_D(LF_CS_RAR_D), .LF_CS_VE_D(LF_CS_VE_D), .LF_CS_VER_D(LF_CS_VER_D), .LF_CS_PVS_D(LF_CS_PVS_D), .LF_CS_VSP_D(LF_CS_VSP_D)) u_lp (.rst_n(rst_n), .sid(sid), .ri_w(ri_w), .ri_e(ri_e), .ro_e(ro_e), .ro_w(ro_w), .vi(vi), .vo(vo), .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc), .ck_rt(ck_rt), .fault(fault), .ck_CAP_RT(ck_CAP_RT), .ck_CAP_CW(ck_CAP_CW), .ck_CAP_CE(ck_CAP_CE), .ck_CAP_RN(ck_CAP_RN), .ck_CAP_RS(ck_CAP_RS), .ck_C(ck_C), .ck_L0(ck_L0), .ck_L1(ck_L1), .ck_L3(ck_L3), .ck_L4(ck_L4));
endmodule
