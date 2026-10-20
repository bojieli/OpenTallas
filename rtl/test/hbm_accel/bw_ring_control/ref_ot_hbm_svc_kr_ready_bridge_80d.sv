`timescale 1ns/1ps
// Opt-in H9b KR compatibility: native source consumes ready from the prior
// edge; legacy consumer consumes valid/ready at the same edge. A three-entry
// ring reserves one in-flight grant. At most two resident entries advertise
// ready; the outstanding grant can fill the third. One HBM edge latency,
// sustained II=1. 3*277=831 payload bits per PC, no indexed storage above2kb.
module ot_hbm_svc_kr_ready_bridge #(parameter integer WIDTH=277,MUT=0)(
 input wire clk,rst_n,input wire in_v,output wire in_rdy,
 input wire[WIDTH-1:0]in_data,output wire out_v,input wire out_rdy,
 output wire[WIDTH-1:0]out_data,output wire fault,
 output wire[2:0]occupancy
);
 reg ready_prev;
 always @(posedge clk)if(!rst_n)ready_prev<=0;else ready_prev<=in_rdy;
 assign in_rdy=rst_n&&(occupancy<3'd2);
 wire push=rst_n&&in_v&&((MUT==1)?in_rdy:ready_prev);
 wire[2:0]next_count;
 ot_hbm_svc_ring_bw_safe #(.WIDTH(WIDTH),.DEPTH(3)) u_ring(
  .clk(clk),.rst_n(rst_n),.in_v(push),.in_data(in_data),
  .out_v(out_v),.pop(rst_n&&out_v&&out_rdy),.out_data(out_data),
  .cnt(occupancy),.cnt_next(next_count),.fault(fault));
endmodule
