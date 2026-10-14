`timescale 1ns/1ps
`default_nettype none
// Actual source-stack B2 producer. Queue dequeue credits reserve downstream capacity;
// VM commit pulses count destination visibility. Independent leaf clock pins are required.
module ot_hgi_dma_front_xsw10 #(
 parameter integer SOURCE_CAP=16,REQ_IDLE=0,QID=0,NL=8,LD=16,SBIT=35,MUT=0,MUT_B2=0,
 parameter [35:0] STACK_BYTES=36'd22500000000
)(input wire clk,input wire [NL-1:0] lane_clk,input wire slice_clk,input wire rst_n,
 input wire mv_v,output wire mv_rdy,input wire [226:0] mv,output wire mv_done,mv_fault,
 input wire ix_v,output wire ix_rdy,input wire [175:0] ix_cmd,input wire id_v,output wire id_rdy,input wire [31:0] id,
 output wire [203:0] dq,input wire [3:0] dq_rdy,input wire [4*NL*270-1:0] dd,output wire [4*NL-1:0] dd_cr,
 input wire lease_grant,output wire lease_busy,
 input wire [7:0] wl_credit,wl_done,output wire [7:0] issue_v,
 output wire [8*281-1:0] vm_packet,output wire [7:0] vm_bad);
 ot_hgi_dma_front_core10 #(.SOURCE_CAP(SOURCE_CAP),.REQ_IDLE(REQ_IDLE),.NS(4),.NL(NL),.SBIT(SBIT),.STACK_BYTES(STACK_BYTES),.NB(8),.LD(LD),
  .AP(0),.XP(1),.XQ(1),.QID(QID),.MUT(MUT),.MUT_B2(MUT_B2)) core(
  .clk(clk),.lane_clk(lane_clk),.rst_n(rst_n),.mv_v(mv_v),.mv_rdy(mv_rdy),.mv(mv),.mv_done(mv_done),.mv_fault(mv_fault),
  .ix_v(ix_v),.ix_rdy(ix_rdy),.ix_cmd(ix_cmd),.id_v(id_v),.id_rdy(id_rdy),.id(id),
  .dq(dq),.dq_rdy(dq_rdy),.dd(dd),.dd_cr(dd_cr),
  .lease_grant(lease_grant),.lease_busy(lease_busy),.wl_done(wl_done),.wl_rdy(8'hff),.wl_credit(wl_credit),.vm_packet(vm_packet),.vm_bad(vm_bad),.issue_v(issue_v));
endmodule
`default_nettype wire
