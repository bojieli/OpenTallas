// bench (gen_svc.py) for hfd_svc_NW
`timescale 1ps/1ps
module tb_hfd_svc_NW;
  localparam [7:0] FWDV = 8'b01010101;
`include "tb_svc_body.svh"
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
  hfd_svc_NW dut (.ck(ck), .rst(rst), .e({fck, ed, ev}), .kv(tkv), .ik(tik), .phy(phy),
    .qsm20(tq0), .lsm20(tl0), .qsm16(tq1), .lsm16(tl1), .qsm21(tq2), .lsm21(tl2), .qsm17(tq3), .lsm17(tl3), .qsm22(tq4), .lsm22(tl4), .qsm18(tq5), .lsm18(tl5), .qsm23(tq6), .lsm23(tl6), .qsm19(tq7), .lsm19(tl7));
endmodule
