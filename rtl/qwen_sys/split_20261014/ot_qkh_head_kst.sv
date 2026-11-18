`timescale 1ns/1ps
// KV-KT-E0 2026-11-18 (FABLE-FIX-KV-HG fix #2, KV event D25): one kt input station stage of a native head lane.
// Sits between a lane's ot_qkh_head_stk_native (kp_o / kpv_o / gf_o, 34 b) and the head K-tree input of that lane.  The
// head variants ot_qkh_head_native_r4*_kst (generated, tools/qwen_kv_die/head_st_rtl.py) carry two of them a lane
// (u_kst0 beside the lane's stk, u_kst1 beside the K-tree) so each stage is a named cell that can be sited on its own:
// on the KV die lanes 2..15 keep both stages in the hg / hgi parent (e1..e7 -> e0 is 1.1 - 1.8 mm), lanes 0, 1 keep them
// inside kv3_head_eighth_e0.  The depth is uniform over the 16 lanes of a head (the K-tree adds lanes edge for edge).
//   D = 1  one register stage on the 34 bits (kp 32 + kpv + gf)
//   D = 0  wires (no cell left after flattening: the head is the head without stations)
// No reset: exactly the plan station cell (ot_dp_dly) of the timing proof.  In reset the lane stk drives its reset value
// (kpv / gf 0), so stage k holds it after k + 1 clock edges in reset, and the stk / K-tree reset relays themselves need
// three edges to release (ot_rst_relay 2 + 1): the K-tree never samples a stage's power-up value.  Valid / fault
// semantics are those of u_stk, one edge a stage later (lock-step rtl/test/qwen_kv_die/tb_qkh_head_kst.sv: resets of
// 4 and 8 edges between and inside K passes, random flop power-up).
module ot_qkh_head_kst_native #(parameter integer D=1) (
  input wire clk,
  input wire [31:0] kp_i,input wire kpv_i,gf_i,
  output wire [31:0] kp_o,output wire kpv_o,gf_o);
  generate if(D==0) begin:g_w
    assign {gf_o,kpv_o,kp_o}={gf_i,kpv_i,kp_i};
  end else if(D==1) begin:g_r
    (* keep *) reg [33:0] r;
    always @(posedge clk) r<={gf_i,kpv_i,kp_i};
    assign {gf_o,kpv_o,kp_o}=r;
  end else begin:g_bad
    ot_qkh_head_kst_native__D_is_0_or_1 u_bad();
  end endgenerate
endmodule
