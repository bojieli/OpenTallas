`timescale 1ns/1ps
// Native SM -> SU result edge (contract 8c8bb2af2): the SM r face (fault, rv, rrow[11:0], rdata[255:0] = 270 b)
// leaves the SM through a PIN STATION (register abutting the SM pins), crosses NST relay stations
// (ot_hbm_result_relay_slice x5, 64-b slices, per station; the r23 worst path result_sm8 is 49 stages) and enters
// the SU through a second PIN STATION, then ot_hbm_su_result_ingress (credit reservation, count-gated release).
// One-way: no ready crosses the die; the reservation in the ingress is the flow control.
// Latency: NST + 2 cycles one way, plus the ingress write and count edge (see the bench's measured figure).
module ot_hbm_sm_su_result_edge #(parameter integer NST=4, RW=12, DW=256)(
 input wire clk,rst_n,
 // SM side (ot_hbm_accel_sm_v pins)
 input wire rv,input wire [RW-1:0] rrow,input wire [DW-1:0] rdata,input wire sm_fault,
 // SU command path: present an op's rows (hold op_v until op_ack) before starting the SM
 input wire op_v,input wire [6:0] op_rows,output wire op_ack,
 // SU consumer
 output wire out_v,input wire out_r,output wire [RW-1:0] out_row,output wire [DW-1:0] out_data,
 output wire op_done,output wire [6:0] op_done_rows,output wire fault,output wire [6:0] free_o);
 localparam integer PW=2+RW+DW;            // 270
 localparam integer NS=(PW+63)/64;          // 5 slices of 64 b
 wire [NS*64-1:0] stage[0:NST+2];
 assign stage[0]={{(NS*64-PW){1'b0}},sm_fault,rv,rrow,rdata};
 genvar k,j;
 generate for(k=0;k<NST+2;k=k+1)begin:g_st   // k=0: SM pin station; 1..NST: relays; NST+1: SU pin station
  for(j=0;j<NS;j=j+1)begin:g_sl
   ot_hbm_result_relay_slice #(.W(64),.ENABLE(1)) u_slice(.clk(clk),.rst_n(rst_n),.d(stage[k][j*64+:64]),.q(stage[k+1][j*64+:64]));
  end
 end endgenerate
 wire [PW-1:0] su=stage[NST+2][PW-1:0];
 ot_hbm_su_result_ingress #(.RW(RW),.DW(DW)) u_in(.clk(clk),.rst_n(rst_n),.op_v(op_v),.op_rows(op_rows),.op_ack(op_ack),
  .in_v(su[PW-2]),.in_row(su[RW+DW-1:DW]),.in_data(su[DW-1:0]),.in_fault(su[PW-1]),
  .out_v(out_v),.out_r(out_r),.out_row(out_row),.out_data(out_data),.op_done(op_done),.op_done_rows(op_done_rows),
  .fault(fault),.free_o(free_o));
endmodule
