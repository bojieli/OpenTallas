`timescale 1ns/1ps
// Wires-only native TP8 band/upper composition using direct_up4 quarter packing.
// All 55 child clock roots remain independent. lnk and upper selector arrival are
// explicit integration inputs: no unmeasured physical route age is invented.
// The b0 straps and unused nonzero-band upper return buses are architectural
// constants (ot_qfd_band_lanes selects upper returns only for b0).
module qfd_native_band_tree_tp8 (
 input wire [2:0] ck_band,
 input wire [47:0] ck_lane,
 input wire [3:0] ck_upper,
 input wire rst_n,
 input wire [17:0] lnk,
 input wire [25:0] sel,
 input wire [25:0] lc0,
 input wire [4095:0] tw0,
 output wire [4095:0] ty0,
 input wire [25:0] lc1,
 input wire [4095:0] tw1,
 output wire [4095:0] ty1,
 input wire [25:0] lc2,
 input wire [4095:0] tw2,
 output wire [4095:0] ty2,
 output wire [3:0] uf,
 output wire [2:0] band_fault
);
 wire [128:0] pw_b0_l0;
 wire [128:0] pw_b0_l1;
 wire [128:0] pw_b0_l2;
 wire [128:0] pw_b0_l3;
 wire [3:0] f_up0;
 wire [128:0] pw_b1_l0;
 wire [128:0] pw_b1_l1;
 wire [128:0] pw_b1_l2;
 wire [128:0] pw_b1_l3;
 wire [3:0] f_up1;
 wire [128:0] pw_b2_l0;
 wire [128:0] pw_b2_l1;
 wire [128:0] pw_b2_l2;
 wire [128:0] pw_b2_l3;
 wire [3:0] f_up2;
 wire [1537:0] tt0;
 qfd_sp_band_lanes u_band0 (
 .ck(ck_band[0]),.rst_n(rst_n),.b0(1'b1),.lnk(lnk[0 +: 6]),
 .tw(tw0),.c(lc0),.ty(ty0),.tt(tt0),.pw(),.f(band_fault[0]),.f_up(f_up0),
 .pw_l0(pw_b0_l0),
 .pw_l1(pw_b0_l1),
 .pw_l2(pw_b0_l2),
 .pw_l3(pw_b0_l3),
 .ck_l0(ck_lane[0]),
 .ck_l1(ck_lane[1]),
 .ck_l2(ck_lane[2]),
 .ck_l3(ck_lane[3]),
 .ck_l4(ck_lane[4]),
 .ck_l5(ck_lane[5]),
 .ck_l6(ck_lane[6]),
 .ck_l7(ck_lane[7]),
 .ck_l8(ck_lane[8]),
 .ck_l9(ck_lane[9]),
 .ck_l10(ck_lane[10]),
 .ck_l11(ck_lane[11]),
 .ck_l12(ck_lane[12]),
 .ck_l13(ck_lane[13]),
 .ck_l14(ck_lane[14]),
 .ck_l15(ck_lane[15])
 );
 qfd_sp_band_lanes u_band1 (
 .ck(ck_band[1]),.rst_n(rst_n),.b0(1'b0),.lnk(lnk[6 +: 6]),
 .tw(tw1),.c(lc1),.ty(ty1),.tt(1538'd0),.pw(),.f(band_fault[1]),.f_up(f_up1),
 .pw_l0(pw_b1_l0),
 .pw_l1(pw_b1_l1),
 .pw_l2(pw_b1_l2),
 .pw_l3(pw_b1_l3),
 .ck_l0(ck_lane[16]),
 .ck_l1(ck_lane[17]),
 .ck_l2(ck_lane[18]),
 .ck_l3(ck_lane[19]),
 .ck_l4(ck_lane[20]),
 .ck_l5(ck_lane[21]),
 .ck_l6(ck_lane[22]),
 .ck_l7(ck_lane[23]),
 .ck_l8(ck_lane[24]),
 .ck_l9(ck_lane[25]),
 .ck_l10(ck_lane[26]),
 .ck_l11(ck_lane[27]),
 .ck_l12(ck_lane[28]),
 .ck_l13(ck_lane[29]),
 .ck_l14(ck_lane[30]),
 .ck_l15(ck_lane[31])
 );
 qfd_sp_band_lanes u_band2 (
 .ck(ck_band[2]),.rst_n(rst_n),.b0(1'b0),.lnk(lnk[12 +: 6]),
 .tw(tw2),.c(lc2),.ty(ty2),.tt(1538'd0),.pw(),.f(band_fault[2]),.f_up(f_up2),
 .pw_l0(pw_b2_l0),
 .pw_l1(pw_b2_l1),
 .pw_l2(pw_b2_l2),
 .pw_l3(pw_b2_l3),
 .ck_l0(ck_lane[32]),
 .ck_l1(ck_lane[33]),
 .ck_l2(ck_lane[34]),
 .ck_l3(ck_lane[35]),
 .ck_l4(ck_lane[36]),
 .ck_l5(ck_lane[37]),
 .ck_l6(ck_lane[38]),
 .ck_l7(ck_lane[39]),
 .ck_l8(ck_lane[40]),
 .ck_l9(ck_lane[41]),
 .ck_l10(ck_lane[42]),
 .ck_l11(ck_lane[43]),
 .ck_l12(ck_lane[44]),
 .ck_l13(ck_lane[45]),
 .ck_l14(ck_lane[46]),
 .ck_l15(ck_lane[47])
 );
 wire [383:0] up_ty0;
 wire up_use0,up_v0;
 ot_qfd_band_upper #(.NL(4),.NB(3),.LNK(0),.DLY(1),.TREE_LAT(7),.TCUT(7),.LG(12),.RPIN(1)) u_upper0 (
 .clk(ck_upper[0]),.rst_n(rst_n),
 .pw({pw_b2_l0[127:0],pw_b1_l0[127:0],pw_b0_l0[127:0]}),
 .pw_v({pw_b2_l0[128],pw_b1_l0[128],pw_b0_l0[128]}),
 .lf({f_up2[0],f_up1[0],f_up0[0]}),
 .sel_e(sel[12:0]),.tv_e(sel[25:13]),.tt_ty(up_ty0),.tt_use(up_use0),.tt_v(up_v0),.fault(uf[0])
 );
 assign tt0[0 +: 128]=up_ty0[0 +: 128];
 assign tt0[512 +: 128]=up_ty0[128 +: 128];
 assign tt0[1024 +: 128]=up_ty0[256 +: 128];
 wire [383:0] up_ty1;
 wire up_use1,up_v1;
 ot_qfd_band_upper #(.NL(4),.NB(3),.LNK(0),.DLY(1),.TREE_LAT(7),.TCUT(7),.LG(12),.RPIN(1)) u_upper1 (
 .clk(ck_upper[1]),.rst_n(rst_n),
 .pw({pw_b2_l1[127:0],pw_b1_l1[127:0],pw_b0_l1[127:0]}),
 .pw_v({pw_b2_l1[128],pw_b1_l1[128],pw_b0_l1[128]}),
 .lf({f_up2[1],f_up1[1],f_up0[1]}),
 .sel_e(sel[12:0]),.tv_e(sel[25:13]),.tt_ty(up_ty1),.tt_use(up_use1),.tt_v(up_v1),.fault(uf[1])
 );
 assign tt0[128 +: 128]=up_ty1[0 +: 128];
 assign tt0[640 +: 128]=up_ty1[128 +: 128];
 assign tt0[1152 +: 128]=up_ty1[256 +: 128];
 wire [383:0] up_ty2;
 wire up_use2,up_v2;
 ot_qfd_band_upper #(.NL(4),.NB(3),.LNK(0),.DLY(1),.TREE_LAT(7),.TCUT(7),.LG(12),.RPIN(1)) u_upper2 (
 .clk(ck_upper[2]),.rst_n(rst_n),
 .pw({pw_b2_l2[127:0],pw_b1_l2[127:0],pw_b0_l2[127:0]}),
 .pw_v({pw_b2_l2[128],pw_b1_l2[128],pw_b0_l2[128]}),
 .lf({f_up2[2],f_up1[2],f_up0[2]}),
 .sel_e(sel[12:0]),.tv_e(sel[25:13]),.tt_ty(up_ty2),.tt_use(up_use2),.tt_v(up_v2),.fault(uf[2])
 );
 assign tt0[256 +: 128]=up_ty2[0 +: 128];
 assign tt0[768 +: 128]=up_ty2[128 +: 128];
 assign tt0[1280 +: 128]=up_ty2[256 +: 128];
 wire [383:0] up_ty3;
 wire up_use3,up_v3;
 ot_qfd_band_upper #(.NL(4),.NB(3),.LNK(0),.DLY(1),.TREE_LAT(7),.TCUT(7),.LG(12),.RPIN(1)) u_upper3 (
 .clk(ck_upper[3]),.rst_n(rst_n),
 .pw({pw_b2_l3[127:0],pw_b1_l3[127:0],pw_b0_l3[127:0]}),
 .pw_v({pw_b2_l3[128],pw_b1_l3[128],pw_b0_l3[128]}),
 .lf({f_up2[3],f_up1[3],f_up0[3]}),
 .sel_e(sel[12:0]),.tv_e(sel[25:13]),.tt_ty(up_ty3),.tt_use(up_use3),.tt_v(up_v3),.fault(uf[3])
 );
 assign tt0[384 +: 128]=up_ty3[0 +: 128];
 assign tt0[896 +: 128]=up_ty3[128 +: 128];
 assign tt0[1408 +: 128]=up_ty3[256 +: 128];
 assign tt0[1537:1536]={up_v0,up_use0};
endmodule
