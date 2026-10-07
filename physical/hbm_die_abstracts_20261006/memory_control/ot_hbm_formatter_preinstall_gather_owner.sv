`timescale 1ns/1ps
// Default-OFF successor composition: ONE original bridge + ONE original borrower.
// Gibbs owns selected-parent replacement. Protected descriptor/lease observation
// uses original decoded rows; hierarchical synthesis support remains to verify.
// Additive combined parent hook. Native/index/SU/W2 share ONE actual SM0
// request/response route upstream of existing AW3 CDC. All caller and provider
// signals remain real enclosing ports; no grants/ready/values are constant-tied.
// Installer/source phase and original W15 held-caller enrollment remain required.
module ot_hbm_formatter_preinstall_gather_owner #(
 parameter integer ENABLE=0,VM_AW=0,PREINSTALL_ENABLE=0,
 parameter [63:0] ENTRY_PC=0,
 parameter [31:0] SCORE_SOURCE=32'h80000,ID_SOURCE=32'h80800,
 parameter [31:0] ARENA_BASE=32'h10000,ARENA_LIMIT=32'h70000,
 parameter [31:0] SINK_BASE=32'h70000,SINK_LIMIT=32'h70800,
 parameter [32:0] CAPACITY_BYTES=33'h100000
)(
 input wire clk,por_n,
 input wire warm_req,
 input wire preinstall_begin_v,output wire preinstall_begin_r,
 input wire [72:0] preinstall_begin_frame,
 input wire [31:0] preinstall_score_base,preinstall_id_base,
 input wire [32:0] preinstall_capacity,
 input wire [7:0] preinstall_occupied_records,
 input wire [4:0] preinstall_layer,preinstall_candidate_source_layer,
 input wire preinstall_candidate_masked,
 input wire preinstall_record_v,output wire preinstall_record_r,
 input wire [1:0] preinstall_record_kind,input wire [6:0] preinstall_record_rank,
 input wire [31:0] preinstall_record_base,preinstall_record_end,
 input wire [72:0] preinstall_record_frame,
 input wire [2:0] preinstall_other_writer_v,
 input wire [95:0] preinstall_other_writer_base,preinstall_other_writer_end,
 input wire preinstall_source_v,output wire preinstall_source_r,
 input wire [72:0] preinstall_source_frame,input wire [6:0] preinstall_source_rank,
 input wire preinstall_source_plane,input wire [4:0] preinstall_source_word,
 input wire [511:0] preinstall_source_data,
 output wire preinstall_source_ACK_v,input wire preinstall_source_ACK_r,
 output wire [72:0] preinstall_source_ACK_frame,output wire [6:0] preinstall_source_ACK_rank,
 output wire preinstall_source_ACK_plane,output wire [4:0] preinstall_source_ACK_word,
 output wire reservation_v,input wire reservation_r,
 output wire reservation_checked,reservation_exclusive,
 output wire [72:0] reservation_frame,output wire [511:0] reservation_descriptor,
 input wire consumer_reverse_v,output wire consumer_reverse_r,
 input wire [72:0] consumer_reverse_frame,input wire consumer_sink_ACK_drained,
 output wire source_reverse_v,input wire source_reverse_r,
 output wire source_reverse_checked,source_drained,output wire [72:0] source_reverse_frame,
 output wire preinstall_retained,output wire [72:0] preinstall_frame,
 output wire preinstall_warm_ack,preinstall_fault,preinstall_ce,preinstall_due,

 input wire desc_v, output wire desc_r, input wire [2:0] desc_index,
 input wire [63:0] desc_data,
 input wire start_v, output wire start_r, input wire installed_book_valid,
 input wire [31:0] job, input wire [3:0] gen,
 input wire [16:0] token, input wire [19:0] pos,
 output wire retained,arena_visible,sink_visible,fault,
 output wire [31:0] bound_arena_base,bound_arena_limit,
 // Existing checked shared-borrow grant and existing protected retained frame.
 // Export only: no second owner seat, grant source, or completion authority.
 output wire formatter_lease_valid,output wire [72:0] formatter_lease_frame,
 // All addresses here are BYTE addresses. kind: 0 source read, 1 score
 // store, 2 ID store, 3 formatter read, 4 final ID sink store.
 input wire req_v, output wire req_r, input wire [2:0] req_kind,
 input wire [31:0] req_addr, input wire [15:0] req_tag,
 input wire [6:0] req_rank, input wire [5:0] req_word,
 input wire [511:0] req_data,
 input wire [31:0] req_job, input wire [3:0] req_gen,
 input wire [16:0] req_token, input wire [19:0] req_pos,
 output wire rsp_v, input wire rsp_r, output wire [511:0] rsp_data,
 output wire [31:0] rsp_addr, output wire [15:0] rsp_tag,
 output wire [2:0] rsp_kind, output wire rsp_checked,
 output wire [31:0] held_job, output wire [3:0] held_gen,
 output wire [16:0] held_token, output wire [19:0] held_pos,
 // Connect to shared borrower's existing SM-side AW3 CDC, not a new port.
 output wire m_req_v, input wire m_req_rdy, output wire m_req_we,
 output wire [31:0] m_req_addr, output wire [255:0] m_req_wdata,
 output wire [31:0] m_req_wstrb, output wire [15:0] m_req_tag,
 input wire m_rsp_v, output wire m_rsp_rdy, input wire m_rsp_we,
 input wire [255:0] m_rsp_data, input wire [15:0] m_rsp_tag,
 input wire release_v, output wire release_r,
 input wire [31:0] release_job, input wire [3:0] release_gen,
 input wire [16:0] release_token, input wire [19:0] release_pos,
 input wire result_published,source_reverse_done,
 // Existing native, SU and W2 requesters respectively; no new provider port.
 input wire native_clients_drained,cdc_drained,provider_fault,
 input wire [3:0] observe_req,observe_rsp,observe_req_we,observe_rsp_we,
 input wire [63:0] observe_req_tag,observe_rsp_tag,
 input wire [3:0] return_offer,output wire [3:0] response_authorized,
 input wire [31:0] native_job,input wire [3:0] native_gen,
 input wire [16:0] native_token,input wire [19:0] native_pos,
 output wire native_credit_empty,shared_idle,
 input wire [1:0] peer_lease_v,peer_quiet,peer_release_v,
 input wire [63:0] peer_lease_job,peer_release_job,
 input wire [7:0] peer_lease_gen,peer_release_gen,
 input wire [33:0] peer_lease_token,peer_release_token,
 input wire [39:0] peer_lease_pos,peer_release_pos,
 output wire [1:0] peer_lease_granted,peer_release_r,
 input wire [2:0] p_req_v,p_req_we,output wire [2:0] p_req_rdy,
 input wire [95:0] p_req_addr,p_req_wstrb,input wire [767:0] p_req_wdata,
 input wire [47:0] p_req_tag,output wire [2:0] p_rsp_v,p_rsp_we,
 input wire [2:0] p_rsp_rdy,output wire [47:0] p_rsp_tag,
 output wire [767:0] p_rsp_data
);
 wire borrow_v,borrow_granted,borrow_fault,borrow_release,borrow_release_ack;
 wire bridge_fault,arb_fault;
 wire b_req_v,b_req_rdy,b_req_we,b_rsp_v,b_rsp_rdy,b_rsp_we;
 wire [31:0] b_req_addr,b_req_wstrb;wire [255:0] b_req_wdata,b_rsp_data;
 wire [15:0] b_req_tag,b_rsp_tag;
 wire [2:0] grants,releases;
 wire [3:0] all_req_rdy,all_rsp_v,all_rsp_we;
 wire [63:0] all_rsp_tag;wire [1023:0] all_rsp_data;
 wire use_pre=ENABLE!=0&&PREINSTALL_ENABLE!=0;
 wire pre_lease,pre_req_v,pre_req_r,pre_req_we,pre_rsp_r;
 wire [31:0] pre_req_addr,pre_req_strb;wire [255:0] pre_req_data;
 wire [15:0] pre_req_tag;
 wire [511:0] descriptor_readback;wire [7:0] descriptor_mask;
 wire descriptor_good;wire [72:0] actual_lease_frame;
 wire original_desc_r;
 wire selected_pre=use_pre&&!retained;
 wire x_req_v=selected_pre?pre_req_v:b_req_v;
 wire x_req_we=selected_pre?pre_req_we:b_req_we;
 wire [31:0] x_req_addr=selected_pre?pre_req_addr:b_req_addr;
 wire [31:0] x_req_strb=selected_pre?pre_req_strb:b_req_wstrb;
 wire [255:0] x_req_data=selected_pre?pre_req_data:b_req_wdata;
 wire [15:0] x_req_tag=selected_pre?pre_req_tag:b_req_tag;
 wire x_rsp_r=selected_pre?pre_rsp_r:b_rsp_rdy;
 assign pre_req_r=all_req_rdy[1]&&selected_pre;
 assign desc_r=original_desc_r&&(!use_pre||(!preinstall_retained&&!warm_req));
 assign borrow_granted=grants[0];assign borrow_release_ack=releases[0];
 generate if(ENABLE!=0&&PREINSTALL_ENABLE!=0)begin:observed_protected_rows
  // Observational exports of the ORIGINAL decoded protected rows. No mirror
  // descriptor storage and no force/write into another authority.
  for(genvar k=0;k<8;k=k+1)begin:descriptor
   assign descriptor_readback[k*64+:64]=u_bridge.on.d[k];
  end
  assign descriptor_mask=u_bridge.on.d[8][7:0];
  wire [8:0] descriptor_errors;
  for(genvar k=0;k<9;k=k+1)assign descriptor_errors[k]=|u_bridge.on.dec[k][65:64];
  assign descriptor_good=!(|descriptor_errors);
  assign actual_lease_frame=u_shared_owner.on.frame[72:0];
 end else begin:no_observation
  assign descriptor_readback=0;assign descriptor_mask=0;
  assign descriptor_good=0;assign actual_lease_frame=0;
 end endgenerate
 ot_hbm_formatter_preinstall #(.ENABLE(32'(ENABLE!=0&&PREINSTALL_ENABLE!=0)), .ENTRY_PC(ENTRY_PC),.SCORE_SOURCE(SCORE_SOURCE),.ID_SOURCE(ID_SOURCE),
  .ARENA_BASE(ARENA_BASE),.ARENA_LIMIT(ARENA_LIMIT),.SINK_BASE(SINK_BASE),.SINK_LIMIT(SINK_LIMIT),.CAPACITY_BYTES(CAPACITY_BYTES)) u_preinstall(
  .clk(clk),.por_n(por_n),.warm_req(warm_req),.actual_cp_frame({pos,token,gen,job}),
  .begin_v(preinstall_begin_v),.begin_r(preinstall_begin_r),.begin_frame(preinstall_begin_frame),
  .score_plane_base(preinstall_score_base),.id_plane_base(preinstall_id_base),
  .capacity_bytes(preinstall_capacity),.occupied_records(preinstall_occupied_records),
  .layer(preinstall_layer),.candidate_source_layer(preinstall_candidate_source_layer),.candidate_masked(preinstall_candidate_masked),
  .descriptor_readback(descriptor_readback),.descriptor_mask(descriptor_mask),.descriptor_good(descriptor_good),
  .record_v(preinstall_record_v),.record_r(preinstall_record_r),.record_kind(preinstall_record_kind),
  .record_rank(preinstall_record_rank),.record_base(preinstall_record_base),.record_end(preinstall_record_end),.record_frame(preinstall_record_frame),
  .other_writer_v(preinstall_other_writer_v),.other_writer_base(preinstall_other_writer_base),.other_writer_end(preinstall_other_writer_end),
  .lease_v(pre_lease),.lease_granted(grants[0]),.lease_frame(actual_lease_frame),.provider_fault(arb_fault|provider_fault),
  .source_v(preinstall_source_v),.source_r(preinstall_source_r),.source_frame(preinstall_source_frame),
  .source_rank(preinstall_source_rank),.source_plane(preinstall_source_plane),.source_word(preinstall_source_word),.source_data(preinstall_source_data),
  .source_ACK_v(preinstall_source_ACK_v),.source_ACK_r(preinstall_source_ACK_r),.source_ACK_frame(preinstall_source_ACK_frame),
  .source_ACK_rank(preinstall_source_ACK_rank),.source_ACK_plane(preinstall_source_ACK_plane),.source_ACK_word(preinstall_source_ACK_word),
  .m_req_v(pre_req_v),.m_req_r(pre_req_r),.m_req_we(pre_req_we),.m_req_addr(pre_req_addr),.m_req_data(pre_req_data),.m_req_strb(pre_req_strb),.m_req_tag(pre_req_tag),
  .m_rsp_v(b_rsp_v&&selected_pre),.m_rsp_r(pre_rsp_r),.m_rsp_we(b_rsp_we),.m_rsp_data(b_rsp_data),.m_rsp_tag(b_rsp_tag),
  .reservation_v(reservation_v),.reservation_r(reservation_r),.reservation_checked(reservation_checked),.reservation_exclusive(reservation_exclusive),
  .reservation_frame(reservation_frame),.reservation_descriptor(reservation_descriptor),
  .gather_retained(retained),.gather_sink_visible(sink_visible),.gather_frame({held_pos,held_token,held_gen,held_job}),
  .consumer_reverse_v(consumer_reverse_v),.consumer_reverse_r(consumer_reverse_r),.consumer_reverse_frame(consumer_reverse_frame),
  .consumer_sink_ACK_drained(consumer_sink_ACK_drained),.source_reverse_v(source_reverse_v),.source_reverse_r(source_reverse_r),
  .source_reverse_checked(source_reverse_checked),.source_drained(source_drained),.source_reverse_frame(source_reverse_frame),
  .borrower_release_ACK(releases[0]),.retained(preinstall_retained),.held_frame(preinstall_frame),
  .warm_ack(preinstall_warm_ack),.fault(preinstall_fault),.ce(preinstall_ce),.due(preinstall_due));
 assign borrow_fault=arb_fault|provider_fault;
 assign formatter_lease_valid=(ENABLE!=0)&&borrow_granted&&retained&&!fault;
 assign formatter_lease_frame={held_pos,held_token,held_gen,held_job};
 assign fault=bridge_fault|arb_fault|preinstall_fault|(ENABLE!=0&&provider_fault);
 assign peer_lease_granted=grants[2:1];assign peer_release_r=releases[2:1];
 assign p_req_rdy={all_req_rdy[3:2],all_req_rdy[0]};assign b_req_rdy=all_req_rdy[1]&&!selected_pre;
 assign p_rsp_v={all_rsp_v[3:2],all_rsp_v[0]};assign b_rsp_v=all_rsp_v[1];
 assign p_rsp_we={all_rsp_we[3:2],all_rsp_we[0]};assign b_rsp_we=all_rsp_we[1];
 assign p_rsp_tag={all_rsp_tag[63:32],all_rsp_tag[15:0]};assign b_rsp_tag=all_rsp_tag[31:16];
 assign p_rsp_data={all_rsp_data[1023:512],all_rsp_data[255:0]};assign b_rsp_data=all_rsp_data[511:256];
 ot_hbm_integrated_gather_bridge #(.ENABLE(ENABLE),.VM_AW(VM_AW)) u_bridge (
  .fault(bridge_fault),.m_req_v(b_req_v),.m_req_rdy(b_req_rdy),.m_req_we(b_req_we),
  .m_req_addr(b_req_addr),.m_req_wdata(b_req_wdata),.m_req_wstrb(b_req_wstrb),.m_req_tag(b_req_tag),
  .m_rsp_rdy(b_rsp_rdy),.m_rsp_we(b_rsp_we),.m_rsp_tag(b_rsp_tag),.m_rsp_data(b_rsp_data),
  .desc_v(desc_v&&(!use_pre||(!preinstall_retained&&!warm_req))),.desc_r(original_desc_r),
  .start_v(start_v&&(!use_pre||reservation_checked)),
  .installed_book_valid(installed_book_valid&&(!use_pre||reservation_checked)),
  .m_rsp_v(b_rsp_v&&!selected_pre),.*);
 ot_hbm_integrated_sm0_borrow #(.ENABLE(ENABLE)) u_shared_owner (
  .clk(clk),.por_n(por_n),.native_clients_drained(native_clients_drained),.cdc_drained(cdc_drained),
  .lease_v({peer_lease_v,use_pre?pre_lease:borrow_v}),.borrower_quiet({peer_quiet,!retained}),
  .lease_job({peer_lease_job,use_pre?preinstall_frame[31:0]:job}),.lease_gen({peer_lease_gen,use_pre?preinstall_frame[35:32]:gen}),
  .lease_token({peer_lease_token,use_pre?preinstall_frame[52:36]:token}),.lease_pos({peer_lease_pos,use_pre?preinstall_frame[72:53]:pos}),.lease_granted(grants),
  .release_v({peer_release_v,borrow_release}),.release_r(releases),
  .release_job({peer_release_job,held_job}),.release_gen({peer_release_gen,held_gen}),
  .release_token({peer_release_token,held_token}),.release_pos({peer_release_pos,held_pos}),
  .req_v({p_req_v[2:1],x_req_v,p_req_v[0]}),.req_rdy(all_req_rdy),
  .req_we({p_req_we[2:1],x_req_we,p_req_we[0]}),
  .req_addr({p_req_addr[95:32],x_req_addr,p_req_addr[31:0]}),
  .req_wdata({p_req_wdata[767:256],x_req_data,p_req_wdata[255:0]}),
  .req_wstrb({p_req_wstrb[95:32],x_req_strb,p_req_wstrb[31:0]}),
  .req_tag({p_req_tag[47:16],x_req_tag,p_req_tag[15:0]}),
  .rsp_v(all_rsp_v),.rsp_rdy({p_rsp_rdy[2:1],x_rsp_r,p_rsp_rdy[0]}),
  .rsp_we(all_rsp_we),.rsp_tag(all_rsp_tag),.rsp_data(all_rsp_data),
  .idle(shared_idle),.fault(arb_fault),.*);
endmodule
