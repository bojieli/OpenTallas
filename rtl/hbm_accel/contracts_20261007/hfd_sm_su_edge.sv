`timescale 1ns/1ps
// Physical wrapper: one SU result-ingress lane with its SU-side pin station (the SM pin station and relays are
// the r22 relay64 primitives already characterised as hfd_result_relay64_{ew,ns}).
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
 ot_hbm_su_result_ingress #(.RW(12),.DW(256)) u_in(.clk(clk),.rst_n(rst_i),.op_v(op_v),.op_rows(op_rows),.op_ack(op_ack),
  .in_v(pin_q[268]),.in_row(pin_q[267:256]),.in_data(pin_q[255:0]),.in_fault(pin_q[269]),
  .out_v(out_v),.out_r(out_r),.out_row(out_row),.out_data(out_data),.op_done(op_done),.op_done_rows(op_done_rows),
  .fault(fault),.free_o(free_o));
endmodule
