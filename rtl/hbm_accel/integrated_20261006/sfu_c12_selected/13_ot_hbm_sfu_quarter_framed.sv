// Integration-only c12 namespace export. Canonical source: physical/hbm_die_abstracts_20261006/compute/ot_hbm_sfu_quarter_framed.sv
`timescale 1ns/1ps
// Actual arithmetic parent connection; no stub completion or tied-ready sink.
// Added sidebands require real native frame-source binding; parent physical OPEN.
module ot_hbm_sfu_quarter_framed #(parameter integer ENABLE=0)(
 input wire clk,por_n,source_permit,warm_req,output wire warm_ack,
 input wire rx_v,output wire rx_r,input wire [1023:0] rx_d,
 input wire owner_valid,input wire [72:0] rx_owner,input wire rx_first,rx_last,
 output wire tx_v,input wire tx_r,output wire [1023:0] tx_d,
 output wire [72:0] tx_owner,output wire [3:0] tx_index,output wire tx_last,
 output wire finish_v,input wire finish_r,input wire [72:0] finish_owner,
 output wire complete_v,input wire complete_r,input wire [72:0] complete_owner,
 output wire [72:0] retained_owner,output wire fault
);
 wire req_v,req_r,rsp_v,rsp_r,child_fault;wire [2082:0] req;wire [2080:0] rsp;
 ot_hbm_compute_frame1024 #(.ENABLE(ENABLE),.IW(2083),.OW(2081)) u_frame(
  .clk(clk),.por_n(por_n),.source_permit(source_permit),.warm_req(warm_req),.warm_ack(warm_ack),
  .rx_v(rx_v),.rx_r(rx_r),.rx_d(rx_d),.owner_valid(owner_valid),.rx_owner(rx_owner),
  .rx_first(rx_first),.rx_last(rx_last),.tx_v(tx_v),.tx_r(tx_r),.tx_d(tx_d),
  .tx_owner(tx_owner),.tx_index(tx_index),.tx_last(tx_last),.finish_v(finish_v),
  .finish_r(finish_r),.finish_owner(finish_owner),.complete_v(complete_v),
  .complete_r(complete_r),.complete_owner(complete_owner),.retained_owner(retained_owner),
  .child_req_v(req_v),.child_req_r(req_r),.child_req_d(req),
  .child_rsp_v(rsp_v),.child_rsp_r(rsp_r),.child_rsp_d(rsp),.child_fault(child_fault),.fault(fault));
 ot_hbm_selected_c12__ot_hbm_sfu_quarter #(.ENABLE(ENABLE),.LANES(64)) u_quarter(
  .clk(clk),.rst_n(por_n),.req_v(req_v),.req_r(req_r),.req_tag(req[2051+:32]),
  .req_fn(req[2048+:3]),.req_x(req[0+:2048]),.rsp_v(rsp_v),.rsp_r(rsp_r),
  .rsp_tag(rsp[2049+:32]),.rsp_y(rsp[0+:2048]),.rsp_error(rsp[2048]),.fault(child_fault));
endmodule
