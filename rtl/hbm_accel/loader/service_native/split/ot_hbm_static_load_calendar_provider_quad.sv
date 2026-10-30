`default_nettype none
// PREP actual native command/calendar/PHY boundary for a private LOAD copy.
// No standalone resolved-desc, step, begin, metadata or release stimulus ports:
// cmd/cycle come from the shared wholeBACK collar, calendar is existing ROLE89,
// and fill comes from the real selected16PC VMKS group. Physical regional
// command/begin/fill/DQ/done/status transport still requires a planned event.
module ot_hbm_static_load_calendar_provider_quad #(
 parameter integer SOURCE_QUAD=2,SOURCE_STACK=2,SOURCE_LOW_QUAD=2
)(
 input wire clk,rst_n,input wire cmd_v,input wire[307:0]cmd,input wire[31:0]cycle,input wire command_fault_i,
 input wire calendar_v_i,input wire[88:0]calendar_payload_i,
 input wire[15:0]fill_v,fill_bank,input wire[95:0]fill_slot,input wire[255:0]fill_epoch,input wire[4095:0]fill_data,
 input wire[31:0]vm_dq_done_i,vm_fault_i,
 output wire dated_step_o,admit_o,output wire[280:0]vm_dq,output wire[15:0]block_ready,
 output wire[7:0]leaf_fault,output wire busy_o,fault_o,load_done_o
);
 wire rv,rb,bv,bb,calendar_fault,consumer_fault,consumer_done;
 wire[15:0]re,be;wire[14:0]br;wire[3:0]bc;
 ot_hbm_static_load_window_calendar window_calendar(
 .clk(clk),.rst_n(rst_n),.calendar_v_i(calendar_v_i),.payload_i(calendar_payload_i),
 .load_busy_i(busy_o),.load_fault_i(command_fault_i|consumer_fault),
 .release_v_o(rv),.release_buffer_o(rb),.release_epoch_o(re),
 .begin_v_o(bv),.begin_buffer_o(bb),.begin_epoch_o(be),.begin_row_o(br),.begin_col_o(bc),.fault_o(calendar_fault));
 ot_hbm_static_load_cmd_provider_quad #(.SOURCE_QUAD(SOURCE_QUAD),.VM_COMMIT_AUDIT(1),.SOURCE_STACK(SOURCE_STACK),.SOURCE_LOW_QUAD(SOURCE_LOW_QUAD)) consumer(
 .clk(clk),.rst_n(rst_n),.cmd_v(cmd_v),.cmd(cmd),.cycle(cycle),.command_fault_i(command_fault_i|calendar_fault),
 .begin_v(bv),.begin_bank(bb),.begin_epoch(be),.begin_row(br),.begin_col(bc),
 .fill_v(fill_v),.fill_bank(fill_bank),.fill_slot(fill_slot),.fill_epoch(fill_epoch),.fill_data(fill_data),
 .release_v_i(rv),.release_buffer_i(rb),.release_epoch_i(re),.vm_dq_done_i(vm_dq_done_i),.vm_fault_i(vm_fault_i),
 .dated_step_o(dated_step_o),.admit_o(admit_o),.vm_dq(vm_dq),.block_ready(block_ready),.leaf_fault(leaf_fault),
 .busy_o(busy_o),.fault_o(consumer_fault),.load_done_o(consumer_done));
 assign fault_o=calendar_fault|consumer_fault;
 assign load_done_o=consumer_done&&!calendar_fault&&!command_fault_i;
endmodule
`default_nettype wire
