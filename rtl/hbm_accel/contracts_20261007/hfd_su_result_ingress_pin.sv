`timescale 1ns/1ps
// PIN-SHELL VARIANT of the SU result-ingress physical wrapper (redesign-hbm 2026-10-08): same ports as
// hfd_sm_su_edge.sv's hfd_su_result_ingress, every input lands in a flop and every output leaves a flop:
// r_in -> pin_q (unchanged), op_v/op_rows -> pin flops, consumer side on credit flow (out_r = credit-return
// pulse, OCR=4 consumer slots; see ot_hbm_su_result_pinshell.sv).  Cost: op_ack +1 cycle, out_* +1 cycle.
module hfd_su_result_ingress(
 input wire clk,rst_n,
 input wire [269:0] r_in,                  // {fault, rv, rrow[11:0], rdata[255:0]} from the last relay
 input wire op_v,input wire [6:0] op_rows,output wire op_ack,
 output wire out_v,input wire out_r,output wire [11:0] out_row,output wire [255:0] out_data,
 output wire op_done,output wire [6:0] op_done_rows,output wire fault,output wire [6:0] free_o);
 (* ASYNC_REG="TRUE" *) reg [1:0] rst_s;
 always @(posedge clk or negedge rst_n)if(!rst_n)rst_s<=2'b00;else rst_s<={rst_s[0],1'b1};
 wire rst_i=rst_s[1];
 reg [269:0] pin_q;
 always @(posedge clk or negedge rst_i)if(!rst_i)pin_q<=0;else pin_q<=r_in;
 wire c_op_v,c_out_v,c_out_r;wire [6:0] c_op_rows;wire [11:0] c_out_row;wire [255:0] c_out_data;
 ot_hbm_su_result_pinshell #(.RW(12),.DW(256),.OCR(4)) u_ps(.clk(clk),.rst_n(rst_i),.op_v(op_v),.op_rows(op_rows),
  .out_v(out_v),.out_r(out_r),.out_row(out_row),.out_data(out_data),.c_op_ack(op_ack),.c_op_v(c_op_v),.c_op_rows(c_op_rows),
  .c_out_v(c_out_v),.c_out_r(c_out_r),.c_out_row(c_out_row),.c_out_data(c_out_data));
 ot_hbm_su_result_ingress #(.RW(12),.DW(256)) u_in(.clk(clk),.rst_n(rst_i),.op_v(c_op_v),.op_rows(c_op_rows),.op_ack(op_ack),
  .in_v(pin_q[268]),.in_row(pin_q[267:256]),.in_data(pin_q[255:0]),.in_fault(pin_q[269]),
  .out_v(c_out_v),.out_r(c_out_r),.out_row(c_out_row),.out_data(c_out_data),.op_done(op_done),.op_done_rows(op_done_rows),
  .fault(fault),.free_o(free_o));
endmodule
