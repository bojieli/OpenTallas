`timescale 1ns/1ps
`default_nettype none
// Source-identical transparent native pin profile of dsfd_vm_static_bank128; no added FF/cycle.
// _E: request inputs on the E face, registered return/commit on the W face (mirror of the standard
// profile's signal faces; ck/rst_n keep the standard N-face M3 coordinates).  Used by the bank column
// LEFT of its quarter so request pins face the quarter (S81 VM composed-hop table, left column q2bank).
module dsfd_vm_static_bank128_E(
 input wire ck,rst_n,
 input wire i_rv,input wire [8:0] i_ra,input wire [7:0] i_rt,
 input wire i_wv,input wire [8:0] i_wa,input wire [127:0] i_wd,
 input wire [3:0] i_wm,input wire [7:0] i_wt,
 output wire o_rv,output wire [127:0] o_rd,output wire [7:0] o_rt,
 output wire o_commit,output wire [8:0] o_ca,
 output wire [3:0] o_cm,output wire [7:0] o_ct
);
dsfd_vm_static_bank128 u_leaf(.ck(ck),.rst_n(rst_n),.i_rv(i_rv),.i_ra(i_ra),.i_rt(i_rt),.i_wv(i_wv),.i_wa(i_wa),
 .i_wd(i_wd),.i_wm(i_wm),.i_wt(i_wt),.o_rv(o_rv),.o_rd(o_rd),.o_rt(o_rt),.o_commit(o_commit),.o_ca(o_ca),
 .o_cm(o_cm),.o_ct(o_ct));
endmodule
`default_nettype wire
