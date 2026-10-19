`timescale 1ns/1ps
// HKV-HRORD: member-local reset landing for qkd_host_ingest_chain_pt.
// Original member unchanged. Asynchronous assertion; release +3 ck_map edges.
// Zero steady-state cycles; compiler must reserve three reset-release edges before traffic.
// QKD_HR_ORD_RR_MUTANT bypasses relay for the reset-contract witness.
module qkd_host_ingest_chain_pt_rr #(
  parameter integer ORDER_MUT=0
)(
 input wire ck_map,
 input wire ck_sum,
 input wire ck_order,
 input wire rst_n,
 input wire [289:0] ing,
 output wire ing_cr,
 output wire [1163:0] chain_f,
 input wire [127:0] chain_c,
 input wire [127:0] chain_a,
 input wire [3:0] chain_fault_i,
 input wire [127:0] slice_ack,
 output wire [127:0] all_acks,
 output wire marker_v,
 output wire [65:0] marker,
 input wire marker_cr,
 output wire [31:0] issued,
 output wire [31:0] landed,
 output wire map_fault,
 output wire [3:0] chain_fault,
 output wire [7:0] ack_n,
 output wire [7:0] physical_ack_n,
 output wire order_fault
);
 wire rst_q;
`ifdef QKD_HR_ORD_RR_MUTANT
 assign rst_q = rst_n;
`else
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst_relay(.clk(ck_map),.rst_n_in(rst_n),.rst_n(rst_q));
`endif
 qkd_host_ingest_chain_pt #(.ORDER_MUT(ORDER_MUT)) u_m(
  .ck_map(ck_map),
  .ck_sum(ck_sum),
  .ck_order(ck_order),
  .rst_n(rst_q),
  .ing(ing),
  .ing_cr(ing_cr),
  .chain_f(chain_f),
  .chain_c(chain_c),
  .chain_a(chain_a),
  .chain_fault_i(chain_fault_i),
  .slice_ack(slice_ack),
  .all_acks(all_acks),
  .marker_v(marker_v),
  .marker(marker),
  .marker_cr(marker_cr),
  .issued(issued),
  .landed(landed),
  .map_fault(map_fault),
  .chain_fault(chain_fault),
  .ack_n(ack_n),
  .physical_ack_n(physical_ack_n),
  .order_fault(order_fault));
endmodule
