`timescale 1ns/1ps
`default_nettype none
// Four actual compiled masters: no parameter overrides at parent hard boundaries.
module dsfd_vm_static_return_bank8_l0(
 input wire ck,rst_n,
 input wire [7:0] i_v,input wire [63:0] i_tag,input wire [1023:0] i_data,
 input wire release_v,input wire [2:0] release_group,input wire [7:0] release_mask,
 input wire prepare_v,input wire [2:0] prepare_group,input wire [7:0] prepare_mask,
 input wire [47:0] peer_token,
 output wire [11:0] completion_token,
 output wire [7:0] o_v,output wire [1023:0] o_data,
 output wire [2:0] o_group,output wire fault
);
 dsfd_vm_static_return_bank8 #(.DW(128),.LANE(0)) u(
  .ck(ck),
  .rst_n(rst_n),
  .i_v(i_v),
  .i_tag(i_tag),
  .i_data(i_data),
  .release_v(release_v),
  .release_group(release_group),
  .release_mask(release_mask),
  .prepare_v(prepare_v),
  .prepare_group(prepare_group),
  .prepare_mask(prepare_mask),
  .peer_token(peer_token),
  .completion_token(completion_token),
  .o_v(o_v),
  .o_data(o_data),
  .o_group(o_group),
  .fault(fault));
endmodule
module dsfd_vm_static_return_bank8_l1(
 input wire ck,rst_n,
 input wire [7:0] i_v,input wire [63:0] i_tag,input wire [1023:0] i_data,
 input wire release_v,input wire [2:0] release_group,input wire [7:0] release_mask,
 input wire prepare_v,input wire [2:0] prepare_group,input wire [7:0] prepare_mask,
 input wire [47:0] peer_token,
 output wire [11:0] completion_token,
 output wire [7:0] o_v,output wire [1023:0] o_data,
 output wire [2:0] o_group,output wire fault
);
 dsfd_vm_static_return_bank8 #(.DW(128),.LANE(1)) u(
  .ck(ck),
  .rst_n(rst_n),
  .i_v(i_v),
  .i_tag(i_tag),
  .i_data(i_data),
  .release_v(release_v),
  .release_group(release_group),
  .release_mask(release_mask),
  .prepare_v(prepare_v),
  .prepare_group(prepare_group),
  .prepare_mask(prepare_mask),
  .peer_token(peer_token),
  .completion_token(completion_token),
  .o_v(o_v),
  .o_data(o_data),
  .o_group(o_group),
  .fault(fault));
endmodule
module dsfd_vm_static_return_bank8_l2(
 input wire ck,rst_n,
 input wire [7:0] i_v,input wire [63:0] i_tag,input wire [1023:0] i_data,
 input wire release_v,input wire [2:0] release_group,input wire [7:0] release_mask,
 input wire prepare_v,input wire [2:0] prepare_group,input wire [7:0] prepare_mask,
 input wire [47:0] peer_token,
 output wire [11:0] completion_token,
 output wire [7:0] o_v,output wire [1023:0] o_data,
 output wire [2:0] o_group,output wire fault
);
 dsfd_vm_static_return_bank8 #(.DW(128),.LANE(2)) u(
  .ck(ck),
  .rst_n(rst_n),
  .i_v(i_v),
  .i_tag(i_tag),
  .i_data(i_data),
  .release_v(release_v),
  .release_group(release_group),
  .release_mask(release_mask),
  .prepare_v(prepare_v),
  .prepare_group(prepare_group),
  .prepare_mask(prepare_mask),
  .peer_token(peer_token),
  .completion_token(completion_token),
  .o_v(o_v),
  .o_data(o_data),
  .o_group(o_group),
  .fault(fault));
endmodule
module dsfd_vm_static_return_bank8_l3(
 input wire ck,rst_n,
 input wire [7:0] i_v,input wire [63:0] i_tag,input wire [1023:0] i_data,
 input wire release_v,input wire [2:0] release_group,input wire [7:0] release_mask,
 input wire prepare_v,input wire [2:0] prepare_group,input wire [7:0] prepare_mask,
 input wire [47:0] peer_token,
 output wire [11:0] completion_token,
 output wire [7:0] o_v,output wire [1023:0] o_data,
 output wire [2:0] o_group,output wire fault
);
 dsfd_vm_static_return_bank8 #(.DW(128),.LANE(3)) u(
  .ck(ck),
  .rst_n(rst_n),
  .i_v(i_v),
  .i_tag(i_tag),
  .i_data(i_data),
  .release_v(release_v),
  .release_group(release_group),
  .release_mask(release_mask),
  .prepare_v(prepare_v),
  .prepare_group(prepare_group),
  .prepare_mask(prepare_mask),
  .peer_token(peer_token),
  .completion_token(completion_token),
  .o_v(o_v),
  .o_data(o_data),
  .o_group(o_group),
  .fault(fault));
endmodule
`default_nettype wire
