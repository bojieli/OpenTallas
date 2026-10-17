`timescale 1ns/1ps
// KVPLAN 1815 (OT_KV_PV_T): the V word fork of one V port -- WIRES ONLY: four closed relay standards qkd_rlys_296 register
// the vport word vi[1054:0] = {v_hi, v_lo, epoch, t, valid} once and hand it out as the 31-b header vh (-> the pair control
// tile) and the eight 128-b GS chunks vc0 .. vc7 (-> each GS group's channel of the trunked pair).  One register stage
// (counted by kv_die in the header / chunk stage totals); the 129 spare inputs of the last replica are tied low.
module qkd_pvfork (input wire ck, input wire [1054:0] vi, output wire [30:0] vh,
  output wire [127:0] vc0, vc1, vc2, vc3, vc4, vc5, vc6, vc7);
 wire [1183:0] q;
 wire [1183:0] d = {129'd0, vi};
 qkd_rlys_296 u_r0 (.ck(ck), .a(d[295:0]), .b(q[295:0]));
 qkd_rlys_296 u_r1 (.ck(ck), .a(d[591:296]), .b(q[591:296]));
 qkd_rlys_296 u_r2 (.ck(ck), .a(d[887:592]), .b(q[887:592]));
 qkd_rlys_296 u_r3 (.ck(ck), .a(d[1183:888]), .b(q[1183:888]));
 assign vh = q[30:0];
 assign vc0 = q[158:31];
 assign vc1 = q[286:159];
 assign vc2 = q[414:287];
 assign vc3 = q[542:415];
 assign vc4 = q[670:543];
 assign vc5 = q[798:671];
 assign vc6 = q[926:799];
 assign vc7 = q[1054:927];
endmodule
