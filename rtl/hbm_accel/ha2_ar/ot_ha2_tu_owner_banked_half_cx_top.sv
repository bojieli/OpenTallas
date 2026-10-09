`timescale 1ns/1ps
// Physical top for the TUhalf -cx route (review-0400 R5): ot_ha2_tu_owner_banked_half_cx with the opposite-phase
// landing enabled (LANDING=1) and the genuine phase (MUT_PHASE=0), every other parameter at its default (the gated
// full-failed shape NC8 PF384 LANES16 INJ2 NPT8 FD8). Ports and names are unchanged, so the h2 fixed pin plan applies.
module ot_ha2_tu_owner_banked_half_cx_top #(
 parameter integer NC=8,PFMAX=384,LANES=16,INJ=2,NPT=8,FD=8,
 parameter integer FW=32*LANES,PWT=FW+33
)(input wire clk,rst_n,active,arm,input wire [7:0] rank,input wire [15:0] pf,
 input wire [INJ-1:0] h_v,input wire [INJ*(32+FW)-1:0] h_d,output wire [INJ-1:0] h_r,
 input wire [NPT-1:0] p_v,input wire [NPT*PWT-1:0] p_flit,
 output wire [NPT-1:0] p_r,
 output wire r_v,output wire [15:0] r_m,output wire [FW-1:0] r_d,
 output wire dupe,output wire issue_o,output wire quiet);
 ot_ha2_tu_owner_banked_half_cx #(.NC(NC),.PFMAX(PFMAX),.LANES(LANES),.INJ(INJ),.NPT(NPT),.FD(FD),
  .LANDING(1),.MUT_PHASE(0)) u_dut(
  .clk(clk),.rst_n(rst_n),.active(active),.arm(arm),.rank(rank),.pf(pf),.h_v(h_v),.h_d(h_d),.h_r(h_r),
  .p_v(p_v),.p_flit(p_flit),.p_r(p_r),.r_v(r_v),.r_m(r_m),.r_d(r_d),.dupe(dupe),.issue_o(issue_o),.quiet(quiet));
endmodule
