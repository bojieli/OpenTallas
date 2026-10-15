`timescale 1ns/1ps
`default_nettype none
module dsfd_vm_static_read_q0(input wire ck,rst_n,
 input wire[255:0] i_data,
 input wire[3:0] i_valid,
 input wire[7:0] i_expected,
 input wire[11:0] i_sel,
 input wire i_su1_group,
 input wire[63:0] i_peer_data,
 input wire i_peer_valid,
 output wire[7:0] o_partial_valid,
 output wire[511:0] o_data,
 output wire fault);
 wire[15:0] select_fixed;
 assign select_fixed[0+:2]=i_sel[0+:2];
 assign select_fixed[2+:2]=i_sel[2+:2];
 assign select_fixed[4+:2]=2'd2;
 assign select_fixed[6+:2]=2'd3;
 assign select_fixed[8+:2]=i_sel[4+:2];
 assign select_fixed[10+:2]=i_sel[6+:2];
 assign select_fixed[12+:2]=i_sel[8+:2];
 assign select_fixed[14+:2]=i_sel[10+:2];
 dsfd_vm_static_read_leaf #(.G(0)) leaf(.ck(ck),.rst_n(rst_n),.i_data(i_data),.i_valid(i_valid),.i_sel(select_fixed),.i_expected(i_expected),.i_su1_group(i_su1_group),.i_peer_data(i_peer_data),.i_peer_valid(i_peer_valid),.o_peer_data(),.o_peer_valid(),.o_partial_valid(o_partial_valid),.o_data(o_data),.fault(fault));
endmodule
module dsfd_vm_static_read_q1(input wire ck,rst_n,
 input wire[255:0] i_data,
 input wire[3:0] i_valid,
 input wire[8:0] i_expected,
 input wire[9:0] i_sel,
 input wire i_su1_group,
 output wire[63:0] o_peer_data,
 output wire o_peer_valid,
 output wire[8:0] o_partial_valid,
 output wire[511:0] o_data,
 output wire fault);
 wire[17:0] select_fixed;
 assign select_fixed[0+:2]=i_sel[0+:2];
 assign select_fixed[2+:2]=2'd0;
 assign select_fixed[4+:2]=2'd1;
 assign select_fixed[6+:2]=2'd2;
 assign select_fixed[8+:2]=2'd3;
 assign select_fixed[10+:2]=i_sel[2+:2];
 assign select_fixed[12+:2]=i_sel[4+:2];
 assign select_fixed[14+:2]=i_sel[6+:2];
 assign select_fixed[16+:2]=i_sel[8+:2];
 dsfd_vm_static_read_leaf #(.G(1)) leaf(.ck(ck),.rst_n(rst_n),.i_data(i_data),.i_valid(i_valid),.i_sel(select_fixed),.i_expected(i_expected),.i_su1_group(i_su1_group),.i_peer_data(64'd0),.i_peer_valid(1'b0),.o_peer_data(o_peer_data),.o_peer_valid(o_peer_valid),.o_partial_valid(o_partial_valid),.o_data(o_data),.fault(fault));
endmodule
module dsfd_vm_static_read_q2(input wire ck,rst_n,
 input wire[255:0] i_data,
 input wire[3:0] i_valid,
 input wire[7:0] i_expected,
 input wire[7:0] i_sel,
 output wire[7:0] o_partial_valid,
 output wire[511:0] o_data,
 output wire fault);
 wire[15:0] select_fixed;
 assign select_fixed[0+:2]=2'd0;
 assign select_fixed[2+:2]=2'd1;
 assign select_fixed[4+:2]=2'd2;
 assign select_fixed[6+:2]=2'd3;
 assign select_fixed[8+:2]=i_sel[0+:2];
 assign select_fixed[10+:2]=i_sel[2+:2];
 assign select_fixed[12+:2]=i_sel[4+:2];
 assign select_fixed[14+:2]=i_sel[6+:2];
 dsfd_vm_static_read_leaf #(.G(2)) leaf(.ck(ck),.rst_n(rst_n),.i_data(i_data),.i_valid(i_valid),.i_sel(select_fixed),.i_expected(i_expected),.i_su1_group(1'b0),.i_peer_data(64'd0),.i_peer_valid(1'b0),.o_peer_data(),.o_peer_valid(),.o_partial_valid(o_partial_valid),.o_data(o_data),.fault(fault));
endmodule
module dsfd_vm_static_read_q3(input wire ck,rst_n,
 input wire[255:0] i_data,
 input wire[3:0] i_valid,
 input wire[7:0] i_expected,
 input wire[7:0] i_sel,
 output wire[7:0] o_partial_valid,
 output wire[511:0] o_data,
 output wire fault);
 wire[15:0] select_fixed;
 assign select_fixed[0+:2]=2'd0;
 assign select_fixed[2+:2]=2'd1;
 assign select_fixed[4+:2]=2'd2;
 assign select_fixed[6+:2]=2'd3;
 assign select_fixed[8+:2]=i_sel[0+:2];
 assign select_fixed[10+:2]=i_sel[2+:2];
 assign select_fixed[12+:2]=i_sel[4+:2];
 assign select_fixed[14+:2]=i_sel[6+:2];
 dsfd_vm_static_read_leaf #(.G(3)) leaf(.ck(ck),.rst_n(rst_n),.i_data(i_data),.i_valid(i_valid),.i_sel(select_fixed),.i_expected(i_expected),.i_su1_group(1'b0),.i_peer_data(64'd0),.i_peer_valid(1'b0),.o_peer_data(),.o_peer_valid(),.o_partial_valid(o_partial_valid),.o_data(o_data),.fault(fault));
endmodule
module dsfd_vm_static_read_q4(input wire ck,rst_n,
 input wire[255:0] i_data,
 input wire[3:0] i_valid,
 input wire[1:0] i_expected,
 input wire[3:0] i_sel,
 output wire[1:0] o_partial_valid,
 output wire[127:0] o_data,
 output wire fault);
 wire[3:0] select_fixed;
 assign select_fixed[0+:2]=i_sel[0+:2];
 assign select_fixed[2+:2]=i_sel[2+:2];
 dsfd_vm_static_read_leaf #(.G(4)) leaf(.ck(ck),.rst_n(rst_n),.i_data(i_data),.i_valid(i_valid),.i_sel(select_fixed),.i_expected(i_expected),.i_su1_group(1'b0),.i_peer_data(64'd0),.i_peer_valid(1'b0),.o_peer_data(),.o_peer_valid(),.o_partial_valid(o_partial_valid),.o_data(o_data),.fault(fault));
endmodule
module dsfd_vm_static_read_q5(input wire ck,rst_n,
 input wire[255:0] i_data,
 input wire[3:0] i_valid,
 input wire[7:0] i_expected,
 input wire[7:0] i_sel,
 output wire[7:0] o_partial_valid,
 output wire[511:0] o_data,
 output wire fault);
 wire[15:0] select_fixed;
 assign select_fixed[0+:2]=2'd0;
 assign select_fixed[2+:2]=2'd1;
 assign select_fixed[4+:2]=2'd2;
 assign select_fixed[6+:2]=2'd3;
 assign select_fixed[8+:2]=i_sel[0+:2];
 assign select_fixed[10+:2]=i_sel[2+:2];
 assign select_fixed[12+:2]=i_sel[4+:2];
 assign select_fixed[14+:2]=i_sel[6+:2];
 dsfd_vm_static_read_leaf #(.G(5)) leaf(.ck(ck),.rst_n(rst_n),.i_data(i_data),.i_valid(i_valid),.i_sel(select_fixed),.i_expected(i_expected),.i_su1_group(1'b0),.i_peer_data(64'd0),.i_peer_valid(1'b0),.o_peer_data(),.o_peer_valid(),.o_partial_valid(o_partial_valid),.o_data(o_data),.fault(fault));
endmodule
module dsfd_vm_static_read_q6(input wire ck,rst_n,
 input wire[255:0] i_data,
 input wire[3:0] i_valid,
 input wire[3:0] i_expected,
 output wire[3:0] o_partial_valid,
 output wire[255:0] o_data,
 output wire fault);
 wire[7:0] select_fixed;
 assign select_fixed[0+:2]=2'd0;
 assign select_fixed[2+:2]=2'd1;
 assign select_fixed[4+:2]=2'd2;
 assign select_fixed[6+:2]=2'd3;
 dsfd_vm_static_read_leaf #(.G(6)) leaf(.ck(ck),.rst_n(rst_n),.i_data(i_data),.i_valid(i_valid),.i_sel(select_fixed),.i_expected(i_expected),.i_su1_group(1'b0),.i_peer_data(64'd0),.i_peer_valid(1'b0),.o_peer_data(),.o_peer_valid(),.o_partial_valid(o_partial_valid),.o_data(o_data),.fault(fault));
endmodule
module dsfd_vm_static_read_q7(input wire ck,rst_n,
 input wire[255:0] i_data,
 input wire[3:0] i_valid,
 input wire[3:0] i_expected,
 output wire[3:0] o_partial_valid,
 output wire[255:0] o_data,
 output wire fault);
 wire[7:0] select_fixed;
 assign select_fixed[0+:2]=2'd0;
 assign select_fixed[2+:2]=2'd1;
 assign select_fixed[4+:2]=2'd2;
 assign select_fixed[6+:2]=2'd3;
 dsfd_vm_static_read_leaf #(.G(7)) leaf(.ck(ck),.rst_n(rst_n),.i_data(i_data),.i_valid(i_valid),.i_sel(select_fixed),.i_expected(i_expected),.i_su1_group(1'b0),.i_peer_data(64'd0),.i_peer_valid(1'b0),.o_peer_data(),.o_peer_valid(),.o_partial_valid(o_partial_valid),.o_data(o_data),.fault(fault));
endmodule
`default_nettype wire
