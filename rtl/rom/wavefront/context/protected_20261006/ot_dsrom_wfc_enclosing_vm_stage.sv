`timescale 1ns/1ps
// Dedicated minimum enclosing source. Canonical cfg/prompt/whole-stage and
// engine/journal inputs MUST come from their actual owners. No native parent
// is modified. Whole-stage producer retains its result until actual WFC ACK.
module ot_dsrom_wfc_enclosing_vm_stage #(
 parameter ENABLE=0,SOURCE=0,STRUCTURAL=0
)(
 input wire clk,rst_n,advance,memory_step,read_step,write_step,
 output wire vm_we,vm_re,
 output wire [14:0]vm_waddr,vm_raddr,
 output wire [511:0]vm_wdata,
 input wire [511:0]vm_rq,
 output wire [9:0]vm_owner_user,
 output wire [20:0]vm_owner_pos,
 output wire vm_read_capture,vm_owner_conflict,
 output wire [9:0]vm_read_owner_user,
 output wire [20:0]vm_read_owner_pos,
 input wire [9:0]cfg_users,
 input wire [20:0]cfg_prompt_len,cfg_gen_len,
 input wire [20:0]pr_q,
 input wire pr_qk,
 output wire pr_re,
 output wire [9:0]pr_user,
 output wire [20:0]pr_pos,
 output wire [3:0]pr_blk,
 input wire in_valid,in_last,out_ready,
 input wire [511:0]in_data,
 output wire in_ready,out_valid,out_last,
 output wire [511:0]out_data,
 input wire bl_rx_valid,bl_rx_last,bl_tx_ready,
 input wire [511:0]bl_rx_data,
 output wire bl_rx_ready,bl_tx_valid,bl_tx_last,
 output wire [511:0]bl_tx_data,
 input wire rcfg_we,
 input wire [7:0]rcfg_dest,
 input wire [2:0]rcfg_mask,
 input wire [15:0]stage_epoch,
 input wire [13:0]stage_entry,
 output wire stage_request_v,
 input wire stage_request_ready,
 output wire [46:0]stage_request_identity,
 output wire [20:0]stage_request_token,
 output wire [13:0]stage_request_entry,
 input wire whole_stage_v,
 input wire [46:0]whole_stage_identity,
 input wire [20:0]whole_stage_token,
 input wire [31:0]whole_stage_value,
 output wire whole_stage_accepted,
 input wire context_restored,native_idle,native_fragment_done,
 input wire c8_write_quiet,c8_write_quarantine,c8_write_fault,coll_busy,
 output wire context_v,
 output wire [46:0]context_identity,
 output wire [20:0]context_token,
 output wire [13:0]context_entry,
 output wire native_start,
 output wire [20:0]native_token,native_pos,
 output wire [13:0]native_entry,
 output wire [9:0]native_user,
 output wire [46:0]native_identity,
 output wire [20:0]captured_token,captured_pos,
 output wire [13:0]captured_pc,
 output wire c8_retire_v,
 output wire [46:0]c8_retire_identity,
 output wire tok_valid,
 output wire [9:0]tok_user,users_done,
 output wire [20:0]tok_pos,tok_id,
 output wire busy,fault
);
 generate if(ENABLE)begin:g_stage
   wire core_start,core_busy,accepted;
   wire [20:0]core_token,core_pos;
   wire [9:0]core_user,owner_user;
   wire [29:0]kv_base;
   wire proto_fault,rtr_overflow;wire [31:0]rtr_drops;
   wire wf_issue,wf_reject,wf_squash,c8_ready,c8_active,c8_poison;
   reg owned=0,issued=0,launched=0,poison=0,owner_capture_pending=0;
   reg [81:0]request;
   wire [15:0]rq_epoch;wire [9:0]rq_user;wire [20:0]rq_pos,rq_token;wire [13:0]rq_entry;
   assign {rq_epoch,rq_user,rq_pos,rq_token,rq_entry}=request;
   assign stage_request_identity={rq_epoch,rq_user,rq_pos};
   assign stage_request_token=rq_token;assign stage_request_entry=rq_entry;
   // One transaction is jointly admitted by both real consumers. Valid remains
   // asserted while either owner stalls; neither side gets a partial request.
   wire offer=owned&&!issued&&!poison&&!owner_capture_pending;
   assign stage_request_v=offer&&c8_ready&&advance;
   wire take=stage_request_v&&stage_request_ready;
   wire health=c8_write_quiet&&!c8_write_quarantine&&!c8_write_fault&&!coll_busy;
   wire matching_result=owned&&issued&&launched&&whole_stage_identity==stage_request_identity;
   wire result_v=whole_stage_v&&matching_result&&!poison&&!c8_poison;
   assign whole_stage_accepted=accepted&&result_v&&health&&advance;
   assign busy=owned||core_busy||c8_active;
   assign fault=poison||c8_poison||proto_fault||rtr_overflow;
   always @(posedge clk)begin
     // Accepted owner metadata and debt survive warm reset; poison blocks
     // automatic reuse. Actual producer retirement alone clears owned.
     if(!rst_n)begin if(owned)poison<=1;end
     else if(!poison)begin
       if(c8_write_quarantine||c8_write_fault||c8_poison||
          ((vm_we||vm_re)&&coll_busy)||
          (whole_stage_v&&(!owned||!issued||whole_stage_identity!=stage_request_identity)))poison<=1;
       if(native_start)begin
         if(!native_idle||native_identity!=stage_request_identity)poison<=1;
         else launched<=1;
       end
       if(owner_capture_pending)begin request[65:56]<=owner_user;owner_capture_pending<=0;end
       if(take)issued<=1;
       if(whole_stage_accepted)begin owned<=0;issued<=0;launched<=0;end
       if(core_start&&advance)begin
         if(owned&&!whole_stage_accepted)poison<=1;
         else begin
           owned<=1;issued<=0;launched<=0;owner_capture_pending<=!STRUCTURAL;
           request<={stage_epoch,owner_user,core_pos,core_token,stage_entry};
         end
       end
     end
   end
   ot_dsrom_c8_stage_context u_c8(
     .clk(clk),.rst_n(rst_n),.offer_v(offer&&stage_request_ready&&advance),.offer_ready(c8_ready),
     .offer_token(rq_token),.offer_pos(rq_pos),.offer_user(rq_user),.offer_epoch(rq_epoch),.offer_entry(rq_entry),
     .context_v(context_v),.context_restored(context_restored),.context_identity(context_identity),
     .context_token(context_token),.context_entry(context_entry),
     .engine_start(native_start),.engine_token(native_token),.engine_pos(native_pos),
     .engine_user(native_user),.engine_entry(native_entry),.engine_identity(native_identity),
     .engine_done(native_fragment_done),.write_journal_quiet(c8_write_quiet),
     .write_quarantine(c8_write_quarantine),.write_fault(c8_write_fault),
     .retire_v(c8_retire_v),.retire_identity(c8_retire_identity),.active(c8_active),.quarantine(c8_poison));
   ot_dsrom_wfc_core_capture u_core_capture(.clk(clk),.native_idle(native_idle),.start(native_start),
     .token(native_token),.pos(native_pos),.entry(native_entry),
     .tok_r(captured_token),.pos_r(captured_pos),.pc(captured_pc));
   ot_dsrom_wfc_parent_enclosed_vm #(.SOURCE(SOURCE),.XWORDS(SOURCE?41:46),
     .DECODED_READ(STRUCTURAL),.CONTROL_PIPE(STRUCTURAL),.QUEUE_SHIFT(STRUCTURAL),
     .HEADER_LOCAL(STRUCTURAL),.PREFIX_INC(STRUCTURAL))u_boundary(
     .clk(clk),.rst_n(rst_n),.advance(advance),.memory_step(memory_step),.read_step(read_step),.write_step(write_step),
     .vm_owner_user(vm_owner_user),.vm_owner_pos(vm_owner_pos),.vm_read_capture(vm_read_capture),.vm_owner_conflict(vm_owner_conflict),.vm_read_owner_user(vm_read_owner_user),.vm_read_owner_pos(vm_read_owner_pos),.cfg_users(cfg_users),.cfg_prompt_len(cfg_prompt_len),.cfg_gen_len(cfg_gen_len),
     .in_valid(in_valid),.in_last(in_last),.in_data(in_data),.in_ready(in_ready),
     .out_valid(out_valid),.out_last(out_last),.out_data(out_data),.out_ready(out_ready),
     .core_start(core_start),.core_token(core_token),.core_pos(core_pos),.core_user(core_user),
     .core_owner_user(owner_user),.core_done_accepted(accepted),.core_done(result_v),
     .core_next_token(whole_stage_token),.core_next_val(whole_stage_value),.core_busy(core_busy),
     .pr_re(pr_re),.pr_user(pr_user),.pr_pos(pr_pos),.pr_blk(pr_blk),.pr_q(pr_q),.pr_qk(pr_qk),
     .c8_write_quiet(c8_write_quiet),.c8_write_quarantine(c8_write_quarantine||poison||c8_poison),
     .c8_write_fault(c8_write_fault),.coll_busy(coll_busy),.*);
 end else begin:g_disabled
   assign {vm_we,vm_re,vm_waddr,vm_raddr,vm_wdata,vm_owner_user,vm_owner_pos,vm_read_capture,vm_owner_conflict,vm_read_owner_user,vm_read_owner_pos}=0;
   assign {pr_re,pr_user,pr_pos,pr_blk,in_ready,out_valid,out_last,out_data,
     bl_rx_ready,bl_tx_valid,bl_tx_last,bl_tx_data,stage_request_v,stage_request_identity,
     stage_request_token,stage_request_entry,whole_stage_accepted,context_v,context_identity,
     context_token,context_entry,native_start,native_token,native_pos,native_entry,native_user,
     native_identity,captured_token,captured_pos,captured_pc,c8_retire_v,c8_retire_identity,
     tok_valid,tok_user,users_done,tok_pos,tok_id,busy,fault}=0;
 end endgenerate
endmodule
