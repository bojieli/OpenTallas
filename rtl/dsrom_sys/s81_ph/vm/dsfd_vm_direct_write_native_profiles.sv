`timescale 1ns/1ps
`default_nettype none
// Source-identical transparent native profile boundaries; no added FF/cycle.
// Production slice must select actual closed profile by assigned pins; no view aliases.
module dsfd_vm_static_write_capture128_W(
 input wire ck,
 input wire rst_n,
 input wire i_v,
 input wire i_we,
 input wire [13:0] i_row,
 input wire [3:0] i_mask,
 input wire [127:0] i_data,
 input wire [7:0] i_tag,
 output wire o_v,
 output wire o_we,
 output wire [13:0] o_row,
 output wire [3:0] o_mask,
 output wire [127:0] o_data,
 output wire [7:0] o_tag
);
dsfd_vm_static_write_capture128 u_leaf (
 .ck(ck),
 .rst_n(rst_n),
 .i_v(i_v),
 .i_we(i_we),
 .i_row(i_row),
 .i_mask(i_mask),
 .i_data(i_data),
 .i_tag(i_tag),
 .o_v(o_v),
 .o_we(o_we),
 .o_row(o_row),
 .o_mask(o_mask),
 .o_data(o_data),
 .o_tag(o_tag)
);
endmodule
module dsfd_vm_static_scatter_b8_out_B8 #(parameter integer PIPE=0) (
 input wire ck,
 input wire rst_n,
 input wire [7:0] i_v,
 input wire [7:0] i_we,
 input wire [111:0] i_row,
 input wire [31:0] i_mask,
 input wire [1023:0] i_data,
 input wire [63:0] i_tag,
 output wire [7:0] o_v,
 output wire [7:0] o_we,
 output wire [71:0] o_addr,
 output wire [31:0] o_mask,
 output wire [1023:0] o_data,
 output wire [63:0] o_tag,
 output wire fault
);
dsfd_vm_static_scatter_b8_out #(.BANK_BASE(8),.PIPE(PIPE)) u_leaf (
 .ck(ck),
 .rst_n(rst_n),
 .i_v(i_v),
 .i_we(i_we),
 .i_row(i_row),
 .i_mask(i_mask),
 .i_data(i_data),
 .i_tag(i_tag),
 .o_v(o_v),
 .o_we(o_we),
 .o_addr(o_addr),
 .o_mask(o_mask),
 .o_data(o_data),
 .o_tag(o_tag),
 .fault(fault)
);
endmodule
module dsfd_vm_static_scatter_b8_out_B16 #(parameter integer PIPE=0) (
 input wire ck,
 input wire rst_n,
 input wire [7:0] i_v,
 input wire [7:0] i_we,
 input wire [111:0] i_row,
 input wire [31:0] i_mask,
 input wire [1023:0] i_data,
 input wire [63:0] i_tag,
 output wire [7:0] o_v,
 output wire [7:0] o_we,
 output wire [71:0] o_addr,
 output wire [31:0] o_mask,
 output wire [1023:0] o_data,
 output wire [63:0] o_tag,
 output wire fault
);
dsfd_vm_static_scatter_b8_out #(.BANK_BASE(16),.PIPE(PIPE)) u_leaf (
 .ck(ck),
 .rst_n(rst_n),
 .i_v(i_v),
 .i_we(i_we),
 .i_row(i_row),
 .i_mask(i_mask),
 .i_data(i_data),
 .i_tag(i_tag),
 .o_v(o_v),
 .o_we(o_we),
 .o_addr(o_addr),
 .o_mask(o_mask),
 .o_data(o_data),
 .o_tag(o_tag),
 .fault(fault)
);
endmodule
module dsfd_vm_static_scatter_b8_out_B24 #(parameter integer PIPE=0) (
 input wire ck,
 input wire rst_n,
 input wire [7:0] i_v,
 input wire [7:0] i_we,
 input wire [111:0] i_row,
 input wire [31:0] i_mask,
 input wire [1023:0] i_data,
 input wire [63:0] i_tag,
 output wire [7:0] o_v,
 output wire [7:0] o_we,
 output wire [71:0] o_addr,
 output wire [31:0] o_mask,
 output wire [1023:0] o_data,
 output wire [63:0] o_tag,
 output wire fault
);
dsfd_vm_static_scatter_b8_out #(.BANK_BASE(24),.PIPE(PIPE)) u_leaf (
 .ck(ck),
 .rst_n(rst_n),
 .i_v(i_v),
 .i_we(i_we),
 .i_row(i_row),
 .i_mask(i_mask),
 .i_data(i_data),
 .i_tag(i_tag),
 .o_v(o_v),
 .o_we(o_we),
 .o_addr(o_addr),
 .o_mask(o_mask),
 .o_data(o_data),
 .o_tag(o_tag),
 .fault(fault)
);
endmodule
`default_nettype wire
