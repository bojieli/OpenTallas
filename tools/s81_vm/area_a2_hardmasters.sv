`timescale 1ns/1ps
// Unique native hardmaster names; every public top is full53 and unparameterized.
module s81_a2_controller_b0(
 input wire ck_control,rst_n,
 input wire [52:0] src_v,input wire [423:0] src_bank,
 input wire [2:0] header_epoch,input wire [11:0] payload_epoch,
 output wire [167:0] ids,output wire [7:0] dr_v,output wire [15:0] dr_s,output wire fault
);
 s81_a2_controller #(.NSRC(53),.BASE(0)) u_impl(
  ck_control,rst_n,src_v,src_bank,header_epoch,payload_epoch,ids,dr_v,dr_s,fault);
endmodule
module s81_a2_controller_b8(
 input wire ck_control,rst_n,
 input wire [52:0] src_v,input wire [423:0] src_bank,
 input wire [2:0] header_epoch,input wire [11:0] payload_epoch,
 output wire [167:0] ids,output wire [7:0] dr_v,output wire [15:0] dr_s,output wire fault
);
 s81_a2_controller #(.NSRC(53),.BASE(8)) u_impl(
  ck_control,rst_n,src_v,src_bank,header_epoch,payload_epoch,ids,dr_v,dr_s,fault);
endmodule
module s81_a2_controller_b16(
 input wire ck_control,rst_n,
 input wire [52:0] src_v,input wire [423:0] src_bank,
 input wire [2:0] header_epoch,input wire [11:0] payload_epoch,
 output wire [167:0] ids,output wire [7:0] dr_v,output wire [15:0] dr_s,output wire fault
);
 s81_a2_controller #(.NSRC(53),.BASE(16)) u_impl(
  ck_control,rst_n,src_v,src_bank,header_epoch,payload_epoch,ids,dr_v,dr_s,fault);
endmodule
module s81_a2_controller_b24(
 input wire ck_control,rst_n,
 input wire [52:0] src_v,input wire [423:0] src_bank,
 input wire [2:0] header_epoch,input wire [11:0] payload_epoch,
 output wire [167:0] ids,output wire [7:0] dr_v,output wire [15:0] dr_s,output wire fault
);
 s81_a2_controller #(.NSRC(53),.BASE(24)) u_impl(
  ck_control,rst_n,src_v,src_bank,header_epoch,payload_epoch,ids,dr_v,dr_s,fault);
endmodule
module s81_a2_stripe_data16(
 input wire ck,rst_n,input wire [847:0] i_data,input wire [167:0] i_sel,
 input wire [7:0] i_drain_v,input wire [15:0] i_drain_slot,
 output wire [7:0] o_v,output wire [127:0] o_data,output wire fault
);
 s81_area_stripe #(.NSRC(53),.W(16)) u_impl(
  ck,rst_n,i_data,i_sel,i_drain_v,i_drain_slot,o_v,o_data,fault);
endmodule
module s81_a2_stripe_meta26(
 input wire ck,rst_n,input wire [1377:0] i_data,input wire [167:0] i_sel,
 input wire [7:0] i_drain_v,input wire [15:0] i_drain_slot,
 output wire [7:0] o_v,output wire [207:0] o_data,output wire fault
);
 s81_area_stripe #(.NSRC(53),.W(26)) u_impl(
  ck,rst_n,i_data,i_sel,i_drain_v,i_drain_slot,o_v,o_data,fault);
endmodule
