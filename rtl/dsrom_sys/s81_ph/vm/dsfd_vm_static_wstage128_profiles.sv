`timescale 1ns/1ps
`default_nettype none
// Source-identical transparent native write-edge profile boundaries (claude S81 VM F1, 2026-10-15): no added FF/cycle.
// Each wrapper is a distinct hard master (own pin plan / bank-base constant); the production wsched selects the closed
// profile by its assigned pins and bank base. No view aliases between profiles.
module dsfd_vm_static_wstage128_E(
 input wire ck,
 input wire rst_n,
 input wire [2:0] capture_v,
 input wire [5:0] capture_slot,
 input wire [41:0] capture_row,
 input wire [11:0] capture_mask,
 input wire [383:0] capture_data,
 input wire [23:0] capture_tag,
 input wire drain_v,
 input wire [1:0] drain_slot,
 output wire o_v,
 output wire [13:0] o_row,
 output wire [3:0] o_mask,
 output wire [127:0] o_data,
 output wire [7:0] o_tag,
 output wire fault
);
dsfd_vm_static_wstage128 #(.DEPTH(3)) u_leaf (
 .ck(ck),
 .rst_n(rst_n),
 .capture_v(capture_v),
 .capture_slot(capture_slot),
 .capture_row(capture_row),
 .capture_mask(capture_mask),
 .capture_data(capture_data),
 .capture_tag(capture_tag),
 .drain_v(drain_v),
 .drain_slot(drain_slot),
 .o_v(o_v),
 .o_row(o_row),
 .o_mask(o_mask),
 .o_data(o_data),
 .o_tag(o_tag),
 .fault(fault)
);
endmodule
module dsfd_vm_static_wstage128_W(
 input wire ck,
 input wire rst_n,
 input wire [2:0] capture_v,
 input wire [5:0] capture_slot,
 input wire [41:0] capture_row,
 input wire [11:0] capture_mask,
 input wire [383:0] capture_data,
 input wire [23:0] capture_tag,
 input wire drain_v,
 input wire [1:0] drain_slot,
 output wire o_v,
 output wire [13:0] o_row,
 output wire [3:0] o_mask,
 output wire [127:0] o_data,
 output wire [7:0] o_tag,
 output wire fault
);
dsfd_vm_static_wstage128 #(.DEPTH(3)) u_leaf (
 .ck(ck),
 .rst_n(rst_n),
 .capture_v(capture_v),
 .capture_slot(capture_slot),
 .capture_row(capture_row),
 .capture_mask(capture_mask),
 .capture_data(capture_data),
 .capture_tag(capture_tag),
 .drain_v(drain_v),
 .drain_slot(drain_slot),
 .o_v(o_v),
 .o_row(o_row),
 .o_mask(o_mask),
 .o_data(o_data),
 .o_tag(o_tag),
 .fault(fault)
);
endmodule
`default_nettype wire
