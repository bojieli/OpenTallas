`timescale 1ns/1ps
`default_nettype none
module dsfd_vm_static_fsr_b0(
 input wire ck,rst_n,input wire[17:0] i_v,input wire[251:0] i_row,
 input wire[89:0] i_slot,input wire[2:0] i_group,
 input wire[11:0] i_aux_v,input wire[167:0] i_aux_row,
 output wire[7:0] o_v,output wire[71:0] o_addr,output wire[63:0] o_tag,output wire fault);
 dsfd_vm_static_fsr_bank8 #(.BASE(0)) leaf(.*);
endmodule
module dsfd_vm_static_fsr_b1(
 input wire ck,rst_n,input wire[17:0] i_v,input wire[251:0] i_row,
 input wire[89:0] i_slot,input wire[2:0] i_group,
 input wire[11:0] i_aux_v,input wire[167:0] i_aux_row,
 output wire[7:0] o_v,output wire[71:0] o_addr,output wire[63:0] o_tag,output wire fault);
 dsfd_vm_static_fsr_bank8 #(.BASE(8)) leaf(.*);
endmodule
module dsfd_vm_static_fsr_b2(
 input wire ck,rst_n,input wire[17:0] i_v,input wire[251:0] i_row,
 input wire[89:0] i_slot,input wire[2:0] i_group,
 input wire[11:0] i_aux_v,input wire[167:0] i_aux_row,
 output wire[7:0] o_v,output wire[71:0] o_addr,output wire[63:0] o_tag,output wire fault);
 dsfd_vm_static_fsr_bank8 #(.BASE(16)) leaf(.*);
endmodule
module dsfd_vm_static_fsr_b3(
 input wire ck,rst_n,input wire[17:0] i_v,input wire[251:0] i_row,
 input wire[89:0] i_slot,input wire[2:0] i_group,
 input wire[11:0] i_aux_v,input wire[167:0] i_aux_row,
 output wire[7:0] o_v,output wire[71:0] o_addr,output wire[63:0] o_tag,output wire fault);
 dsfd_vm_static_fsr_bank8 #(.BASE(24)) leaf(.*);
endmodule
module dsfd_vm_static_suhc_fsr_split(
 input wire[3:0] ck,rst_n,input wire[17:0] i_v,input wire[251:0] i_row,
 input wire[89:0] i_slot,input wire[2:0] i_group,
 input wire[11:0] i_aux_v,input wire[167:0] i_aux_row,
 output wire[31:0] o_v,output wire[287:0] o_addr,output wire[255:0] o_tag,output wire[3:0] fault);
 dsfd_vm_static_fsr_b0 b0(.ck(ck[0]),.rst_n(rst_n[0]),.i_v(i_v),.i_row(i_row),.i_slot(i_slot),.i_group(i_group),.i_aux_v(i_aux_v),.i_aux_row(i_aux_row),.o_v(o_v[0+:8]),.o_addr(o_addr[0+:72]),.o_tag(o_tag[0+:64]),.fault(fault[0]));
 dsfd_vm_static_fsr_b1 b1(.ck(ck[1]),.rst_n(rst_n[1]),.i_v(i_v),.i_row(i_row),.i_slot(i_slot),.i_group(i_group),.i_aux_v(i_aux_v),.i_aux_row(i_aux_row),.o_v(o_v[8+:8]),.o_addr(o_addr[72+:72]),.o_tag(o_tag[64+:64]),.fault(fault[1]));
 dsfd_vm_static_fsr_b2 b2(.ck(ck[2]),.rst_n(rst_n[2]),.i_v(i_v),.i_row(i_row),.i_slot(i_slot),.i_group(i_group),.i_aux_v(i_aux_v),.i_aux_row(i_aux_row),.o_v(o_v[16+:8]),.o_addr(o_addr[144+:72]),.o_tag(o_tag[128+:64]),.fault(fault[2]));
 dsfd_vm_static_fsr_b3 b3(.ck(ck[3]),.rst_n(rst_n[3]),.i_v(i_v),.i_row(i_row),.i_slot(i_slot),.i_group(i_group),.i_aux_v(i_aux_v),.i_aux_row(i_aux_row),.o_v(o_v[24+:8]),.o_addr(o_addr[216+:72]),.o_tag(o_tag[192+:64]),.fault(fault[3]));
endmodule
`default_nettype wire
