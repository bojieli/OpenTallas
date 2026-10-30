`default_nettype none
// PREP actual one-collar CW308 + existing ROLE89 + selected VMKS fill boundary.
// Accepted future LOADcontext precedes COPYonly prefetch; STATIC consumeradmit
// is issue_at-2. Existing RAW begin/start/data stay on their old path, with
// only raw_fill_v_o replacing their valid wires. No-context RAW traffic is
// bitexact, including malformed fills. COPYfirstfill must follow COPYbegin+2
// physical/path constraint; firststep never waits. Actual RAW+COPY lifecycle,
// host multi-target arm/launch dates and regional routing still need proof.
module ot_hbm_static_load_native_provider_quad #(
 parameter integer SOURCE_QUAD=2,SOURCE_STACK=2,SOURCE_LOW_QUAD=2
)(
 input wire clk,rst_n,input wire cmd_v,input wire[307:0]cmd,input wire[31:0]cycle,input wire command_fault_i,
 // Selected PC/VMKS/refresh/RAW sticky faults, returned by a bounded static
 // path before the fixed completion deadline. Never infer success from ACKs
 // while the actual source mechanism reports failure.
 input wire source_fault_i,
 input wire calendar_v_i,input wire[88:0]calendar_payload_i,
 input wire[15:0]fill_v,fill_bank,input wire[95:0]fill_slot,input wire[255:0]fill_epoch,input wire[4095:0]fill_data,
 input wire[31:0]vm_dq_done_i,vm_fault_i,
 output wire[15:0]raw_fill_v_o,
 output wire dated_step_o,admit_o,output wire[280:0]vm_dq,output wire[15:0]block_ready,
 output wire[7:0]leaf_fault,output wire busy_o,fault_o,load_done_o
);
 wire held_v,context_v,hold_busy,hold_fault,route_fault,calendar_fault,consumer_fault,consumer_busy,consumer_done;
 wire[307:0]held_cmd,context_cmd;wire[15:0]copy_fv;wire copy_cv;wire[88:0]copy_cp;
 wire rv,rb,bv,bb;wire[15:0]re,be;wire[14:0]br;wire[3:0]bc;
 ot_hbm_static_load_dated_cmd_hold dated_context(.clk(clk),.rst_n(rst_n),.cmd_v_i(cmd_v),.cmd_i(cmd),.cycle_i(cycle),
 .consumer_done_i(load_done_o),.consumer_fault_i(command_fault_i|source_fault_i|route_fault|calendar_fault|consumer_fault),
 .consumer_cmd_v_o(held_v),.consumer_cmd_o(held_cmd),.context_v_o(context_v),.context_cmd_o(context_cmd),.busy_o(hold_busy),.fault_o(hold_fault));
 ot_hbm_static_load_raw_copy_fill_route fill_route(.clk(clk),.rst_n(rst_n),.context_v_i(context_v),.context_cmd_i(context_cmd),
 .calendar_v_i(calendar_v_i),.calendar_payload_i(calendar_payload_i),.fill_v_i(fill_v),.fill_bank_i(fill_bank),.fill_epoch_i(fill_epoch),
 .raw_fill_v_o(raw_fill_v_o),.copy_fill_v_o(copy_fv),.copy_calendar_v_o(copy_cv),.copy_calendar_payload_o(copy_cp),.fault_o(route_fault));
 ot_hbm_static_load_window_calendar #(.REQUIRE_RAW_BEGIN(0))window_calendar(
 .clk(clk),.rst_n(rst_n),.calendar_v_i(copy_cv),.payload_i(copy_cp),.load_busy_i(consumer_busy),
 .load_fault_i(command_fault_i|source_fault_i|hold_fault|route_fault|consumer_fault),.release_v_o(rv),.release_buffer_o(rb),.release_epoch_o(re),
 .begin_v_o(bv),.begin_buffer_o(bb),.begin_epoch_o(be),.begin_row_o(br),.begin_col_o(bc),.fault_o(calendar_fault));
 ot_hbm_static_load_cmd_provider_quad #(.SOURCE_QUAD(SOURCE_QUAD),.VM_COMMIT_AUDIT(1),.SOURCE_STACK(SOURCE_STACK),.SOURCE_LOW_QUAD(SOURCE_LOW_QUAD))consumer(
 .clk(clk),.rst_n(rst_n),.cmd_v(held_v),.cmd(held_cmd),.cycle(cycle),.command_fault_i(command_fault_i|source_fault_i|hold_fault|route_fault|calendar_fault),
 .begin_v(bv),.begin_bank(bb),.begin_epoch(be),.begin_row(br),.begin_col(bc),
 .fill_v(copy_fv),.fill_bank(fill_bank),.fill_slot(fill_slot),.fill_epoch(fill_epoch),.fill_data(fill_data),
 .release_v_i(rv),.release_buffer_i(rb),.release_epoch_i(re),.vm_dq_done_i(vm_dq_done_i),.vm_fault_i(vm_fault_i),
 .dated_step_o(dated_step_o),.admit_o(admit_o),.vm_dq(vm_dq),.block_ready(block_ready),.leaf_fault(leaf_fault),
 .busy_o(consumer_busy),.fault_o(consumer_fault),.load_done_o(consumer_done));
 assign busy_o=hold_busy|consumer_busy;
 assign fault_o=source_fault_i|hold_fault|route_fault|calendar_fault|consumer_fault;
 assign load_done_o=consumer_done&&!hold_fault&&!route_fault&&!calendar_fault&&!command_fault_i&&!source_fault_i;
endmodule
`default_nettype wire
