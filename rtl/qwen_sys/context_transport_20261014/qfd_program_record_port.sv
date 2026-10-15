`timescale 1ns/1ps
// Compute end of typed native HOST records. Two sink receipts must be produced
// independently by actual TT/SU consumed-macro observers. This leaf does not
// create a memory receipt from transmitted PW data or mirror one sink as two.
module qfd_program_record_port(
 input wire ck,rst_n,auth_slot,context_slot,witness_slot,
 input wire rx_v,input wire[547:0]rx_record,
 input wire execution_active,
 // Two actual independent TT/SU consumed-write observer faces, v/full/address/data.
 input wire[151:0]program_obs2,input wire[68:0]descriptor_obs,
 input wire[1:0]cfg_image_ready,
 input wire head_context_v,input wire[5:0]head_stage,
 input wire[17:0]head_token,head_position,
 output wire begin_v,auth_v,output wire[15:0]begin_epoch,auth_epoch,
 output wire[10:0]expected_pw,output wire[3:0]expected_dw,output wire[63:0]auth_digest,
 output wire program_ready,installed_fusedcap,commit_v,
 output wire[15:0]program_epoch,output wire[63:0]program_digest,
 output wire host_epoch_valid,output wire[15:0]host_epoch,
 output wire[58:0]host_tag,output wire[1:0]host_gen,
 output wire tx_v,tx_observed_v,output wire[547:0]tx_record,
 output wire fault
);
 wire af,jf,cf,wf;reg slot_fault;
 wire[1:0]sink_ready,sink_fault,sink_fusedcap;
 wire[31:0]sink_epoch;wire[127:0]sink_digest;
 // SU owns the one actual descriptor store. TT's extra program-bank stage
 // needs the genuine consumed descriptor receipt delayed one fixed edge.
 reg[68:0]tt_descriptor_obs;
 always @(posedge ck or negedge rst_n)
 if(!rst_n)tt_descriptor_obs<=0;else tt_descriptor_obs<=descriptor_obs;
 for(genvar sink=0;sink<2;sink=sink+1)begin:g_actual_sink
 wire[75:0]pw=program_obs2[76*sink+:76];
 wire[68:0]dw=(sink==0)?tt_descriptor_obs:descriptor_obs;
 qkd_program_commit u_receipt(.ck(ck),.rst_n(rst_n),.execution_active(execution_active),.control_stores_ready(cfg_image_ready[sink]),
 .begin_v(begin_v),.begin_epoch(begin_epoch),.expected_pw(expected_pw),.expected_dw(expected_dw),
 .auth_v(auth_v),.auth_epoch(auth_epoch),.auth_digest(auth_digest),
 .pw_v(pw[75]),.pw_full_word(pw[74]),.pw_addr(pw[73:64]),.pw_data(pw[63:0]),
 .dw_v(dw[68]),.dw_full_word(dw[67]),.dw_addr(dw[66:64]),.dw_data(dw[63:0]),
 .commit_v(),.ready(sink_ready[sink]),.fault(sink_fault[sink]),.installed_fusedcap(sink_fusedcap[sink]),
 .commit_epoch(sink_epoch[16*sink+:16]),.commit_digest(sink_digest[64*sink+:64]));
 end
 wire context_cap;wire[15:0]context_image_epoch;wire[63:0]context_image_digest;
 always @(posedge ck or negedge rst_n)
 if(!rst_n)slot_fault<=0;
 else if((auth_slot&&context_slot)||(rx_v!==(auth_slot|context_slot)))slot_fault<=1;
 qfd_program_auth_rx u_auth(.ck(ck),.rst_n(rst_n),.receive_slot(auth_slot),.rx_v(rx_v&&auth_slot),.rx_record(rx_record),
 .begin_v(begin_v),.begin_epoch(begin_epoch),.expected_pw(expected_pw),.expected_dw(expected_dw),
 .auth_v(auth_v),.auth_epoch(auth_epoch),.auth_digest(auth_digest),.fault(af));
 qkd_program_commit_join #(.SINKS(2))u_join(.ck(ck),.rst_n(rst_n),.begin_v(begin_v),.auth_v(auth_v),
 .execution_active(execution_active),.control_stores_ready(&cfg_image_ready),
 .auth_epoch(auth_epoch),.auth_digest(auth_digest),.sink_ready(sink_ready),.sink_fault(sink_fault),
 .sink_fusedcap(sink_fusedcap),.sink_epoch(sink_epoch),.sink_digest(sink_digest),
 .commit_v(commit_v),.ready(program_ready),.fault(jf),.installed_fusedcap(installed_fusedcap),
 .commit_epoch(program_epoch),.commit_digest(program_digest));
 qfd_host_native_context_rx u_context(.ck(ck),.rst_n(rst_n),.receive_slot(context_slot),.rx_v(rx_v&&context_slot),.rx_record(rx_record),
 .program_begin_v(begin_v),.program_ready(program_ready),.installed_fusedcap(installed_fusedcap),.program_epoch(program_epoch),.program_digest(program_digest),
 .head_context_v(head_context_v),.head_stage(head_stage),.head_token(head_token),.head_position(head_position),.native_active(execution_active),
 .host_epoch_valid(host_epoch_valid),.host_epoch(host_epoch),.host_tag(host_tag),.host_gen(host_gen),
 .host_fusedcap(context_cap),.host_image_epoch(context_image_epoch),.host_image_digest(context_image_digest),.fault(cf));
 qfd_program_witness_tx u_witness(.ck(ck),.rst_n(rst_n),.send_slot(witness_slot),.commit_v(commit_v),
 .program_ready(program_ready),.installed_fusedcap(installed_fusedcap),.program_fault(jf|af|slot_fault),
 .program_epoch(program_epoch),.program_digest(program_digest),.tx_v(tx_v),.tx_observed_v(tx_observed_v),.tx_record(tx_record),.fault(wf));
 assign fault=af|jf|cf|wf|slot_fault;
endmodule
