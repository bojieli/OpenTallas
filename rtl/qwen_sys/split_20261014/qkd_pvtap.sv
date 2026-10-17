`timescale 1ns/1ps
// KVPLAN2 2215 (OT_KV_PV_T): chunk trunk taps of the trunked PV16 pair -- WIRES ONLY: qkd_pvtap<n> registers the n 128-b
// chunks a trunk still carries, ti = {top chunk, ..., lowest chunk}, once in closed qkd_rlys_296 replicas, hands the top chunk
// to its GS group's face pin (tc) and forwards the n - 1 lower chunks down the face (to).  One register stage (counted by
// kv_die in the chunk edge totals: header + DELTA_g); spare inputs of the last replica are tied low.  Generated.
module qkd_pvtap2 (input wire ck, input wire [255:0] ti, output wire [127:0] tc, output wire [127:0] to);
 wire [295:0] q;
 wire [295:0] d = {40'd0, ti};
 qkd_rlys_296 u_r0 (.ck(ck), .a(d[295:0]), .b(q[295:0]));
 assign tc = q[255:128];
 assign to = q[127:0];
endmodule
module qkd_pvtap3 (input wire ck, input wire [383:0] ti, output wire [127:0] tc, output wire [255:0] to);
 wire [591:0] q;
 wire [591:0] d = {208'd0, ti};
 qkd_rlys_296 u_r0 (.ck(ck), .a(d[295:0]), .b(q[295:0]));
 qkd_rlys_296 u_r1 (.ck(ck), .a(d[591:296]), .b(q[591:296]));
 assign tc = q[383:256];
 assign to = q[255:0];
endmodule
module qkd_pvtap4 (input wire ck, input wire [511:0] ti, output wire [127:0] tc, output wire [383:0] to);
 wire [591:0] q;
 wire [591:0] d = {80'd0, ti};
 qkd_rlys_296 u_r0 (.ck(ck), .a(d[295:0]), .b(q[295:0]));
 qkd_rlys_296 u_r1 (.ck(ck), .a(d[591:296]), .b(q[591:296]));
 assign tc = q[511:384];
 assign to = q[383:0];
endmodule
