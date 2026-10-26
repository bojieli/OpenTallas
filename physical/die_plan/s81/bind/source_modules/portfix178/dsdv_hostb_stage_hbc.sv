`timescale 1ns/1ps
`default_nettype none
// dsdv_hostb_stage_hbc (STEWARD-TOK-S81-HOSTCTX 2026-10-21): the s0N HBE stage
// receiver WITH its production expected-context source.  Gap G-HOST-CONTEXT:
// dsdv_hostb_stage/dsdv_hostb_rx take configured/TID16/epoch32/programme64/
// user/position/token/header-stage/header_slot/receiver_edge as EXTERNAL pins
// and gate the first HBE header against them, but no on-die block drove them
// (benches only; the 53-bit KS word {start,user10,tok21,pos21} cannot carry
// TID/epoch/programme).  This parent closes the loop structurally with the
// owner-accepted HBC1 one-context architecture (Codex c2bb78aa8, source-only):
//
//   from_prev ring -> dsdv_hbc1_loader (addressed HBC1 LOAD/body/COMMIT records,
//   HOST authority on the same HFWD kind-6 lane, static boot-counter slots,
//   CRC32C + shape checks, shadow->active on explicit COMMIT, one-shot)
//   -> active_fields (flops) -> dsdv_hbc1_affine_book (slices + fixed-date
//   slot compares against the loaded receiver epoch) -> dsdv_hostb_stage pins.
//
// Every context pin is a flop output (active field banks / epoch counter) or a
// compare of flops; no credit, ready or completion feedback; HBC records are
// consumed by the loader and never reach the RX.  Stage/rank are straps.
// The first HBE header is therefore accepted only if it matches the context the
// HOST loaded; a wrong TID/epoch/programme header raises RX fault[4] and is
// never written.  ENABLE=0 keeps the original dsdv_hostb_stage wiring.
// job_active must be the actual MU/issuer busy of this stage (same net the RX
// already takes): the loader refuses LOAD/COMMIT while a job is active.
// COLLB-HOST 10-21 (die bind prep): the TX forward/return slots are the book's own
// static dates (next_forward_slot, source_return_TX_slot = return_send_slot+1, the
// edge on which a dsdv_hostb_return return_ring registered at return_send_slot is
// presented), no longer external pins: nothing outside may tie them.
// The book reads the loader's kept same-edge copies context_valid_bk / receiver_edge_bk
// (native census: context_valid 35 loads, receiver_edge bits 33-38 loads > 32).
// S81/PORTFIX-FLT 10-25 (S81 DECISION 4): ONE output `fault` = the registered sticky OR of the stage RX/TX faults
// (dsdv_hostb_stage fault[11:0]), the HBC1 loader faults (hbc_fault[7:0]) and the return-emitter faults
// (return_fault[3:0]).  The status outputs arm_mask / arm_commit (starter arm state), context_valid and the 48-b
// receiver_edge / boot_edge counters are no longer ports (internal nets of the same names, bench taps only).
// Reset: the sticky fault is control state, cleared by rst_n (landed by its own 2-stage reset sync).
module dsdv_hostb_stage_hbc #(
 parameter integer ENABLE=0, LOCAL_STAGE=255, LOCAL_RANK=4, PHASE_BOUND=0,
 parameter integer RETURN_LOCAL=0, RETURN_REQUIRE_KIT=1, VARIABLE_WORDS=0, ALLOW_RELOAD=0,
 parameter [47:0] RETURN_ARRIVAL_DEADLINE=48'hffffffffffff,
 parameter [63:0] CLOCK_RESET_ID=64'd0,
 parameter [47:0] BOOT_HEADER_EDGE=48'hffffffffffff,
 parameter [47:0] BOOT_COMMIT_EDGE=48'hffffffffffff
)(
 input wire ck,rst_n,job_active,starter_armed,
 input wire [1103:0] from_prev,local_ro,return_ro,
 input wire [76:0] status_t_host,input wire [53:0] status_t_kd,
 output wire [1103:0] to_local,next_ro,
 output wire [514:0] f_host,output wire [52:0] ks_descriptor,
 output wire [2:0] ks_slot,
 output reg fault);
 wire [3:0] return_fault;wire [5:0] arm_mask;wire arm_commit;wire [11:0] stage_fault;
 wire context_valid;wire [47:0] receiver_edge,boot_edge;wire [7:0] hbc_fault;
 wire fault_rn;ot_reset_sync #(.ASYNC_STAGES(2)) u_fault_rst(.clk(ck),.async_rst_n(rst_n),.sync_rst_n(fault_rn));
 always @(posedge ck or negedge fault_rn)
  if(!fault_rn)fault<=1'b0;else fault<=fault|(|stage_fault)|(|hbc_fault)|(|return_fault);
 generate if(ENABLE==0)begin:g_original
  dsdv_hostb_stage #(.ENABLE(0)) u_stage(.ck(ck),.rst_n(rst_n),.configured(1'b0),.local_stage(8'd0),.local_rank(2'd0),
   .epoch_id(32'd0),.programme_id(64'd0),.receiver_edge(48'd0),.transit_body_edge(48'd0),.expected_tid(16'd0),
   .expected_header_stage(8'd0),.expected_user(10'd0),.expected_position(21'd0),.expected_token(21'd0),
   .header_slot(1'b0),.job_active(job_active),.starter_armed(starter_armed),.from_prev(from_prev),.local_ro(local_ro),
   .return_ro(return_ro),.forward_slot(1'b0),.return_slot(1'b0),.to_local(to_local),.next_ro(next_ro),
   .f_host(f_host),.ks_descriptor(ks_descriptor),.ks_slot(ks_slot),.arm_mask(arm_mask),.arm_commit(arm_commit),.fault(stage_fault));
  assign return_fault=0;
  assign context_valid=0;assign receiver_edge=0;assign boot_edge=0;assign hbc_fault=0;
 end else begin:g_hbc
  wire [1103:0] after_hbc;wire [511:0] active_fields;wire context_valid_bk;wire [47:0] receiver_edge_bk;
  (* keep_hierarchy="yes" *) dsdv_hbc1_loader #(.ENABLE(1),.LOCAL_STAGE(LOCAL_STAGE),.LOCAL_RANK(LOCAL_RANK),
   .PHASE_BOUND(PHASE_BOUND),.VARIABLE_WORDS(VARIABLE_WORDS),.ALLOW_RELOAD(ALLOW_RELOAD),.CLOCK_RESET_ID(CLOCK_RESET_ID),.BOOT_HEADER_EDGE(BOOT_HEADER_EDGE),
   .BOOT_COMMIT_EDGE(BOOT_COMMIT_EDGE)) u_loader(.ck(ck),.rst_n(rst_n),.ring_i(from_prev),.job_active(job_active),
   .local_ring(after_hbc),.active_fields(active_fields),.context_valid(context_valid),
   .receiver_edge(receiver_edge),.boot_edge(boot_edge),.fault(hbc_fault),
   .context_valid_bk(context_valid_bk),.receiver_edge_bk(receiver_edge_bk));
  wire [15:0] tid;wire [9:0] user_id;wire [20:0] position,token;wire [31:0] epoch_id;wire [63:0] programme_id;
  wire [7:0] data_stage;wire [1:0] data_rank;wire next_header_slot,next_forward_slot,source_return_tx_slot,status_sample_slot,return_send_slot;wire [47:0] transit_body_edge;
  (* keep_hierarchy="yes" *) dsdv_hbc1_affine_book u_book(.ck(ck),.rst_n(rst_n),.context_valid(context_valid_bk),
   .fields(active_fields),.receiver_edge(receiver_edge_bk),.tid(tid),.user_id(user_id),.position(position),.token(token),
   .epoch_id(epoch_id),.programme_id(programme_id),.expected_data_stage(data_stage),.expected_data_rank(data_rank),
   .next_header_slot(next_header_slot),.next_forward_slot(next_forward_slot),.prev_header_slot(),.prev_forward_slot(),
   .status_sample_slot(status_sample_slot),.return_send_slot(return_send_slot),.source_return_TX_slot(source_return_tx_slot),.transit_body_edge(transit_body_edge));
  wire [1103:0] actual_return;
  if(RETURN_LOCAL!=0)begin:g_return
   // This date is a compiled UPSTREAM arrival authority, not local PREV input.
   // Refuse an unprofiled route rather than fabricating a deadline.
   initial if(RETURN_ARRIVAL_DEADLINE==48'hffffffffffff)
    $fatal(1,"HBC return requires explicit compiled upstream arrival date");
   dsdv_hostb_return u_return(.ck(ck),.rst_n(rst_n),.configured(context_valid),
    .sample_slot(status_sample_slot),.send_slot(return_send_slot),.require_kit(RETURN_REQUIRE_KIT!=0),
    .context_valid(context_valid),.stage_id(LOCAL_STAGE[7:0]),.rank_id(LOCAL_RANK[1:0]),
    .tid(tid),.user_id(user_id),.position(position),.token(token),.epoch_id(epoch_id),
    .arrival_deadline(RETURN_ARRIVAL_DEADLINE),.programme_id(programme_id),
    .t_host(status_t_host),.t_kd(status_t_kd),.return_ring(actual_return),.fault(return_fault));
  end else begin:g_external_return
   assign actual_return=return_ro;assign return_fault=0;
  end
  dsdv_hostb_stage #(.ENABLE(1)) u_stage(.ck(ck),.rst_n(rst_n),.configured(context_valid),
   .local_stage(LOCAL_STAGE[7:0]),.local_rank(LOCAL_RANK[1:0]),.epoch_id(epoch_id),.programme_id(programme_id),
   .receiver_edge(receiver_edge),.transit_body_edge(transit_body_edge),.expected_tid(tid),
   .expected_header_stage(data_stage),.expected_user(user_id),.expected_position(position),.expected_token(token),
   .header_slot(next_header_slot),.job_active(job_active),.starter_armed(starter_armed),.from_prev(after_hbc),
   .local_ro(local_ro),.return_ro(actual_return),.forward_slot(next_forward_slot),.return_slot(source_return_tx_slot),
   .to_local(to_local),.next_ro(next_ro),.f_host(f_host),.ks_descriptor(ks_descriptor),.ks_slot(ks_slot),
   .arm_mask(arm_mask),.arm_commit(arm_commit),.fault(stage_fault));
 end endgenerate
endmodule
`default_nettype wire
