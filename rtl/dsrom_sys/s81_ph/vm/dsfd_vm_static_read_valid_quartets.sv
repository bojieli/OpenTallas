`timescale 1ns/1ps
`default_nettype none
module dsfd_vm_static_read_v0(input wire ck,rst_n,
 input wire[7:0] i_expected,
 input wire[39:0] i_slot,
 input wire[63:0] i_partial_valid,
 input wire[7:0] i_fault,
 input wire[7:0] i_peer_valid,
 output wire[7:0] o_valid,
 output wire fault);
 dsfd_vm_static_read_valid #(.G(0)) leaf(.ck(ck),.rst_n(rst_n),.i_expected(i_expected),.i_slot(i_slot),.i_partial_valid(i_partial_valid),.i_peer_valid(i_peer_valid),.i_fault(i_fault),.o_valid(o_valid),.fault(fault));
endmodule
module dsfd_vm_static_read_v1(input wire ck,rst_n,
 input wire[8:0] i_expected,
 input wire[44:0] i_slot,
 input wire[71:0] i_partial_valid,
 input wire[7:0] i_fault,
 output wire[7:0] o_valid,
 output wire fault);
 dsfd_vm_static_read_valid #(.G(1)) leaf(.ck(ck),.rst_n(rst_n),.i_expected(i_expected),.i_slot(i_slot),.i_partial_valid(i_partial_valid),.i_peer_valid(8'd0),.i_fault(i_fault),.o_valid(o_valid),.fault(fault));
endmodule
module dsfd_vm_static_read_v2(input wire ck,rst_n,
 input wire[7:0] i_expected,
 input wire[39:0] i_slot,
 input wire[63:0] i_partial_valid,
 input wire[7:0] i_fault,
 output wire[7:0] o_valid,
 output wire fault);
 dsfd_vm_static_read_valid #(.G(2)) leaf(.ck(ck),.rst_n(rst_n),.i_expected(i_expected),.i_slot(i_slot),.i_partial_valid(i_partial_valid),.i_peer_valid(8'd0),.i_fault(i_fault),.o_valid(o_valid),.fault(fault));
endmodule
module dsfd_vm_static_read_v3(input wire ck,rst_n,
 input wire[7:0] i_expected,
 input wire[39:0] i_slot,
 input wire[63:0] i_partial_valid,
 input wire[7:0] i_fault,
 output wire[7:0] o_valid,
 output wire fault);
 dsfd_vm_static_read_valid #(.G(3)) leaf(.ck(ck),.rst_n(rst_n),.i_expected(i_expected),.i_slot(i_slot),.i_partial_valid(i_partial_valid),.i_peer_valid(8'd0),.i_fault(i_fault),.o_valid(o_valid),.fault(fault));
endmodule
module dsfd_vm_static_read_v4(input wire ck,rst_n,
 input wire[1:0] i_expected,
 input wire[9:0] i_slot,
 input wire[15:0] i_partial_valid,
 input wire[7:0] i_fault,
 output wire[1:0] o_valid,
 output wire fault);
 dsfd_vm_static_read_valid #(.G(4)) leaf(.ck(ck),.rst_n(rst_n),.i_expected(i_expected),.i_slot(i_slot),.i_partial_valid(i_partial_valid),.i_peer_valid(8'd0),.i_fault(i_fault),.o_valid(o_valid),.fault(fault));
endmodule
module dsfd_vm_static_read_v5(input wire ck,rst_n,
 input wire[7:0] i_expected,
 input wire[39:0] i_slot,
 input wire[63:0] i_partial_valid,
 input wire[7:0] i_fault,
 output wire[4:0] o_valid,
 output wire fault);
 dsfd_vm_static_read_valid #(.G(5)) leaf(.ck(ck),.rst_n(rst_n),.i_expected(i_expected),.i_slot(i_slot),.i_partial_valid(i_partial_valid),.i_peer_valid(8'd0),.i_fault(i_fault),.o_valid(o_valid),.fault(fault));
endmodule
module dsfd_vm_static_read_v6(input wire ck,rst_n,
 input wire[3:0] i_expected,
 input wire[19:0] i_slot,
 input wire[31:0] i_partial_valid,
 input wire[7:0] i_fault,
 output wire[3:0] o_valid,
 output wire fault);
 dsfd_vm_static_read_valid #(.G(6)) leaf(.ck(ck),.rst_n(rst_n),.i_expected(i_expected),.i_slot(i_slot),.i_partial_valid(i_partial_valid),.i_peer_valid(8'd0),.i_fault(i_fault),.o_valid(o_valid),.fault(fault));
endmodule
module dsfd_vm_static_read_v7(input wire ck,rst_n,
 input wire[3:0] i_expected,
 input wire[19:0] i_slot,
 input wire[31:0] i_partial_valid,
 input wire[7:0] i_fault,
 output wire[3:0] o_valid,
 output wire fault);
 dsfd_vm_static_read_valid #(.G(7)) leaf(.ck(ck),.rst_n(rst_n),.i_expected(i_expected),.i_slot(i_slot),.i_partial_valid(i_partial_valid),.i_peer_valid(8'd0),.i_fault(i_fault),.o_valid(o_valid),.fault(fault));
endmodule
`default_nettype wire
