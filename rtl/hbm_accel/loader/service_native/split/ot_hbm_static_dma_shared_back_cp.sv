`default_nettype none
// PREP: explicit successor to the whole ot_hgi_dma_back_static_vp4_banks_cp
// hard master. One unchanged collar/table, reset relays and STORE banks/core;
// the commanded LOAD consumer is external to this cut. Existing physical BACK
// views do not cover this interface. New parent pins/routes/cell typing must be
// planned before physical adoption. All clocks are related same logical clock.
// Host paging remains <=128 literal commands, no hidden large programme ROM.
module ot_hbm_static_dma_shared_back_cp #(
 parameter [35:0] STACK_BYTES=36'd22500000000,
 parameter integer RR_RT=80
)(
 input wire clk,rst_n,clk_cp,clk_rst,input wire[7:0]clk_bank,
 input wire[1:0]stk,strap_vm_qid,input wire[7:0]tgt,
 input wire cfg_v,input wire[7:0]cfg_target,input wire[11:0]cfg_addr,input wire[255:0]cfg_data,
 input wire desc_v,input wire[11:0]desc_base,input wire[12:0]desc_limit,input wire[15:0]desc_loops,input wire launch_v,
 output wire cp_configured,cp_fault,cp_active,
 output wire mv_src,mv_done,mv_fault,quiet,busy,
 output wire[135:0]rq,input wire[2055:0]rr,
 output wire wb_reserve_v,wb_reserve_bank,wb_fill_bank,
 output wire[15:0]wb_reserve_epoch,wb_fill_epoch,output wire[11:0]wb_reserve_sectors,
 output wire[31:0]wb_reserve_base,output wire wb_fill_start,input wire wb_ready,
 output wire[2311:0]wd,input wire[11:0]wa,
 // New explicit cut boundary: no command retiming here. LOAD endpoint reset is
 // direct reset-relay output E+4. STORE controller adds two internal reset
 // capture edges (effective E+6); LOAD consumer has no such capture here.
 // Leaf-local reset relays add their own declared edges. Command dates use
 // cycle_o; host programming/launch must honor all endpoint cold guards.
 output wire load_cmd_v_o,output wire[307:0]cmd_o,output wire[31:0]cycle_o,
 output wire load_rst_n_o,command_fault_o,
 input wire load_busy_i,load_fault_i,load_done_i
);
 wire[8:0]rst_bk_n;wire[0:0]rst_ctl_q;
 ot_rst_relay #(.REGIONS(9),.SYNC_STAGES(2),.TREE_STAGES(1))u_rst_bk(.clk(clk_rst),.rst_n_in(rst_n),.rst_n(rst_bk_n));
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(2))u_rst_ctl(.clk(clk_rst),.rst_n_in(rst_n),.rst_n(rst_ctl_q));
 assign load_rst_n_o=rst_ctl_q[0];
 wire cmd_v,store_v,store_busy,store_fault,store_done,store_quiet,dispatch_fault;
 wire[135:0]rq_local;
 assign busy=store_busy|load_busy_i;
 assign quiet=store_quiet&&!load_busy_i;
 assign mv_done=store_done|load_done_i;
 assign mv_fault=store_fault|load_fault_i|dispatch_fault;
 assign command_fault_o=dispatch_fault|cp_fault;
 ot_hgi_dma_back_cp_collar u_cp(
 .clk(clk_cp),.rst_n(rst_bk_n[8]),.tgt(tgt),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
 .tgt_active(busy),.tgt_fault(mv_fault),.cmd_v(cmd_v),.cmd(cmd_o),.cycle(cycle_o),.configured(cp_configured),.fault(cp_fault),.active(cp_active));
 ot_hbm_static_dma_cmd_dispatch u_dispatch(.clk(clk),.rst_n(rst_ctl_q[0]),.cmd_v_i(cmd_v),.cmd_i(cmd_o),
 .busy_i(busy),.backend_fault_i(store_fault|load_fault_i),.load_v_o(load_cmd_v_o),.store_v_o(store_v),.fault_o(dispatch_fault));
 ot_hgi_dma_back_static_vp4_banks_rs #(.STACK_BYTES(STACK_BYTES),.RR_RT(RR_RT))u_dbk(
 .clk(clk),.rst_ctl_n(rst_ctl_q[0]),.rst_bank_n(rst_bk_n[7:0]),.stk(stk),.clk_bank(clk_bank),.cycle(cycle_o),
 .mv_v(store_v),.mv(cmd_o[290:64]),.issue_at(cmd_o[31:0]),.drain_at(cmd_o[63:32]),.mv_wb_bank(cmd_o[291]),.mv_wb_epoch(cmd_o[307:292]),
 .mv_src(mv_src),.mv_done(store_done),.mv_fault(store_fault),.quiet(store_quiet),.busy(store_busy),.rq(rq_local),.rr(rr),
 .wb_reserve_v(wb_reserve_v),.wb_reserve_bank(wb_reserve_bank),.wb_fill_bank(wb_fill_bank),.wb_reserve_epoch(wb_reserve_epoch),
 .wb_fill_epoch(wb_fill_epoch),.wb_reserve_sectors(wb_reserve_sectors),.wb_reserve_base(wb_reserve_base),.wb_fill_start(wb_fill_start),
 .wb_ready(wb_ready),.wd(wd),.wa(wa));
 ot_hbm_static_dma_vm_rq_context u_vm_context(.rq_i(rq_local),.strap_vm_qid(strap_vm_qid),.rq_o(rq));
endmodule
`default_nettype wire
