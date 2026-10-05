`timescale 1ns/1ps
// Local CP reset only after actual accepted CPL and all owner/provider debt.
// Native response consumers keep running while the reset request waits.
// Cold root POR is distinct; it resets the actual provider and CDC as well.
module ot_hbm_integrated_cp_reset #(parameter integer ENABLE=0)(
 input wire clk,por_n,reset_req,cp_idle,routes_drained,
 output wire cp_reset_n,reset_ack,block_new,fault
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE)begin:off
 assign cp_reset_n=por_n;assign reset_ack=0;assign block_new=0;assign fault=0;
 end else begin:on
 localparam [1:0] IDLE=0,RESET=1,ACK=2,FAIL=3;
 reg [71:0] control;
 wire [65:0] c=decode64(control);wire [1:0] state=c[1:0];
 assign fault=c[65]||state==FAIL;
 // Registered pulse: CP idle/reset combinational feedback is prohibited.
 assign cp_reset_n=por_n&&state!=RESET&&!fault;
 assign reset_ack=state==ACK&&!fault;
 assign block_new=reset_req||state!=IDLE||fault;
 always @(posedge clk or negedge por_n)begin
  if(!por_n)control<=encode64(0);
  else if(fault)control<=encode64(64'(FAIL));
  else case(state)
   IDLE:if(reset_req&&cp_idle&&routes_drained)control<=encode64(64'(RESET));
   RESET:control<=encode64(64'(ACK));
   ACK:if(!reset_req)control<=encode64(64'(IDLE));
   default:control<=encode64(64'(FAIL));
  endcase
 end
 end endgenerate
endmodule
