// bench (gen_svc.py) for hfd_svc_NE
`timescale 1ps/1ps
module tb_svc_ps_NE;
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
  hfd_svc_NE_seg_ps dut (.ck(ck), .rst(rst), .e({fck, ed, ev}), .kv(tkv), .ik(tik), .phy(phy), .kd(kd), .ks0(ks[0]), .kq0(kqf[0]), .ks1(ks[1]), .kq1(kqf[1]), .ks2(ks[2]), .kq2(kqf[2]), .ks3(ks[3]), .kq3(kqf[3]), .ks4(ks[4]), .kq4(kqf[4]), .ks5(ks[5]), .kq5(kqf[5]), .ks6(ks[6]), .kq6(kqf[6]), .ks7(ks[7]), .kq7(kqf[7]),
    .qsm28(tq0), .lsm28(tl0), .qsm24(tq1), .lsm24(tl1), .qsm29(tq2), .lsm29(tl2), .qsm25(tq3), .lsm25(tl3), .qsm30(tq4), .lsm30(tl4), .qsm26(tq5), .lsm26(tl5), .qsm31(tq6), .lsm31(tl6), .qsm27(tq7), .lsm27(tl7));
`ifdef LOCKSTEP
  wire [1040:0] rkv; wire [1025:0] rik;
  wire [1101:0] rl0;
  wire [1098:0] rl1;
  wire [1101:0] rl2;
  wire [1098:0] rl3;
  wire [1101:0] rl4;
  wire [1098:0] rl5;
  wire [1101:0] rl6;
  wire [1098:0] rl7;
  hfd_svc_NE_seg ref_ (.ck(ck), .rst(rst), .e({fck, ed, ev}), .kv(rkv), .ik(rik), .phy(phy),
    .qsm28(tq0), .lsm28(rl0), .qsm24(tq1), .lsm24(rl1), .qsm29(tq2), .lsm29(rl2), .qsm25(tq3), .lsm25(rl3), .qsm30(tq4), .lsm30(rl4), .qsm26(tq5), .lsm26(rl5), .qsm31(tq6), .lsm31(rl6), .qsm27(tq7), .lsm27(rl7));
  integer lsm = 0;
  always @(posedge ck) if (rst) begin
    if ({tl0, tl1, tl2, tl3, tl4, tl5, tl6, tl7, tkv, tik} !== {rl0, rl1, rl2, rl3, rl4, rl5, rl6, rl7, rkv, rik}) begin
      lsm = lsm + 1; if (lsm < 4) $display("ERR LOCKSTEP PS vs legacy segments differ at %0t", $time); err = err + 1; end
  end
`endif

endmodule
