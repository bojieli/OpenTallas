`default_nettype none
// Direct native-parameter views: preserve existing shell flops and calendars.
module ot_hbm_idx_vm_query_static_n12__rt171(
 input wire clk,
 input wire rst_n,
 input wire [1:0] sid,
 input wire weight_slot,
 input wire query_slot,
 input wire [6:0] query_index,
 input wire [15:0] weight_sector,
 input wire [15:0] query_sector,
 output wire [135:0] vm_rq,
 input wire [2055:0] vm_rr,
 output wire block_v,
 output wire [4:0] block_head,
 output wire [1:0] block_number,
 output wire [1023:0] block_data,
 output wire [15:0] head_weight,
 output wire fault
);
 ot_hbm_idx_vm_query_static_n12 #(.VM_RT_EXTRA(171)) u_core(
  .clk(clk),
  .rst_n(rst_n),
  .sid(sid),
  .weight_slot(weight_slot),
  .query_slot(query_slot),
  .query_index(query_index),
  .weight_sector(weight_sector),
  .query_sector(query_sector),
  .vm_rq(vm_rq),
  .vm_rr(vm_rr),
  .block_v(block_v),
  .block_head(block_head),
  .block_number(block_number),
  .block_data(block_data),
  .head_weight(head_weight),
  .fault(fault)
 );
endmodule
module ot_hbm_idx_vm_query_static_n12__rt173(
 input wire clk,
 input wire rst_n,
 input wire [1:0] sid,
 input wire weight_slot,
 input wire query_slot,
 input wire [6:0] query_index,
 input wire [15:0] weight_sector,
 input wire [15:0] query_sector,
 output wire [135:0] vm_rq,
 input wire [2055:0] vm_rr,
 output wire block_v,
 output wire [4:0] block_head,
 output wire [1:0] block_number,
 output wire [1023:0] block_data,
 output wire [15:0] head_weight,
 output wire fault
);
 ot_hbm_idx_vm_query_static_n12 #(.VM_RT_EXTRA(173)) u_core(
  .clk(clk),
  .rst_n(rst_n),
  .sid(sid),
  .weight_slot(weight_slot),
  .query_slot(query_slot),
  .query_index(query_index),
  .weight_sector(weight_sector),
  .query_sector(query_sector),
  .vm_rq(vm_rq),
  .vm_rr(vm_rr),
  .block_v(block_v),
  .block_head(block_head),
  .block_number(block_number),
  .block_data(block_data),
  .head_weight(head_weight),
  .fault(fault)
 );
endmodule
`default_nettype wire
