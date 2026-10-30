`default_nettype none
// SOURCE-ONLY native target integration. Existing CW308/RELF2 command format:
// {epoch16,buffer1,resolved227,drain_at32,issue_at32}. No new ISA or target ID.
// Caller supplies window-safe m1 runs, actual begin/fill/release and VMslot6.
// Bankdone feedback is this DMA's ONLY slot6 producer: drain prior DQ writes,
// hold sole producer ownership until fixed drain/status settle, or supply
// producer-qualified ACKs from an exact regional owner-tag return partner.
// One target stores <=128 literal run descriptors; whole-programme paging/
// compression/dispatch remains explicit. This is not a 95313-entry ROM claim.
module ot_hbm_static_load_cp_provider_quad #(parameter integer SOURCE_QUAD=2,VM_COMMIT_AUDIT=1)(
 input wire clk,rst_n,input wire[7:0]tgt,
 input wire cfg_v,input wire[7:0]cfg_target,input wire[11:0]cfg_addr,input wire[255:0]cfg_data,
 input wire desc_v,input wire[11:0]desc_base,input wire[12:0]desc_limit,input wire[15:0]desc_loops,input wire launch_v,
 input wire begin_v,begin_bank,input wire[15:0]begin_epoch,input wire[14:0]begin_row,input wire[3:0]begin_col,
 input wire[15:0]fill_v,fill_bank,input wire[95:0]fill_slot,input wire[255:0]fill_epoch,input wire[4095:0]fill_data,
 input wire release_v_i,release_buffer_i,input wire[15:0]release_epoch_i,
 input wire[31:0]vm_dq_done_i,vm_fault_i,
 output wire configured,cp_active,output wire[31:0]cycle,
 output wire[280:0]vm_dq,output wire[15:0]block_ready,output wire[7:0]leaf_fault,
 output wire busy_o,output wire fault_o,load_done_o
);

 wire cmd_v,cp_fault,dated_step,admit;wire[307:0]cmd;wire[226:0]move=cmd[290:64];
 ot_hgi_dma_back_cp_collar cp(.clk(clk),.rst_n(rst_n),.tgt(tgt),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
 .tgt_active(busy_o),.tgt_fault(fault_o),.cmd_v(cmd_v),.cmd(cmd),.cycle(cycle),.configured(configured),.fault(cp_fault),.active(cp_active));
 ot_hbm_static_load_cmd_provider_quad #(.SOURCE_QUAD(SOURCE_QUAD),.VM_COMMIT_AUDIT(VM_COMMIT_AUDIT)) command_provider(
 .clk(clk),.rst_n(rst_n),.cmd_v(cmd_v),.cmd(cmd),.cycle(cycle),.command_fault_i(cp_fault),
 .begin_v(begin_v),.begin_bank(begin_bank),.begin_epoch(begin_epoch),.begin_row(begin_row),.begin_col(begin_col),
 .fill_v(fill_v),.fill_bank(fill_bank),.fill_slot(fill_slot),.fill_epoch(fill_epoch),.fill_data(fill_data),
 .release_v_i(release_v_i),.release_buffer_i(release_buffer_i),.release_epoch_i(release_epoch_i),
 .vm_dq_done_i(vm_dq_done_i),.vm_fault_i(vm_fault_i),.dated_step_o(dated_step),.admit_o(admit),
 .vm_dq(vm_dq),.block_ready(block_ready),.leaf_fault(leaf_fault),.busy_o(busy_o),.fault_o(fault_o),.load_done_o(load_done_o));
endmodule
`default_nettype wire
