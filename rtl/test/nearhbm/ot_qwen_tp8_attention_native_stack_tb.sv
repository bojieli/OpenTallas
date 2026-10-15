`timescale 1ns/1ps
// Explicit equal-phase functional bench only. The DUT retains all2822 native
// clock ports; this adapter is not an insertion/phase or physical proof.
module ot_qwen_tp8_attention_native_stack_tb #(
 parameter integer STACK=0,RL=1,QK_ISSUE_AGE=34,ROW_RETURN_LAT=9,
 parameter integer EXP_START_AGE=365,LMAX_START_AGE=350,Z_START_AGE=900,Z_STRIDE=16
)(
 input wire clk,rst_n,input wire[539:0] aq,input wire[35:0] am,
 output wire[562:0] ap,input wire active_layer_parity,
 output wire[135:0] k_request,input wire[8199:0] k_response,
 input wire er_v,input wire[10:0] er_addr,
 output wire er_rsp_v,output wire[10:0] er_rsp_addr,output wire[63:0] er_data,
 output wire[15:0] exp_committed,output wire score_committed,output wire fault
);
 ot_qwen_tp8_attention_native_stack #(.STACK(STACK),.RL(RL),.QK_ISSUE_AGE(QK_ISSUE_AGE),
  .ROW_RETURN_LAT(ROW_RETURN_LAT),.EXP_START_AGE(EXP_START_AGE),
  .LMAX_START_AGE(LMAX_START_AGE),.Z_START_AGE(Z_START_AGE),.Z_STRIDE(Z_STRIDE)) u_native(
  .rst_n(rst_n),.ck_astk_c(clk),.ck_astk_r(clk),.ck_astk_z({4{clk}}),.ck_astk_x({32{clk}}),
  .ck_astk_e({8{clk}}),.ck_ectl({24{clk}}),.ck_head({2752{clk}}),
  .aq(aq),.am(am),.ap(ap),.active_layer_parity(active_layer_parity),
  .k_request(k_request),.k_response(k_response),.er_v(er_v),.er_addr(er_addr),
  .er_rsp_v(er_rsp_v),.er_rsp_addr(er_rsp_addr),.er_data(er_data),
  .exp_committed(exp_committed),.score_committed(score_committed),.fault(fault));
endmodule
