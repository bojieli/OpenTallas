// bench (gen_svc.py) for hfd_svc_SW
`timescale 1ps/1ps
module tb_svc_ps_SW;
  localparam [7:0] FWDV = 8'b01010101;
`include "tb_svc_ps_body.svh"
  wire [44:0] tq0 = {fck, 1'b0, qd[0], qv[0]}; assign qrdy[0] = 1'b0;
  wire [1101:0] tl0; assign ln[0] = tl0[1098:0];
  wire [43:0] tq1; assign tq1[42:0] = {qd[1], qv[1]}; assign qrdy[1] = tq1[43];
  wire [1098:0] tl1; assign ln[1] = tl1;
  wire [44:0] tq2 = {fck, 1'b0, qd[2], qv[2]}; assign qrdy[2] = 1'b0;
  wire [1101:0] tl2; assign ln[2] = tl2[1098:0];
  wire [43:0] tq3; assign tq3[42:0] = {qd[3], qv[3]}; assign qrdy[3] = tq3[43];
  wire [1098:0] tl3; assign ln[3] = tl3;
  wire [44:0] tq4 = {fck, 1'b0, qd[4], qv[4]}; assign qrdy[4] = 1'b0;
  wire [1101:0] tl4; assign ln[4] = tl4[1098:0];
  wire [43:0] tq5; assign tq5[42:0] = {qd[5], qv[5]}; assign qrdy[5] = tq5[43];
  wire [1098:0] tl5; assign ln[5] = tl5;
  wire [44:0] tq6 = {fck, 1'b0, qd[6], qv[6]}; assign qrdy[6] = 1'b0;
  wire [1101:0] tl6; assign ln[6] = tl6[1098:0];
  wire [43:0] tq7; assign tq7[42:0] = {qd[7], qv[7]}; assign qrdy[7] = tq7[43];
  wire [1098:0] tl7; assign ln[7] = tl7;
  wire [1040:0] tkv; wire [1025:0] tik; assign kvo = tkv[1037:0]; assign iko = tik[1023:0];
`ifdef REFDUT
  // the LEGACY segmented service as the DUT on the same nets, its own PHY model and the same scoreboard (2026-10-10:
  // the PS / legacy comparison is transaction-level; no shared PHY bus)
  hfd_svc_SW_seg dut (.ck(ck), .rst(rst), .e({fck, ed, ev}), .kv(tkv), .ik(tik), .phy(phy), .qsm4(tq0), .lsm4(tl0), .qsm0(tq1), .lsm0(tl1), .qsm5(tq2), .lsm5(tl2), .qsm1(tq3), .lsm1(tl3), .qsm6(tq4), .lsm6(tl4), .qsm2(tq5), .lsm2(tl5), .qsm7(tq6), .lsm7(tl6), .qsm3(tq7), .lsm3(tl7));
  assign kd = 2'b00;
  genvar gks; for (gks = 0; gks < 8; gks = gks + 1) begin : gksz assign ks[gks] = 1102'd0; end
`else
  hfd_svc_SW_seg_ps dut (.ck(ck), .rst(rst), .e({fck, ed, ev}), .kv(tkv), .ik(tik), .phy(phy), .kd(kd), .ks0(ks[0]), .kq0(kqf[0]), .ks1(ks[1]), .kq1(kqf[1]), .ks2(ks[2]), .kq2(kqf[2]), .ks3(ks[3]), .kq3(kqf[3]), .ks4(ks[4]), .kq4(kqf[4]), .ks5(ks[5]), .kq5(kqf[5]), .ks6(ks[6]), .kq6(kqf[6]), .ks7(ks[7]), .kq7(kqf[7]),
    .qsm4(tq0), .lsm4(tl0), .qsm0(tq1), .lsm0(tl1), .qsm5(tq2), .lsm5(tl2), .qsm1(tq3), .lsm1(tl3), .qsm6(tq4), .lsm6(tl4), .qsm2(tq5), .lsm2(tl5), .qsm7(tq6), .lsm7(tl6), .qsm3(tq7), .lsm3(tl7));
`endif

endmodule
