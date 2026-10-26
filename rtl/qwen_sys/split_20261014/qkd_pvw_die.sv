`timescale 1ns/1ps
// Q-KVSYS-PV 2026-10-16 (KV die v1.4.4, OT_KV_V144=1): the KV-die face of one PV16 wide pair.  WIRES ONLY: the actual
// ot_qwen_tp8_pv_wide_pair (rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv, unchanged) with its per-V-port words regrouped so
// that each V port qkd_pv16_vport k is ONE die word each way (one relay chain, so valid, tag and data take the same
// registered stages by construction):
//   vrq<k>[14:0]    = {req_t[14k +: 14], req_valid[k]}                         pair -> vport k  (vport pr = {pr_t, pr_valid})
//   vin<k>[1038:0]  = {in_v[1024k +: 1024], in_t[14k +: 14], in_valid[k]}      vport k -> pair  (vport vo = {out_v_hi,
//                                                                               out_v_lo, out_t, out_valid})
// k = 0-3: stack PAIR lanes 0-3, k = 4-7: stack PAIR + 2 lanes 0-3 (vport_wiring.txt).  No logic, no constants: every
// other pair port passes straight through (the pair's clk port is unused by its RTL: it takes col_clk[32]).  The die places the pair's 289 closed leaves itself (kv_expand.py).
module qkd_pvw_die #(
 parameter integer PAIR=0,
 parameter integer CTL_RESET_PIN=1,
 parameter integer LEAF_RESET_PIN=1,
 parameter integer FIRST_INPUT_AGE=20,
 parameter integer MUT=0
)(
 input wire rst_n,start,input wire[32:0] col_clk,input wire[13:0] context_len,input wire[15:0] epoch,
 input wire[1038:0] vin0,vin1,vin2,vin3,vin4,vin5,vin6,vin7,
 input wire[511:0] in_e,input wire[127:0] in_epoch,
 output wire[14:0] vrq0,vrq1,vrq2,vrq3,vrq4,vrq5,vrq6,vrq7,
 output wire out_valid,output wire[16383:0] out_leaf,output wire[15:0] out_epoch,
 output wire fault,output wire busy,output wire[15:0] out_age
);
 wire[1038:0] vin[0:7];
 assign vin[0]=vin0; assign vin[1]=vin1; assign vin[2]=vin2; assign vin[3]=vin3;
 assign vin[4]=vin4; assign vin[5]=vin5; assign vin[6]=vin6; assign vin[7]=vin7;
 wire[7:0] in_valid,req_valid;wire[8191:0] in_v;wire[111:0] in_t,req_t;
 genvar k;
 generate for(k=0;k<8;k=k+1)begin:g_vp
  assign in_valid[k]=vin[k][0];
  assign in_t[14*k+:14]=vin[k][14:1];
  assign in_v[1024*k+:1024]=vin[k][1038:15];
 end endgenerate
 assign vrq0={req_t[0+:14],req_valid[0]};   assign vrq1={req_t[14+:14],req_valid[1]};
 assign vrq2={req_t[28+:14],req_valid[2]};  assign vrq3={req_t[42+:14],req_valid[3]};
 assign vrq4={req_t[56+:14],req_valid[4]};  assign vrq5={req_t[70+:14],req_valid[5]};
 assign vrq6={req_t[84+:14],req_valid[6]};  assign vrq7={req_t[98+:14],req_valid[7]};
 ot_qwen_tp8_pv_wide_pair #(.PAIR(PAIR),.CTL_RESET_PIN(CTL_RESET_PIN),.LEAF_RESET_PIN(LEAF_RESET_PIN),
  .FIRST_INPUT_AGE(FIRST_INPUT_AGE),.MUT(MUT)) u_pair(
  .clk(col_clk[32]),.rst_n(rst_n),.start(start),.col_clk(col_clk),.context_len(context_len),.epoch(epoch),
  .in_valid(in_valid),.in_v(in_v),.in_e(in_e),.in_t(in_t),.in_epoch(in_epoch),.req_valid(req_valid),.req_t(req_t),
  .out_valid(out_valid),.out_leaf(out_leaf),.out_epoch(out_epoch),.fault(fault),.busy(busy),.out_age(out_age));
endmodule
