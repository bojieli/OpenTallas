// bench (gen_svc.py) for hfd_svc_NE
`timescale 1ps/1ps
module tb_svn_ps_NE;
  parameter integer NXL = 0;           // [svc-ep] extra PHY cycles on native requests
`define NEP
  localparam [7:0] FWDV = 8'b01010101;
`include "tb_svc_ps_body.svh"
`include "tb_svn_drv.svh"
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
  hfd_svc_NE_seg_ps dut (.ck(ck), .rst(rst), .e({fck, ed, ev}), .e2({fck, ed2, ev2}), .kv(tkv), .ik(tik), .phy(phy), .kd(kd), .ks0(ks[0]), .kq0(kqf[0]), .ks1(ks[1]), .kq1(kqf[1]), .ks2(ks[2]), .kq2(kqf[2]), .ks3(ks[3]), .kq3(kqf[3]), .ks4(ks[4]), .kq4(kqf[4]), .ks5(ks[5]), .kq5(kqf[5]), .ks6(ks[6]), .kq6(kqf[6]), .ks7(ks[7]), .kq7(kqf[7]), .kc0(kcf[0]), .kc1(kcf[1]), .kc2(kcf[2]), .kc3(kcf[3]), .kc4(kcf[4]), .kc5(kcf[5]), .kc6(kcf[6]), .kc7(kcf[7]), .lq(lq_w), .lr(lr_w),
    .qsm28(tq0), .lsm28(tl0), .qsm24(tq1), .lsm24(tl1), .qsm29(tq2), .lsm29(tl2), .qsm25(tq3), .lsm25(tl3), .qsm30(tq4), .lsm30(tl4), .qsm26(tq5), .lsm26(tl5), .qsm31(tq6), .lsm31(tl6), .qsm27(tq7), .lsm27(tl7));
  // [svc-ep] N8 stray-credit / overflow faults of every group unit and the endpoint fault
  reg nep_ff = 0;
  always @(posedge ck) if (rst && !nep_ff && (dut.u_s0.u_gp0.ovf | dut.u_s0.u_gp1.ovf | dut.u_s1.u_gp2.ovf | dut.u_s2.u_gp3.ovf | dut.u_s3.u_gp4.ovf | dut.u_s4.u_gp5.ovf | dut.u_s5.u_gp6.ovf | dut.u_s7.u_gp7.ovf | dut.u_s3.u_nep.fault)) begin nep_ff = 1; err = err + 1;
    $display("ERR svc fault: group ovf / stray credit %b, endpoint %b", {dut.u_s0.u_gp0.ovf, dut.u_s0.u_gp1.ovf, dut.u_s1.u_gp2.ovf, dut.u_s2.u_gp3.ovf, dut.u_s3.u_gp4.ovf, dut.u_s4.u_gp5.ovf, dut.u_s5.u_gp6.ovf, dut.u_s7.u_gp7.ovf}, dut.u_s3.u_nep.fault); end

endmodule
