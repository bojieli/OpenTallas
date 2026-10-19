`timescale 1ns/1ps
// HKV-HRORD: member-local reset landing for qkd_host_boot_dispatch_debt.
// Original member unchanged. Asynchronous assertion; release +3 ck edges.
// Zero steady-state cycles; compiler must reserve three reset-release edges before traffic.
// QKD_HR_ORD_RR_MUTANT bypasses relay for the reset-contract witness.
module qkd_host_boot_dispatch_debt_rr #(
  parameter integer MUT=0
)(
 input wire ck,
 input wire ck_order,
 input wire rst_n,
 input wire boot_release,
 input wire [289:0] ing,
 output wire ing_cr,
 output wire [289:0] kv,
 input wire kv_cr,
 output wire [282:0] hb,
 input wire hb_cr,
 output wire image_check,
 input wire [127:0] acks,
 output wire prefix_v,
 output wire [31:0] landed,
 output wire [31:0] issued,
 output wire fault,
 output wire dispatch_quiet,
 output wire order_quiet
);
 wire rst_q;
`ifdef QKD_HR_ORD_RR_MUTANT
 assign rst_q = rst_n;
`else
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst_relay(.clk(ck),.rst_n_in(rst_n),.rst_n(rst_q));
`endif
 qkd_host_boot_dispatch_debt #(.MUT(MUT)) u_m(
  .ck(ck),
  .ck_order(ck_order),
  .rst_n(rst_q),
  .boot_release(boot_release),
  .ing(ing),
  .ing_cr(ing_cr),
  .kv(kv),
  .kv_cr(kv_cr),
  .hb(hb),
  .hb_cr(hb_cr),
  .image_check(image_check),
  .acks(acks),
  .prefix_v(prefix_v),
  .landed(landed),
  .issued(issued),
  .fault(fault),
  .dispatch_quiet(dispatch_quiet),
  .order_quiet(order_quiet));
endmodule
