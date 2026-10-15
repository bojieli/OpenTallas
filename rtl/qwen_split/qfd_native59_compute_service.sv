`timescale 1ns/1ps
// Selected compute-local native service composition. Real SU-derived KV words
// use the static formatter and KVN-only x3 route. Real DVM Q words go once to
// the native548 codec; actual returned results enter VM at compiled slots.
// All clock entries require the die's phi-R phase/RC contract. Common-clock
// component tests do not establish physical or full-token qualification.
module qfd_native59_compute_service #(
 parameter integer CODEC_MUT=0,
 // Zero routes are explicit common-clock component profile only. Production
 // must supply the source-pinned measured forward/return/phase edge contract.
 parameter integer NATIVE_PROFILE=0,VM_ROUTE_QUALIFIED=0,
 parameter integer VM_FORWARD_EDGES=0,VM_RETURN_EDGES=0,VM_PHASE_EDGES=0
)(
 input wire ck_context,ck_service,ck_format,ck_record,ck_qtag,ck_x3,rst_n,
 input wire host_epoch_valid,host_fused_capability,input wire[15:0]host_epoch,
 input wire[58:0]host_tag,input wire[1:0]host_generation,
 input wire layer_context_v,input wire[5:0]command_stage,
 input wire[17:0]native_token,native_position,input wire[379:0]native_cmd,
 input wire[62:0]native_issue,input wire[63:0]kv_we,input wire[1535:0]kv_waddr,input wire[2047:0]kv_wdata,
 input wire kv_word_slot,input wire[1:0]kv_word_index,input wire kv_x3_slot,
 output wire[523:0]x3,output wire[58:0]x3_identity,output wire[1:0]x3_generation,
 output wire vm_q_epoch,vm_q_start,input wire q_committed,q_fault,input wire[523:0]q,
 input wire q_slot,input wire[4:0]q_slot_beat,
 input wire tx_slot,input wire[3:0]tx_slot_kind,input wire[4:0]tx_slot_beat,
 output wire native_tx_v,output wire[547:0]native_tx_payload,
 input wire native_rx_v,input wire[547:0]native_rx_payload,
 input wire rx_slot,input wire[3:0]rx_slot_kind,input wire[4:0]rx_slot_beat,
 // Physical VM24e9aeaf7 attention face: valid, group1, beat6, data512.
 // The VM owns fixed rows3167..3198; word/TAG stay local to the commit fence.
 output wire[519:0]vm_ar,
 input wire[38:0]write_commit_v,input wire[311:0]write_commit_line,input wire[623:0]write_commit_mask,
 input wire visibility_slot,
 input wire complete_slot,output wire completed,output reg[94:0]native_ret,
 output wire fault
);
 // Physical status face is a true ck_service pin register. This adds exactly
 // one OBSERVATION edge; internal request/commit/completion slots are unchanged.
 // No combinational decode or fault OR follows the exported native_ret flops.
 wire [94:0] service_ret_raw;
`ifdef QFD_NATIVE_RET_MUT_BYPASS
 always @* native_ret=service_ret_raw;
`else
 always @(posedge ck_service or negedge rst_n)
  if(!rst_n)native_ret<=95'd0;
  else native_ret<=service_ret_raw;
`endif
 wire vm_write_v;wire[19:0]vm_write_word;wire[4:0]vm_write_beat;
 wire[58:0]vm_write_tag;wire[511:0]vm_write_data;
 // No additional edge or generated handshake: this is the actual registered
 // service write event. g0 and beat<32 select the VM's fixed attention rows.
 assign vm_ar={vm_write_v,1'b0,1'b0,vm_write_beat,vm_write_data};
 wire vm_address_fault=vm_write_v&&(vm_write_word!=(20'd3167+{15'd0,vm_write_beat}));
 wire native_context=layer_context_v&&command_stage>=1&&command_stage<=36;
 wire begin_slot,request_slot,context_fault,active;
 wire[58:0]begin_tag,request_tag;wire[19:0]base;
 qfd_native59_command_context u_context(
 .ck(ck_context),.rst_n(rst_n),.host_epoch_valid(host_epoch_valid),.host_fused_capability(host_fused_capability),.host_epoch(host_epoch),.host_tag(host_tag),.host_generation(host_generation),
 .context_v(native_context),.context_stage(command_stage),.context_token(native_token),.context_position(native_position),
 .native_cmd(native_cmd),.command_stage(command_stage),.command_token(native_token),.command_position(native_position),
 .service_active(active),.begin_slot(begin_slot),.begin_tag(begin_tag),.request_slot(request_slot),.request_tag(request_tag),.result_base_word(base),.fault(context_fault));
 wire export_control_fault;
 qfd_native59_q_export_control u_qexport_control(
 .ck(ck_qtag),.rst_n(rst_n),.begin_slot(begin_slot),.request_slot(request_slot),.q_committed(q_committed),
 .vm_q_epoch(vm_q_epoch),.vm_q_start(vm_q_start),.fault(export_control_fault));
 reg[58:0]context_tag,q_epoch_tag,q_frame_tag,operation_tag;
 reg context_valid,q_window,qtag_fault;reg[5:0]q_count;
 always @(posedge ck_qtag or negedge rst_n)begin
  if(!rst_n)begin context_tag<=0;q_epoch_tag<=0;q_frame_tag<=0;operation_tag<=0;context_valid<=0;q_window<=0;qtag_fault<=0;q_count<=0;end
  else begin
   if(begin_slot)begin context_tag<=begin_tag;context_valid<=1;end
   if(request_slot)operation_tag<=request_tag;
   // The same physical q_epoch reaches the actual VM observer and this tag
   // capture. A later layer/context cannot relabel an old Q memory response.
   if(vm_q_epoch)begin
    if(q_window||(!context_valid&&!begin_slot))qtag_fault<=1;
    q_epoch_tag<=begin_slot?begin_tag:context_tag;
   end
   if(vm_q_start)begin
    if(q_window||!q_committed)qtag_fault<=1;
    q_window<=1;q_count<=0;q_frame_tag<=q_epoch_tag;
   end
   if(q[523])begin
    if(!q_window||q[522:520]!=1||q[519:517]!=0||q_count!={1'b0,q[516:512]})qtag_fault<=1;
    q_count<=q_count+1'b1;
    if(q_count==31)q_window<=0;
   end
  end
 end
 wire formatter_fault,formatter_idle,formatter_drained,kvn_v;wire[7:0]formatter_fault_code;
 wire[10:0]kvn_tag;wire[511:0]kvn_data;
 wire kv_issue=native_issue[0]&&native_issue[38:37]==2;
 // Actual accepted issue fields contain the post-DYN scalar destination:
 // V >= 2^20; K's dimension bit6 is scalar address bit10 (Klo/Khi).
 wire[1:0]kv_kind=(|native_issue[62:59])?2'd0:native_issue[49]?2'd2:2'd1;
 ot_qfd_su_kv_static_posted #(.ENABLE(1),.HEADS(1))u_formatter(
 .clk(ck_format),.rst_n(rst_n),.epoch_begin(native_context),.epoch_pos(native_position),
 .issue_v(kv_issue),.issue_kind(kv_kind),.issue_nout(native_issue[18:1]),.issue_nin(native_issue[36:19]),
 .kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),.epoch_idle(formatter_idle),.drained(formatter_drained),
 .word_v(kvn_v),.word_tag(kvn_tag),.word_data(kvn_data),.word_slot(kv_word_slot),.word_index(kv_word_index),
 .fault(formatter_fault),.fault_code(formatter_fault_code));
 reg[58:0]formatter_identity;reg[1:0]formatter_generation;
 always @(posedge ck_format or negedge rst_n)
  if(!rst_n)begin formatter_identity<=0;formatter_generation<=0;end
  else if(native_context)begin formatter_identity<=begin_tag;formatter_generation<=host_generation;end
 wire x3_fault;
 qfd_kvn_static_transport u_kvn(.ck(ck_x3),.rst_n(rst_n),.word_v(kvn_v),.word_tag(kvn_tag),.word_data(kvn_data),
 .word_identity(formatter_identity),.word_generation(formatter_generation),.slot_v(kv_x3_slot),
 .x3(x3),.x3_identity(x3_identity),.x3_generation(x3_generation),.fault(x3_fault));
 wire req_v,kq_v,svc_fault,record_fault;wire[58:0]req_tag,kq_tag;wire[4:0]kq_beat;wire[511:0]kq_data;
 wire result_v,result_slot;wire[4:0]result_beat,result_slot_beat;wire[58:0]result_tag;wire[511:0]result_data;
 wire kernel_done;wire[58:0]kernel_done_tag;
 wire vm_commit_v,commit_complete,commit_fault;
 reg visibility_seen;
 always @(posedge ck_service or negedge rst_n)
  if(!rst_n)visibility_seen<=0;
  else if(request_slot)visibility_seen<=0;
  else if(visibility_slot)visibility_seen<=commit_complete&&!commit_fault;
 wire visibility_fault=complete_slot&&!visibility_seen;wire[4:0]vm_commit_beat;wire[58:0]vm_commit_tag;
 // Raw events come from the actual 39 VM bank SRAM write-consume pins.
 // Native writes are never delayed. Internal VM consume is8 edges; physical
 // forward, return and phase edges are additional compiler-owned constants.
 localparam integer VM_TOTAL_EDGES=8+VM_FORWARD_EDGES+VM_RETURN_EDGES+VM_PHASE_EDGES;
 qfd_vm_attention_commit_fence #(.COMMIT_EDGES(VM_TOTAL_EDGES))u_vm_commit(
 .ck(ck_service),.rst_n(rst_n),.request_slot(request_slot),.request_tag59(request_tag),
 .write_v(vm_write_v),.write_beat(vm_write_beat),.write_tag59(vm_write_tag),
 .visibility_slot(visibility_slot),.write_commit_v(write_commit_v),.write_commit_line(write_commit_line),.write_commit_mask(write_commit_mask),
 .vm_commit_v(vm_commit_v),.vm_commit_beat(vm_commit_beat),.vm_commit_tag59(vm_commit_tag),.complete(commit_complete),.fault(commit_fault));
 qfd_native59_static_service u_service(
 .ck(ck_service),.rst_n(rst_n),.source_fault(context_fault|qtag_fault|export_control_fault|q_fault|formatter_fault|x3_fault|record_fault|commit_fault|visibility_fault|vm_address_fault),
 .begin_slot(begin_slot),.begin_tag(begin_tag),.request_slot(request_slot),.request_tag(request_tag),.result_base_word(base),
 .qr_committed(q_committed),.qr_tag(q_epoch_tag),.kernel_request_v(req_v),.kernel_request_tag(req_tag),
 .q_slot(q_slot),.q_slot_beat(q_slot_beat),.q_v(q[523]),.q_beat(q[516:512]),.q_tag(q_frame_tag),.q_data(q[511:0]),
 .kernel_q_v(kq_v),.kernel_q_beat(kq_beat),.kernel_q_tag(kq_tag),.kernel_q_data(kq_data),
 .result_slot(result_slot),.result_slot_beat(result_slot_beat),.result_v(result_v),.result_beat(result_beat),.result_tag(result_tag),.result_data(result_data),
 .vm_write_v(vm_write_v),.vm_write_word(vm_write_word),.vm_write_beat(vm_write_beat),.vm_write_tag(vm_write_tag),.vm_write_data(vm_write_data),
 .vm_commit_v(vm_commit_v),.vm_commit_beat(vm_commit_beat),.vm_commit_tag(vm_commit_tag),.kernel_done(kernel_done),.kernel_done_tag(kernel_done_tag),
 .complete_slot(complete_slot),.completed(completed),.active(active),.fault(svc_fault),.native_ret(service_ret_raw));
 qfd_native59_record_endpoint #(.CODEC_MUT(CODEC_MUT))u_record(
 .ck(ck_record),.rst_n(rst_n),.operation_tag(operation_tag),.kernel_request_v(req_v),.kernel_request_tag(req_tag),
 .kernel_q_v(kq_v),.kernel_q_beat(kq_beat),.kernel_q_tag(kq_tag),.kernel_q_data(kq_data),
 .tx_slot(tx_slot),.tx_slot_kind(tx_slot_kind),.tx_slot_beat(tx_slot_beat),.tx_valid(native_tx_v),.tx_payload(native_tx_payload),
 .rx_event(native_rx_v),.rx_payload(native_rx_payload),.rx_slot(rx_slot),.rx_slot_kind(rx_slot_kind),.rx_slot_beat(rx_slot_beat),
 .result_v(result_v),.result_beat(result_beat),.result_tag(result_tag),.result_data(result_data),.result_slot(result_slot),.result_slot_beat(result_slot_beat),
 .kernel_done(kernel_done),.kernel_done_tag(kernel_done_tag),.fault(record_fault));
 initial begin
  if(NATIVE_PROFILE!=0&&VM_ROUTE_QUALIFIED!=1)$fatal(1,"native service requires measured VM forward/return/phase contract");
  if(VM_FORWARD_EDGES<0||VM_RETURN_EDGES<0||VM_PHASE_EDGES<0)$fatal(1,"negative physical VM route edges");
 end
 assign fault=svc_fault|context_fault|qtag_fault|export_control_fault|q_fault|formatter_fault|x3_fault|record_fault|commit_fault|visibility_fault|vm_address_fault;
endmodule
