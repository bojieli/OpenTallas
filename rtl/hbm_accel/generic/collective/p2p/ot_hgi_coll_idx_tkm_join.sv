`timescale 1ns/1ps
`default_nettype none
// Actual typed selector -> native staging -> compiler-mode ingress -> qslots
// -> native KMAX2048 TKM. Component composition; no normative host/program or
// remote rank fabric is substituted. G1 local production shape is executable;
// a G>1 calendar requires actual other-rank transport before qualification.
module ot_hgi_coll_idx_tkm_join(
 input wire rst_n,
 input wire clk_selector_control,
 input wire [3:0] clk_selector_quarter,
 input wire [11:0] clk_selector_mem,
 input wire clk_staging_control,
 input wire [7:0] clk_staging_mem,
 input wire clk_ingress,clk_ingest_check,
 input wire [1:0] clk_qslots,
 input wire clk_tkm_control,clk_tkm_buffer,
 input wire [31:0] clk_tkm_tile,
 input wire [3:0] selector_op,
 input wire [1:0] selector_pass,
 input wire [7:0] selector_addr,
 input wire [2367:0] score_line,
 input wire staging_clear,staging_ingest,staging_flush,staging_emit,
 input wire [3:0] staging_group,
 input wire [7:0] rank,gbase,
 input wire ingress_mode_idx,
 input wire [3:0] ingress_expected,
 input wire [3:0] vm_v,
 input wire [2179:0] vm_d,
 input wire [3:0] qslot_capture,qslot_sink,
 input wire [7:0] qslot_select,
 input wire tkm_start,
 input wire [7:0] cfg_g,
 input wire [12:0] cfg_k,cfg_nout,
 input wire [39:0] cfg_obase,cfg_rbase,
 input wire cfg_has_r,
 input wire [3:0] tkm_del_slot,
 output wire w_v,
 output wire [39:0] w_addr,
 output wire [15:0] w_mask,
 output wire [511:0] w_data,
 output wire busy,done,fault,
 output wire [31:0] stat_cycles,
 output wire [9:0] selected_count,
 output wire [3:0] idx_launch_v,tkm_input_v,
 output wire [2179:0] idx_launch_data,tkm_input_data
);
 wire [3:0] selected_v;
 wire [2367:0] selected_line;
 wire selector_fault,staging_fault,ingress_fault,qslots_fault,tkm_fault,ingest_fault;
 wire [3:0] ingress_v;wire [2179:0] ingress_d;
 wire [3:0] qfault_kind;
 ot_hbm_idx_selector_static u_selector(.clk_ctl(clk_selector_control),.clk_q(clk_selector_quarter),
  .clk_mem(clk_selector_mem),.rst_n(rst_n),.op(selector_op),.pass(selector_pass),.addr(selector_addr),
  .k(10'd512),.in_line(score_line),.out_v(),.out_line(),.threshold_observe(),
  .selected_v(selected_v),.selected_line(selected_line),.selected_observe(),.fault(selector_fault));
 ot_hbm_idx_topk_link_static u_staging(.clk(clk_staging_control),.clk_mem(clk_staging_mem),.rst_n(rst_n),
  .clear(staging_clear),.ingest_v(staging_ingest),.selected_line(selected_line),
  .flush(staging_flush),.emit_v(staging_emit),.emit_group(staging_group),.rank(rank),.gbase(gbase),
  .tx_v(idx_launch_v),.tx(idx_launch_data),.fault(staging_fault),.selected_count(selected_count));
 // The complete selected bitmap is checked; it never chooses a later issue.
 ot_hgi_coll_idx_ingest_check u_ingest_check(.clk(clk_ingest_check),.rst_n(rst_n),
  .slot(staging_ingest),.actual(selected_v),.fault(ingest_fault));
 ot_hgi_coll_vm_idx_ingress u_ingress(.clk(clk_ingress),.rst_n(rst_n),.mode_idx(ingress_mode_idx),
  .expected_v(ingress_expected),.vm_v(vm_v),.vm_d(vm_d),.idx_v(idx_launch_v),.idx_d(idx_launch_data),
  .out_v(ingress_v),.out_d(ingress_d),.fault(ingress_fault));
 ot_hgi_coll_qslots #(.NS(4),.ND(4),.SELW(2)) u_transport(
  .clk_capture(clk_qslots[0]),.clk_output(clk_qslots[1]),.rst_n(rst_n),.src_v(ingress_v),.src_d(ingress_d),
  .capture_slot(qslot_capture),.sink_slot(qslot_sink),.sink_select(qslot_select),
  .dst_v(tkm_input_v),.dst_d(tkm_input_data),.fault(qslots_fault),.fault_kind(qfault_kind));
 ot_hgi_coll_tkm_static #(.KMAX(2048)) u_tkm(.clk(clk_tkm_control),.tile_clk(clk_tkm_tile),.buffer_clk(clk_tkm_buffer),
  .rst_n(rst_n),.start(tkm_start),.cfg_n(12'd512),.cfg_k(cfg_k),.cfg_nout(cfg_nout),
  .cfg_g(cfg_g),.cfg_gbase(gbase),.cfg_pf(16'd64),.cfg_obase(cfg_obase),.cfg_rbase(cfg_rbase),.cfg_has_r(cfg_has_r),
  .del_slot(tkm_del_slot),.del_valid(tkm_input_v),.del_flit(tkm_input_data),
  .w_v(w_v),.w_addr(w_addr),.w_mask(w_mask),.w_data(w_data),
  .busy(busy),.done(done),.fault(tkm_fault),.stat_cycles(stat_cycles));
 assign fault=selector_fault|staging_fault|ingest_fault|ingress_fault|qslots_fault|tkm_fault;
endmodule
module ot_hgi_coll_idx_ingest_check(
 input wire clk,rst_n,slot,input wire [3:0] actual,output reg fault
);
 always @(posedge clk or negedge rst_n)
  if(!rst_n)fault<=0;
  else if(actual!={4{slot}})fault<=1;
endmodule
`default_nettype wire
