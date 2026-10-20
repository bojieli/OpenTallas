`timescale 1ns/1ps
// ----------------------------------------------------------------------------------------------------------------------
// Wires-only flat parent (tools/landed_parent/lp.py input; also the lockstep DUT).  Ports = qfd_native59_dv_service_r1.
// Children: rtl/qwen_split/qfd_native59_qbank.sv (edge contract in its header) and qfd_native59_svc.sv (QW-N59-4).  SMUT = bench mutant (MUT 1 / 7 ->
// the bank, 2..6 -> the service), QB_MUT = split-only bank mutants; both 0 in every kit.
module qfd_native59_split_flat #(
 parameter integer SMUT=0,CODEC_MUT=0,NATIVE_PROFILE=0,LAND_QUALIFIED=0,LAND_EDGES=8,
 parameter integer NU=4,parameter [13:0] MU_SEQ0=14'd0,parameter integer MCTX=1,EMB_RELAY=1,QB_MUT=0
)(
 input wire ck,rst_n,
 input wire host_epoch_valid,host_fused_capability,input wire[15:0]host_epoch,
 input wire[58:0]host_tag,input wire[1:0]host_generation,
 input wire layer_context_v,input wire[5:0]command_stage,
 input wire[17:0]native_token,native_position,input wire[379:0]native_cmd,
 input wire[547:0]dd_i,
 input wire kv_word_slot,input wire[1:0]kv_word_index,input wire kv_x3_slot,
 output wire[523:0]x3,output wire[58:0]x3_identity,output wire[1:0]x3_generation,
 input wire q_slot,input wire[4:0]q_slot_beat,
 input wire tx_slot,input wire[3:0]tx_slot_kind,input wire[4:0]tx_slot_beat,
 output wire native_tx_v,output wire[547:0]native_tx_payload,
 input wire native_rx_v,input wire[547:0]native_rx_payload,
 input wire rx_slot,input wire[3:0]rx_slot_kind,input wire[4:0]rx_slot_beat,
 output wire[519:0]dr_o,
 output wire emb_code_re,output wire[23:0]emb_code_addr,output wire emb_scale_re,output wire[17:0]emb_scale_addr,
 input wire[511:0]emb_code_q,input wire[15:0]emb_scale_q,
 input wire visibility_slot,complete_slot,output wire completed,output wire[94:0]native_ret,
 output wire fault
);
 wire[547:0]rl_dd;wire rl_lcv;wire[5:0]rl_stage;
 wire qb_v;wire[4:0]qb_beat;wire[511:0]qb_row;wire qb_full,qb_committed,qb_bad;
 qfd_native59_qbank #(.MUT((SMUT==1||SMUT==7)?SMUT:0),.QB_MUT(QB_MUT)) u_qb(
  .ck(ck),.rst_n(rst_n),.dd_i(dd_i),.layer_context_v(layer_context_v),.command_stage(command_stage),
  .q_slot(q_slot),.q_slot_beat(q_slot_beat),.dd_o(rl_dd),.lcv_o(rl_lcv),.stage_o(rl_stage),
  .qb_v(qb_v),.qb_beat(qb_beat),.qb_row(qb_row),.qb_full(qb_full),.qb_committed(qb_committed),.qb_bad(qb_bad));
 qfd_native59_svc #(.MUT((SMUT>=2&&SMUT<=6)?SMUT:0),.CODEC_MUT(CODEC_MUT),.NATIVE_PROFILE(NATIVE_PROFILE),.LAND_QUALIFIED(LAND_QUALIFIED),
  .LAND_EDGES(LAND_EDGES),.NU(NU),.MU_SEQ0(MU_SEQ0),.MCTX(MCTX),.EMB_RELAY(EMB_RELAY)) u_svc(
  .ck(ck),.rst_n(rst_n),
  .host_epoch_valid(host_epoch_valid),.host_fused_capability(host_fused_capability),.host_epoch(host_epoch),
  .host_tag(host_tag),.host_generation(host_generation),.layer_context_v(rl_lcv),.command_stage(rl_stage),
  .native_token(native_token),.native_position(native_position),.native_cmd(native_cmd),.dd_i(rl_dd),
  .kv_word_slot(kv_word_slot),.kv_word_index(kv_word_index),.kv_x3_slot(kv_x3_slot),
  .x3(x3),.x3_identity(x3_identity),.x3_generation(x3_generation),
  .qb_v(qb_v),.qb_beat(qb_beat),.qb_row(qb_row),.qb_full(qb_full),.qb_committed(qb_committed),.qb_bad(qb_bad),
  .tx_slot(tx_slot),.tx_slot_kind(tx_slot_kind),.tx_slot_beat(tx_slot_beat),
  .native_tx_v(native_tx_v),.native_tx_payload(native_tx_payload),.native_rx_v(native_rx_v),
  .native_rx_payload(native_rx_payload),.rx_slot(rx_slot),.rx_slot_kind(rx_slot_kind),.rx_slot_beat(rx_slot_beat),
  .dr_o(dr_o),.emb_code_re(emb_code_re),.emb_code_addr(emb_code_addr),.emb_scale_re(emb_scale_re),
  .emb_scale_addr(emb_scale_addr),.emb_code_q(emb_code_q),.emb_scale_q(emb_scale_q),
  .visibility_slot(visibility_slot),.complete_slot(complete_slot),.completed(completed),.native_ret(native_ret),
  .fault(fault));
endmodule
