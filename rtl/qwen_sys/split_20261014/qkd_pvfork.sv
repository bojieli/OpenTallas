`timescale 1ns/1ps
// KVPLAN 1815 (OT_KV_PV_T): the V word fork of one V port -- WIRES ONLY: four closed relay standards qkd_rlys_296 register
// the vport word vi[1054:0] = {v_hi, v_lo, epoch, t, valid} once and hand it out as the 31-b header vh (-> the pair control
// tile) and two 512-b chunk trunks vta = {chunk 3, .., chunk 0} / vtb = {chunk 7, .., chunk 4} (chunk g = vt?[128 (g % 4) +: 128];
// -> the qkd_pvtap<n> taps that hand each 128-b GS chunk to its group's face; KVPLAN2 2215).  One register stage (counted by kv_die in the header /
// chunk stage totals); the 129 spare inputs of the last replica are tied low.
module qkd_pvfork (input wire ck, input wire [1054:0] vi, output wire [30:0] vh, output wire [511:0] vta, output wire [511:0] vtb);
 wire [1183:0] q;
 wire [1183:0] d = {129'd0, vi};
 qkd_rlys_296 u_r0 (.ck(ck), .a(d[295:0]), .b(q[295:0]));
 qkd_rlys_296 u_r1 (.ck(ck), .a(d[591:296]), .b(q[591:296]));
 qkd_rlys_296 u_r2 (.ck(ck), .a(d[887:592]), .b(q[887:592]));
 qkd_rlys_296 u_r3 (.ck(ck), .a(d[1183:888]), .b(q[1183:888]));
 assign vh = q[30:0];
 assign vta = q[542:31];
 assign vtb = q[1054:543];
endmodule
